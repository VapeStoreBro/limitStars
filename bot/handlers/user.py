from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.db import Database
from bot.keyboards import amount_menu, confirm_menu, main_menu, recipient_menu
from bot.services.payment import PaymentProvider
from bot.services.pricing import PricingService
from bot.states import BuyStars

router = Router(name="user")
USERNAME_RE = re.compile(r"^@[A-Za-z0-9_]{5,32}$")


def clean_username(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if not value.startswith("@"):
        value = "@" + value
    return value if USERNAME_RE.fullmatch(value) else None


async def touch_user(message_or_call, db: Database) -> None:
    user = message_or_call.from_user
    await db.upsert_user(user.id, user.username, user.first_name)


@router.message(CommandStart())
async def start(message: Message, db: Database, settings: Settings, state: FSMContext):
    await state.clear()
    await touch_user(message, db)
    await message.answer(
        "⭐ <b>Limit Stars</b>\n\n"
        "Быстрая покупка Telegram Stars себе или другу.\n"
        f"Минимум: <b>{settings.min_stars} ⭐</b>\n"
        f"Максимум: <b>{settings.max_stars} ⭐</b>",
        reply_markup=main_menu(message.from_user.id in settings.admin_ids),
    )


@router.callback_query(F.data == "menu:home")
async def home(call: CallbackQuery, db: Database, settings: Settings, state: FSMContext):
    await state.clear()
    await touch_user(call, db)
    await call.message.edit_text(
        "⭐ <b>Limit Stars</b>\n\nВыбери действие:",
        reply_markup=main_menu(call.from_user.id in settings.admin_ids),
    )
    await call.answer()


@router.callback_query(F.data == "buy:start")
async def buy_start(call: CallbackQuery, db: Database, pricing: PricingService, state: FSMContext):
    await touch_user(call, db)
    price = await pricing.quote(call.from_user.id, 100)
    await state.set_state(BuyStars.choose_recipient)
    await call.message.edit_text(
        "⭐ <b>Кому отправить Stars?</b>\n\n"
        f"Твой текущий тариф: <b>{price.unit_price} ₽/⭐</b> ({price.pricing_label}).",
        reply_markup=recipient_menu(),
    )
    await call.answer()


@router.callback_query(F.data == "buy:recipient:self")
async def recipient_self(call: CallbackQuery, state: FSMContext):
    username = clean_username(call.from_user.username)
    if not username:
        await call.answer("У твоего аккаунта нет @username. Сначала установи username в Telegram.", show_alert=True)
        return
    await state.update_data(recipient_type="self", recipient_username=username)
    await state.set_state(BuyStars.choose_amount)
    await call.message.edit_text(
        f"👤 Получатель: <b>{username}</b>\n\nВыбери количество Stars:",
        reply_markup=amount_menu(),
    )
    await call.answer()


@router.callback_query(F.data == "buy:recipient:friend")
async def recipient_friend(call: CallbackQuery, state: FSMContext):
    await state.set_state(BuyStars.enter_friend_username)
    await call.message.edit_text(
        "🎁 <b>Отправка другу</b>\n\n"
        "Пришли @username получателя. Без username оформить заказ нельзя.\n\n"
        "Пример: <code>@durov</code>"
    )
    await call.answer()


@router.message(BuyStars.enter_friend_username)
async def friend_username(message: Message, state: FSMContext):
    username = clean_username(message.text)
    if not username:
        await message.answer("❌ Нужен корректный username вида <code>@username</code>. Попробуй ещё раз.")
        return
    await state.update_data(recipient_type="friend", recipient_username=username)
    await state.set_state(BuyStars.choose_amount)
    await message.answer(
        f"🎁 Получатель: <b>{username}</b>\n\nВыбери количество Stars:",
        reply_markup=amount_menu(),
    )


async def show_quote(target, state: FSMContext, pricing: PricingService, buyer_id: int, stars: int):
    data = await state.get_data()
    quote = await pricing.quote(buyer_id, stars)
    await state.update_data(stars=stars)
    await state.set_state(BuyStars.confirm)
    text = (
        "🧾 <b>Проверь заказ</b>\n\n"
        f"Получатель: <b>{data['recipient_username']}</b>\n"
        f"Количество: <b>{stars} ⭐</b>\n"
        f"Цена за 1 ⭐: <b>{quote.unit_price} ₽</b>\n"
        f"Итого: <b>{quote.total} ₽</b>\n\n"
        "После оплаты заказ автоматически уйдёт на выдачу."
    )
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=confirm_menu())
        await target.answer()
    else:
        await target.answer(text, reply_markup=confirm_menu())


