from __future__ import annotations

import asyncio
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    created_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS special_prices (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    mode TEXT NOT NULL CHECK(mode IN ('cost','fixed','cost_plus_percent')),
    value TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id INTEGER NOT NULL,
    buyer_username TEXT,
    recipient_type TEXT NOT NULL CHECK(recipient_type IN ('self','friend')),
    recipient_username TEXT NOT NULL,
    stars INTEGER NOT NULL,
    unit_price_rub TEXT NOT NULL,
    cost_unit_price_rub TEXT NOT NULL,
    total_rub TEXT NOT NULL,
    expected_cost_rub TEXT NOT NULL,
    status TEXT NOT NULL,
    payment_provider TEXT,
    payment_id TEXT,
    fulfillment_provider TEXT,
    fulfillment_id TEXT,
    error_text TEXT,
    created_at TEXT NOT NULL,
    paid_at TEXT,
    fulfilled_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_orders_buyer ON orders(buyer_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status, id);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Order:
    id: int
    buyer_id: int
    buyer_username: str | None
    recipient_type: str
    recipient_username: str
    stars: int
    unit_price_rub: Decimal
    cost_unit_price_rub: Decimal
    total_rub: Decimal
    expected_cost_rub: Decimal
    status: str
    payment_id: str | None = None
    fulfillment_id: str | None = None
    error_text: str | None = None


class Database:
    def __init__(self, path: Path):
        self.path = path
        self._lock = asyncio.Lock()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    async def init(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._init_sync)

    def _init_sync(self) -> None:
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        async with self._lock:
            return await asyncio.to_thread(self._execute_sync, sql, params)

    def _execute_sync(self, sql: str, params: tuple[Any, ...]) -> int:
        with closing(self._connect()) as conn:
            cur = conn.execute(sql, params)
            conn.commit()
            return int(cur.lastrowid or 0)

    async def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        return await asyncio.to_thread(self._fetchone_sync, sql, params)

    def _fetchone_sync(self, sql: str, params: tuple[Any, ...]) -> sqlite3.Row | None:
        with closing(self._connect()) as conn:
            return conn.execute(sql, params).fetchone()

    async def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        return await asyncio.to_thread(self._fetchall_sync, sql, params)

    def _fetchall_sync(self, sql: str, params: tuple[Any, ...]) -> list[sqlite3.Row]:
        with closing(self._connect()) as conn:
            return list(conn.execute(sql, params).fetchall())

    async def upsert_user(self, telegram_id: int, username: str | None, first_name: str | None) -> None:
        now = utcnow()
        await self.execute(
            """
            INSERT INTO users(telegram_id, username, first_name, created_at, last_seen_at)
            VALUES(?,?,?,?,?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                last_seen_at=excluded.last_seen_at
            """,
            (telegram_id, username, first_name, now, now),
        )

    async def get_setting(self, key: str, default: str) -> str:
        row = await self.fetchone("SELECT value FROM settings WHERE key=?", (key,))
        return str(row["value"]) if row else default

    async def set_setting(self, key: str, value: str) -> None:
        await self.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    async def create_order(
        self,
        buyer_id: int,
        buyer_username: str | None,
        recipient_type: str,
        recipient_username: str,
        stars: int,
        unit_price_rub: Decimal,
        cost_unit_price_rub: Decimal,
        total_rub: Decimal,
        expected_cost_rub: Decimal,
    ) -> int:
        return await self.execute(
            """
            INSERT INTO orders(
                buyer_id,buyer_username,recipient_type,recipient_username,stars,
                unit_price_rub,cost_unit_price_rub,total_rub,expected_cost_rub,
                status,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                buyer_id,
                buyer_username,
                recipient_type,
                recipient_username,
                stars,
                str(unit_price_rub),
                str(cost_unit_price_rub),
                str(total_rub),
                str(expected_cost_rub),
                "awaiting_payment",
                utcnow(),
            ),
        )

    async def get_order(self, order_id: int) -> Order | None:
        row = await self.fetchone("SELECT * FROM orders WHERE id=?", (order_id,))
        if not row:
            return None
        return Order(
            id=row["id"], buyer_id=row["buyer_id"], buyer_username=row["buyer_username"],
            recipient_type=row["recipient_type"], recipient_username=row["recipient_username"],
            stars=row["stars"], unit_price_rub=Decimal(row["unit_price_rub"]),
            cost_unit_price_rub=Decimal(row["cost_unit_price_rub"]), total_rub=Decimal(row["total_rub"]),
            expected_cost_rub=Decimal(row["expected_cost_rub"]), status=row["status"],
            payment_id=row["payment_id"], fulfillment_id=row["fulfillment_id"], error_text=row["error_text"],
        )

    async def set_order_payment(self, order_id: int, provider: str, payment_id: str) -> None:
        await self.execute(
            "UPDATE orders SET payment_provider=?, payment_id=? WHERE id=? AND status='awaiting_payment'",
            (provider, payment_id, order_id),
        )

    async def mark_paid(self, order_id: int) -> bool:
        async with self._lock:
            return await asyncio.to_thread(self._mark_paid_sync, order_id)

    def _mark_paid_sync(self, order_id: int) -> bool:
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "UPDATE orders SET status='paid', paid_at=? WHERE id=? AND status='awaiting_payment'",
                (utcnow(), order_id),
            )
            conn.commit()
            return cur.rowcount == 1

    async def set_order_status(self, order_id: int, status: str, **fields: str | None) -> None:
        allowed = {"fulfillment_provider", "fulfillment_id", "error_text", "fulfilled_at"}
        parts = ["status=?"]
        values: list[Any] = [status]
        for key, value in fields.items():
            if key not in allowed:
                continue
            parts.append(f"{key}=?")
            values.append(value)
        values.append(order_id)
        await self.execute(f"UPDATE orders SET {', '.join(parts)} WHERE id=?", tuple(values))

    async def recent_orders(self, buyer_id: int, limit: int = 10) -> list[sqlite3.Row]:
        return await self.fetchall(
            "SELECT * FROM orders WHERE buyer_id=? ORDER BY id DESC LIMIT ?", (buyer_id, limit)
        )

    async def find_user(self, value: str) -> sqlite3.Row | None:
        value = value.strip()
        if value.isdigit():
            return await self.fetchone("SELECT * FROM users WHERE telegram_id=?", (int(value),))
        username = value.lstrip("@").lower()
        return await self.fetchone("SELECT * FROM users WHERE lower(username)=?", (username,))

    async def get_special_price(self, telegram_id: int) -> sqlite3.Row | None:
        return await self.fetchone("SELECT * FROM special_prices WHERE telegram_id=?", (telegram_id,))

    async def set_special_price(self, telegram_id: int, username: str | None, mode: str, value: str | None) -> None:
        await self.execute(
            """
            INSERT INTO special_prices(telegram_id, username, mode, value, created_at)
            VALUES(?,?,?,?,?)
            ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username, mode=excluded.mode, value=excluded.value
            """,
            (telegram_id, username, mode, value, utcnow()),
        )

    async def remove_special_price(self, telegram_id: int) -> None:
        await self.execute("DELETE FROM special_prices WHERE telegram_id=?", (telegram_id,))

    async def stats(self) -> dict[str, Any]:
        row = await self.fetchone(
            """
            SELECT
                COUNT(*) total_orders,
                COALESCE(SUM(CASE WHEN status='success' THEN 1 ELSE 0 END),0) success_orders,
                COALESCE(SUM(CASE WHEN status='success' THEN stars ELSE 0 END),0) sold_stars,
                COALESCE(SUM(CASE WHEN status='success' THEN CAST(total_rub AS REAL) ELSE 0 END),0) revenue,
                COALESCE(SUM(CASE WHEN status='success' THEN CAST(expected_cost_rub AS REAL) ELSE 0 END),0) expected_cost
            FROM orders
            """
        )
        today = await self.fetchone(
            """
            SELECT
                COUNT(*) orders,
                COALESCE(SUM(CASE WHEN status='success' THEN stars ELSE 0 END),0) sold_stars,
                COALESCE(SUM(CASE WHEN status='success' THEN CAST(total_rub AS REAL) ELSE 0 END),0) revenue
            FROM orders
            WHERE date(created_at)=date('now')
            """
        )
        users = await self.fetchone("SELECT COUNT(*) count FROM users")
        pending = await self.fetchone("SELECT COUNT(*) count FROM orders WHERE status IN ('awaiting_payment','paid','fulfilling')")
        return {
            "total_orders": row["total_orders"],
            "success_orders": row["success_orders"],
            "sold_stars": row["sold_stars"],
            "revenue": Decimal(str(row["revenue"])),
            "expected_cost": Decimal(str(row["expected_cost"])),
            "today_orders": today["orders"],
            "today_stars": today["sold_stars"],
            "today_revenue": Decimal(str(today["revenue"])),
            "users": users["count"],
            "pending": pending["count"],
        }
