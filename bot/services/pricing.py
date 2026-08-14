from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from bot.config import Settings
from bot.db import Database

MONEY = Decimal("0.01")


@dataclass(slots=True)
class PriceQuote:
    stars: int
    unit_price: Decimal
    cost_unit_price: Decimal
    total: Decimal
    expected_cost: Decimal
    pricing_label: str


class PricingService:
    def __init__(self, db: Database, settings: Settings):
        self.db = db
        self.settings = settings

    async def sale_price(self) -> Decimal:
        return Decimal(await self.db.get_setting("sale_price_rub", str(self.settings.default_star_price_rub)))

    async def cost_price(self) -> Decimal:
        return Decimal(await self.db.get_setting("cost_price_rub", str(self.settings.default_cost_price_rub)))

    async def quote(self, buyer_id: int, stars: int) -> PriceQuote:
        sale = await self.sale_price()
        cost = await self.cost_price()
        special = await self.db.get_special_price(buyer_id)
        unit = sale
        label = "обычный прайс"
        if special:
            mode = special["mode"]
            value = Decimal(special["value"]) if special["value"] else Decimal("0")
            if mode == "cost":
                unit = cost
                label = "по закупу"
            elif mode == "fixed":
                unit = value
                label = "персональный прайс"
            elif mode == "cost_plus_percent":
                unit = cost * (Decimal("1") + value / Decimal("100"))
                label = f"закуп + {value}%"
        unit = unit.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        total = (unit * stars).quantize(MONEY, rounding=ROUND_HALF_UP)
        expected_cost = (cost * stars).quantize(MONEY, rounding=ROUND_HALF_UP)
        return PriceQuote(stars, unit, cost, total, expected_cost, label)
