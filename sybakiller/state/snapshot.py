"""Serializable engine state for restart recovery."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from time import time
from typing import Any

import orjson

from sybakiller.types import OrderStatus


@dataclass
class OrderSnapshot:
    client_order_id: str
    exchange_order_id: str | None
    symbol: str
    side: str
    quantity: float
    price: float
    filled_quantity: float
    status: str


@dataclass
class EngineSnapshot:
    version: int = 1
    tenant_id: str = "default"
    saved_at: float = field(default_factory=time)
    kill_switch: bool = False
    tick_count: int = 0
    last_tick: dict[str, Any] | None = None
    open_orders: list[OrderSnapshot] = field(default_factory=list)
    exchange_id_map: dict[str, str] = field(default_factory=dict)
    positions: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_bytes(self) -> bytes:
        payload = asdict(self)
        return orjson.dumps(payload)

    @classmethod
    def from_bytes(cls, raw: bytes) -> EngineSnapshot:
        data = orjson.loads(raw)
        orders = [OrderSnapshot(**o) for o in data.pop("open_orders", [])]
        return cls(open_orders=orders, **data)

    def open_order_ids(self) -> list[str]:
        return [
            o.client_order_id
            for o in self.open_orders
            if o.status
            in (
                OrderStatus.OPEN.value,
                OrderStatus.PARTIALLY_FILLED.value,
                OrderStatus.PENDING.value,
            )
        ]
