from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import settings
from bot.db import Database
from bot.handlers import admin, user
from bot.services.fulfillment import StubFulfillmentProvider
from bot.services.payment import StubPaymentProvider
from bot.services.pricing import PricingService
from bot.services.treasury import TonTreasury


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    db = Database(settings.db_path)
    await db.init()
    pricing = PricingService(db, settings)
    payment = StubPaymentProvider()
    fulfillment = StubFulfillmentProvider()
    treasury = TonTreasury(
        settings.ton_wallet_address,
        settings.toncenter_api_key,
        settings.ton_low_balance,
        settings.ton_critical_balance,
    )

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(admin.router)
    dp.include_router(user.router)

    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(
        bot,
        db=db,
        settings=settings,
        pricing=pricing,
        payment=payment,
        fulfillment=fulfillment,
        treasury=treasury,
        allowed_updates=dp.resolve_used_update_types(),
    )


if __name__ == "__main__":
    asyncio.run(main())
