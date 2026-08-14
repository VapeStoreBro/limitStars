from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


def _load_dotenv(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for raw_line in p.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _parse_admin_ids(value: str) -> list[int]:
    value = value.strip().strip("[]")
    return [int(item.strip()) for item in value.split(",") if item.strip()]


_load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    admin_ids: list[int]
    database_path: str
    default_star_price_rub: Decimal
    default_cost_price_rub: Decimal
    min_stars: int
    max_stars: int
    payment_provider: str
    fulfillment_provider: str

    @property
    def db_path(self) -> Path:
        path = Path(self.database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")
    return Settings(
        bot_token=token,
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "6577441312")),
        database_path=os.getenv("DATABASE_PATH", "data/limitstars.sqlite3"),
        default_star_price_rub=Decimal(os.getenv("DEFAULT_STAR_PRICE_RUB", "1.40")),
        default_cost_price_rub=Decimal(os.getenv("DEFAULT_COST_PRICE_RUB", "1.25")),
        min_stars=int(os.getenv("MIN_STARS", "50")),
        max_stars=int(os.getenv("MAX_STARS", "10000")),
        payment_provider=os.getenv("PAYMENT_PROVIDER", "stub"),
        fulfillment_provider=os.getenv("FULFILLMENT_PROVIDER", "stub"),
    )


settings = load_settings()
