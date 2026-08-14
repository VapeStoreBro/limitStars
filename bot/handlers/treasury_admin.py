from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.config import Settings
from bot.handlers.admin import deny_if_not_admin
from bot.keyboards import admin_menu
from bot.services.treasury import TonTreasury

router = Router(name="treasury_admin")


@router.callback_query(F.data == "admin:treasury")
async def treasury_status(call: CallbackQuery, settings: Settings, treasury: TonTreasury):
    if await deny_if_not_admin(call, settings):
        return

    status = await treasury.status()
    if not status.configured:
        ton_line = "⚪ TON-казна: <b>кошелёк ещё не задан</b>"
    elif status.balance_ton is None:
        ton_line = f"🔴 TON-казна: <b>ошибка чтения</b> ({status.error or 'unknown'})"
    else:
        icon = {"ok": "🟢", "low": "🟡", "critical": "🔴"}.get(status.level, "⚪")
        ton_line = f"{icon} TON-казна: <b>{status.balance_ton} TON</b>"

    text = (
        "⚙️ <b>Статус системы</b>\n\n"
        f"СБП-провайдер: <b>{settings.payment_provider}</b>\n"
        f"Выдача Stars: <b>{settings.fulfillment_provider}</b>\n"
        f"{ton_line}\n"
        f"Порог предупреждения: <b>{settings.ton_low_balance} TON</b>\n"
        f"Критический порог: <b>{settings.ton_critical_balance} TON</b>"
    )
    await call.message.edit_text(text, reply_markup=admin_menu())
    await call.answer()
