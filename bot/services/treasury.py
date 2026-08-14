from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import aiohttp

NANO = Decimal("1000000000")


@dataclass(slots=True)
class TreasuryStatus:
    configured: bool
    balance_ton: Decimal | None
    level: str
    error: str | None = None


class TonTreasury:
    def __init__(
        self,
        address: str,
        api_key: str | None,
        low_balance_ton: Decimal,
        critical_balance_ton: Decimal,
    ) -> None:
        self.address = address.strip()
        self.api_key = api_key.strip() if api_key else None
        self.low_balance_ton = low_balance_ton
        self.critical_balance_ton = critical_balance_ton

    async def status(self) -> TreasuryStatus:
        if not self.address:
            return TreasuryStatus(False, None, "not_configured")

        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        params = {"address": self.address}
        timeout = aiohttp.ClientTimeout(total=10)
        try:
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get("https://toncenter.com/api/v2/getAddressBalance", params=params) as response:
                    data = await response.json(content_type=None)
                    if response.status != 200 or not data.get("ok"):
                        return TreasuryStatus(True, None, "error", str(data.get("error") or response.status))
        except Exception as exc:
            return TreasuryStatus(True, None, "error", f"{type(exc).__name__}: {exc}")

        try:
            balance = (Decimal(str(data["result"])) / NANO).quantize(Decimal("0.0001"))
        except Exception as exc:
            return TreasuryStatus(True, None, "error", f"bad TON Center response: {exc}")

        if balance <= self.critical_balance_ton:
            level = "critical"
        elif balance <= self.low_balance_ton:
            level = "low"
        else:
            level = "ok"
        return TreasuryStatus(True, balance, level)
