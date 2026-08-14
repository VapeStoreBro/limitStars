from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(slots=True)
class PaymentInvoice:
    provider: str
    payment_id: str
    pay_url: str | None
    text: str


class PaymentProvider(Protocol):
    async def create_invoice(self, order_id: int, amount_rub: Decimal, description: str) -> PaymentInvoice: ...


class StubPaymentProvider:
    """Temporary provider until a concrete SBP API is selected."""
    name = "stub"

    async def create_invoice(self, order_id: int, amount_rub: Decimal, description: str) -> PaymentInvoice:
        return PaymentInvoice(
            provider=self.name,
            payment_id=f"stub-{order_id}",
            pay_url=None,
            text=(
                "🧪 Оплата пока в тестовом режиме.\n"
                f"Заказ #{order_id} на {amount_rub} ₽ создан.\n\n"
                "После подключения СБП-провайдера здесь появится кнопка оплаты, "
                "а webhook автоматически переведёт заказ в выдачу."
            ),
        )