@router.callback_query(F.data.startswith("buy:amount:"))
async def choose_amount(call: CallbackQuery, state: FSMContext, pricing: PricingService, settings: Settings):
    raw = call.data.rsplit(":", 1)[-1]
    if raw == "custom":
        await state.set_state(BuyStars.enter_custom_amount)
        await call.message.edit_text(
            f"✏️ Введи количество Stars от <b>{settings.min_stars}</b> до <b>{settings.max_stars}</b>."
        )
        await call.answer()
        return
    stars = int(raw)
    await show_quote(call, state, pricing, call.from_user.id, stars)


@router.message(BuyStars.enter_custom_amount)
async def custom_amount(message: Message, state: FSMContext, pricing: PricingService, settings: Settings):
    if not message.text or not message.text.strip().isdigit():
        await message.answer("❌ Пришли количество целым числом.")
        return
    stars = int(message.text.strip())
    if not settings.min_stars <= stars <= settings.max_stars:
        await message.answer(f"❌ Можно купить от {settings.min_stars} до {settings.max_stars} ⭐.")
        return
    await show_quote(message, state, pricing, message.from_user.id, stars)


@router.callback_query(F.data == "buy:back_amount")
async def back_amount(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.set_state(BuyStars.choose_amount)
    await call.message.edit_text(
        f"Получатель: <b>{data['recipient_username']}</b>\n\nВыбери количество Stars:",
        reply_markup=amount_menu(),
    )
    await call.answer()


@router.callback_query(F.data == "buy:confirm")
async def confirm_order(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    pricing: PricingService,
    payment: PaymentProvider,
):
    data = await state.get_data()
    if not all(k in data for k in ("recipient_type", "recipient_username", "stars")):
        await call.answer("Сессия заказа устарела. Начни заново.", show_alert=True)
        await state.clear()
        return
    stars = int(data["stars"])
    quote = await pricing.quote(call.from_user.id, stars)
    order_id = await db.create_order(
        buyer_id=call.from_user.id,
        buyer_username=call.from_user.username,
        recipient_type=data["recipient_type"],
        recipient_username=data["recipient_username"],
        stars=stars,
        unit_price_rub=quote.unit_price,
        cost_unit_price_rub=quote.cost_unit_price,
        total_rub=quote.total,
        expected_cost_rub=quote.expected_cost,
    )
    invoice = await payment.create_invoice(order_id, quote.total, f"Limit Stars: {stars} stars")
    await db.set_order_payment(order_id, invoice.provider, invoice.payment_id)
    await state.clear()
    await call.message.edit_text(
        f"✅ <b>Заказ #{order_id}</b>\n\n"
        f"Получатель: <b>{data['recipient_username']}</b>\n"
        f"Stars: <b>{stars} ⭐</b>\n"
        f"К оплате: <b>{quote.total} ₽</b>\n\n"
        f"{invoice.text}"
    )
    await call.answer()


@router.callback_query(F.data == "orders:mine")
async def my_orders(call: CallbackQuery, db: Database, settings: Settings):
    rows = await db.recent_orders(call.from_user.id)
    if not rows:
        text = "📦 У тебя пока нет заказов."
    else:
        status_icons = {
            "awaiting_payment": "🕒", "paid": "💳", "fulfilling": "⚙️",
            "success": "✅", "failed": "❌", "cancelled": "🚫",
        }
        lines = ["📦 <b>Последние заказы</b>\n"]
        for row in rows:
            icon = status_icons.get(row["status"], "•")
            lines.append(
                f"{icon} <b>#{row['id']}</b> · {row['stars']} ⭐ · {row['total_rub']} ₽ → {row['recipient_username']}"
            )
        text = "\n".join(lines)
    await call.message.edit_text(text, reply_markup=main_menu(call.from_user.id in settings.admin_ids))
    await call.answer()


@router.callback_query(F.data == "help")
async def help_handler(call: CallbackQuery):
    await call.message.edit_text(
        "ℹ️ <b>Как это работает</b>\n\n"
        "1. Выбираешь — себе или другу.\n"
        "2. Выбираешь готовый пакет или вводишь своё количество.\n"
        "3. Оплачиваешь по СБП.\n"
        "4. После подтверждения оплаты Stars автоматически отправляются получателю."
    )
    await call.answer()


@router.callback_query(F.data == "buy:cancel")
async def cancel_buy(call: CallbackQuery, state: FSMContext, settings: Settings):
    await state.clear()
    await call.message.edit_text("Заказ отменён.", reply_markup=main_menu(call.from_user.id in settings.admin_ids))
    await call.answer()
