from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.db import Database
from bot.keyboards import admin_menu, special_mode_menu
from bot.services.pricing import PricingService
from bot.states import AdminPrice, AdminSpecial

router = Router(name="admin")


def is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in settings.admin_ids


def is_private_admin(event, settings: Settings) -> bool:
    chat = event.message.chat if isinstance(event, CallbackQuery) else event.chat
    return is_admin(event.from_user.id, settings) and chat.type == "private"


async def deny_if_not_admin(event, settings: Settings) -> bool:
    if is_private_admin(event, settings):
        return False
    if isinstance(event, CallbackQuery):
        await event.answer()
    return True


async def render_home(call_or_message, pricing: PricingService):
    sale = await pricing.sale_price()
    cost = await pricing.cost_price()
    text = (
        "🛠 <b>Limit Stars · Админка</b>\n\n"
        f"💰 Продажа: <b>{sale} ₽/⭐</b>\n"
        f"🧾 Закупочная оценка: <b>{cost} ₽/⭐</b>\n\n"
        "Выбери раздел:"
    )
    if isinstance(call_or_message, CallbackQuery):
        await call_or_message.message.edit_text(text, reply_markup=admin_menu())
        await call_or_message.answer()
    else:
        await call_or_message.answer(text, reply_markup=admin_menu())


@router.message(Command("admin"))
async def admin_command(message: Message, settings: Settings, pricing: PricingService, state: FSMContext):
    if not is_private_admin(message, settings):
        return
    await state.clear()
    await render_home(message, pricing)


@router.callback_query(F.data == "admin:home")
async def admin_home(call: CallbackQuery, settings: Settings, pricing: PricingService, state: FSMContext):
    if await deny_if_not_admin(call, settings):
        return
    await state.clear()
    await render_home(call, pricing)


@router.callback_query(F.data == "admin:stats")
async def stats(call: CallbackQuery, settings: Settings, db: Database):
    if await deny_if_not_admin(call, settings):
        return
    s = await db.stats()
    profit = s["revenue"] - s["expected_cost"]
    success_rate = (s["success_orders"] / s["total_orders"] * 100) if s["total_orders"] else 0
    text = (
        "📊 <b>Статистика</b>\n\n"
        f"Сегодня заказов: <b>{s['today_orders']}</b>\n"
        f"Сегодня Stars: <b>{s['today_stars']} ⭐</b>\n"
        f"Сегодня оборот: <b>{s['today_revenue']:.2f} ₽</b>\n\n"
        f"Всего пользователей: <b>{s['users']}</b>\n"
        f"Всего заказов: <b>{s['total_orders']}</b>\n"
        f"Успешных: <b>{s['success_orders']}</b> ({success_rate:.1f}%)\n"
        f"Продано Stars: <b>{s['sold_stars']} ⭐</b>\n"
        f"Оборот: <b>{s['revenue']:.2f} ₽</b>\n"
        f"Ожид. себестоимость: <b>{s['expected_cost']:.2f} ₽</b>\n"
        f"Ожид. валовая прибыль: <b>{profit:.2f} ₽</b>\n"
        f"В обработке: <b>{s['pending']}</b>"
    )
    await call.message.edit_text(text, reply_markup=admin_menu())
    await call.answer()


@router.callback_query(F.data == "admin:sale_price")
async def sale_price(call: CallbackQuery, settings: Settings, state: FSMContext):
    if await deny_if_not_admin(call, settings):
        return
    await state.set_state(AdminPrice.enter_sale_price)
    await call.message.edit_text("💰 Введи новую цену <b>за 1 ⭐</b> в рублях.\nПример: <code>1.40</code>")
    await call.answer()


@router.message(AdminPrice.enter_sale_price)
async def sale_price_value(message: Message, settings: Settings, db: Database, state: FSMContext, pricing: PricingService):
    if not is_private_admin(message, settings):
        return
    try:
        value = Decimal((message.text or "").replace(",", "."))
        if value <= 0 or value > 100:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        await message.answer("❌ Неверная цена. Пример: <code>1.40</code>")
        return
    await db.set_setting("sale_price_rub", str(value))
    await state.clear()
    await message.answer(f"✅ Новая цена продажи: <b>{value} ₽/⭐</b>")
    await render_home(message, pricing)


@router.callback_query(F.data == "admin:cost_price")
async def cost_price(call: CallbackQuery, settings: Settings, state: FSMContext):
    if await deny_if_not_admin(call, settings):
        return
    await state.set_state(AdminPrice.enter_cost_price)
    await call.message.edit_text("🧾 Введи текущую себестоимость <b>1 ⭐</b>.\nПример: <code>1.25</code>")
    await call.answer()


@router.message(AdminPrice.enter_cost_price)
async def cost_price_value(message: Message, settings: Settings, db: Database, state: FSMContext, pricing: PricingService):
    if not is_private_admin(message, settings):
        return
    try:
        value = Decimal((message.text or "").replace(",", "."))
        if value <= 0 or value > 100:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        await message.answer("❌ Неверная цена.")
        return
    await db.set_setting("cost_price_rub", str(value))
    await state.clear()
    await message.answer(f"✅ Закупочная оценка: <b>{value} ₽/⭐</b>")
    await render_home(message, pricing)


