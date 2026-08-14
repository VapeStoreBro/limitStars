from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from bot.db import Order


@dataclass(slots=True)
class FulfillmentResult:
    success: bool
    provider: str
    external_id: str | None = None
    error: str | None = None


class FulfillmentProvider(Protocol):
    async def send_stars(self, order: Order) -> FulfillmentResult: ...


class StubFulfillmentProvider:
    """Safe placeholder. Does not pretend that Stars were sent."""
    name = "stub"

    async def send_stars(self, order: Order) -> FulfillmentResult:
        return FulfillmentResult(
            success=False,
            provider=self.name,
            error="Stars provider is not configured yet",
        )
