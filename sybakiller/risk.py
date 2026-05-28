"""Pre-trade risk checks."""

from __future__ import annotations

from dataclasses import dataclass

from sybakiller.order_book import OrderBook
from sybakiller.types import Order, Side


@dataclass(slots=True)
class RiskLimits:
    max_order_notional: float = 100_000.0
    max_position_notional: float = 500_000.0
    max_orders_per_second: float = 50.0
    max_open_orders: int = 100


@dataclass(slots=True)
class RiskVerdict:
    allowed: bool
    reason: str = ""


class RiskManager:
    def __init__(self, limits: RiskLimits | None = None) -> None:
        self._limits = limits or RiskLimits()
        self._kill_switch = False
        self._order_timestamps: list[float] = []

    @property
    def kill_switch_engaged(self) -> bool:
        return self._kill_switch

    def engage_kill_switch(self) -> None:
        self._kill_switch = True

    def release_kill_switch(self) -> None:
        self._kill_switch = False

    def check_order(self, order: Order, book: OrderBook, now: float) -> RiskVerdict:
        if self._kill_switch:
            return RiskVerdict(False, "kill switch engaged")

        notional = order.quantity * order.price
        if notional > self._limits.max_order_notional:
            return RiskVerdict(False, f"order notional {notional} exceeds limit")

        open_count = len(book.open_orders())
        if open_count >= self._limits.max_open_orders:
            return RiskVerdict(False, "max open orders reached")

        projected = self._projected_position_notional(order, book)
        if projected > self._limits.max_position_notional:
            return RiskVerdict(False, f"projected position notional {projected} exceeds limit")

        self._prune_rate_window(now)
        if len(self._order_timestamps) >= int(self._limits.max_orders_per_second):
            return RiskVerdict(False, "order rate limit exceeded")

        return RiskVerdict(True)

    def record_order_sent(self, now: float) -> None:
        self._prune_rate_window(now)
        self._order_timestamps.append(now)

    def _projected_position_notional(self, order: Order, book: OrderBook) -> float:
        pos = book.position(order.symbol)
        delta = order.quantity if order.side is Side.BUY else -order.quantity
        projected_qty = pos.quantity + delta
        return abs(projected_qty * order.price)

    def _prune_rate_window(self, now: float) -> None:
        cutoff = now - 1.0
        self._order_timestamps = [t for t in self._order_timestamps if t > cutoff]
