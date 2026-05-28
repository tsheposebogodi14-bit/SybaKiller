"""Shared domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from time import time
from typing import NewType
from uuid import uuid4

OrderId = NewType("OrderId", str)
Symbol = NewType("Symbol", str)


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(StrEnum):
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass(slots=True)
class Order:
    symbol: Symbol
    side: Side
    quantity: float
    price: float
    client_order_id: OrderId = field(default_factory=lambda: OrderId(str(uuid4())))
    filled_quantity: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    created_at: float = field(default_factory=time)

    @property
    def remaining_quantity(self) -> float:
        return max(0.0, self.quantity - self.filled_quantity)

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
        )


@dataclass(slots=True)
class Fill:
    order_id: OrderId
    symbol: Symbol
    side: Side
    quantity: float
    price: float
    timestamp: float = field(default_factory=time)


@dataclass(slots=True)
class Position:
    symbol: Symbol
    quantity: float = 0.0
    average_price: float = 0.0

    def apply_fill(self, side: Side, quantity: float, price: float) -> None:
        signed_qty = quantity if side is Side.BUY else -quantity
        new_qty = self.quantity + signed_qty
        if self.quantity == 0.0 or (self.quantity > 0) == (signed_qty > 0):
            total_cost = self.average_price * abs(self.quantity) + price * quantity
            denom = abs(new_qty)
            self.average_price = total_cost / denom if denom > 0 else 0.0
        elif abs(signed_qty) >= abs(self.quantity):
            self.average_price = price if new_qty != 0 else 0.0
        self.quantity = new_qty


@dataclass(slots=True)
class Tick:
    symbol: Symbol
    bid: float
    ask: float
    timestamp: float = field(default_factory=time)