@router.callback_query(F.data == "admin:special")
async def special(call: CallbackQuery, settings: Settings, state: FSMContext):
    if await deny_if_not_admin(call, settings):
        return
    await state.set_state(AdminSpecial.enter_user)
    await call.message.edit_text(
        "👥 <b>Особая цена</b>\n\n"
        "Пришли Telegram ID или @username пользователя.\n"
        "@username сработает, если человек уже запускал бота.\n\n"
        "После этого выберешь: по закупу, фиксированная цена или закуп + %."
    )
    await call.answer()


@router.message(AdminSpecial.enter_user)
async def special_user(message: Message, settings: Settings, state: FSMContext, db: Database):
    if not is_private_admin(message, settings):
        return
    raw = (message.text or "").strip()
    user = await db.find_user(raw)
    if not user:
        await message.answer(
            "❌ Пользователь не найден в базе. Если вводишь @username, человек должен хотя бы один раз запустить бота. "
            "Либо пришли его числовой Telegram ID."
        )
        return
    user_id = int(user["telegram_id"])
    username = user["username"]
    await state.update_data(special_user_id=user_id, special_username=username)
    await state.set_state(AdminSpecial.choose_mode)
    label = f"@{username}" if username else str(user_id)
    await message.answer(f"Пользователь <b>{label}</b> (<code>{user_id}</code>). Какой тариф поставить?", reply_markup=special_mode_menu())


@router.callback_query(F.data.startswith("admin:special_mode:"))
async def special_mode(call: CallbackQuery, settings: Settings, state: FSMContext, db: Database, pricing: PricingService):
    if await deny_if_not_admin(call, settings):
        return
    data = await state.get_data()
    user_id = data.get("special_user_id")
    if not user_id:
        await call.answer("Сессия устарела", show_alert=True)
        return
    mode = call.data.rsplit(":", 1)[-1]
    if mode == "remove":
        await db.remove_special_price(user_id)
        await state.clear()
        await call.message.edit_text(f"✅ Особая цена для <code>{user_id}</code> удалена.", reply_markup=admin_menu())
        await call.answer()
        return
    if mode == "cost":
        await db.set_special_price(user_id, data.get("special_username"), "cost", None)
        await state.clear()
        await call.message.edit_text(f"✅ Для <code>{user_id}</code> установлен тариф <b>по закупу</b>.", reply_markup=admin_menu())
        await call.answer()
        return
    await state.update_data(special_mode=mode)
    await state.set_state(AdminSpecial.enter_value)
    prompt = "Введи фиксированную цену за 1 ⭐:" if mode == "fixed" else "Введи наценку к закупу в процентах:"
    await call.message.edit_text(prompt)
    await call.answer()


@router.message(AdminSpecial.enter_value)
async def special_value(message: Message, settings: Settings, state: FSMContext, db: Database, pricing: PricingService):
    if not is_private_admin(message, settings):
        return
    data = await state.get_data()
    try:
        value = Decimal((message.text or "").replace(",", "."))
        if value < 0 or value > 1000:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        await message.answer("❌ Неверное значение.")
        return
    await db.set_special_price(data["special_user_id"], data.get("special_username"), data["special_mode"], str(value))
    await state.clear()
    await message.answer("✅ Особый тариф сохранён.")
    await render_home(message, pricing)


@router.callback_query(F.data == "admin:orders")
async def admin_orders(call: CallbackQuery, settings: Settings, db: Database):
    if await deny_if_not_admin(call, settings):
        return
    rows = await db.fetchall("SELECT * FROM orders ORDER BY id DESC LIMIT 15")
    if not rows:
        text = "📦 Заказов пока нет."
    else:
        lines = ["📦 <b>Последние заказы</b>\n"]
        for row in rows:
            lines.append(
                f"#{row['id']} · {row['status']} · {row['stars']} ⭐ · {row['total_rub']} ₽ · "
                f"{row['buyer_id']} → {row['recipient_username']}"
            )
        text = "\n".join(lines)
    await call.message.edit_text(text, reply_markup=admin_menu())
    await call.answer()


@router.callback_query(F.data == "admin:system")
async def system_status(call: CallbackQuery, settings: Settings):
    if await deny_if_not_admin(call, settings):
        return
    text = (
        "⚙️ <b>Статус системы</b>\n\n"
        f"СБП-провайдер: <b>{settings.payment_provider}</b>\n"
        f"Выдача Stars: <b>{settings.fulfillment_provider}</b>\n"
        "TON-казна: <b>ещё не подключена</b>\n\n"
        "Магазин и расчёт цен уже работают. Для полной автоматики осталось подключить конкретный СБП API, "
        "TON hot-wallet и механизм выдачи Stars."
    )
    await call.message.edit_text(text, reply_markup=admin_menu())
    await call.answer()
