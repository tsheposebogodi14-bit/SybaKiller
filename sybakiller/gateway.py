"""Execution gateway with idempotent cancel/replace."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from time import time

from sybakiller.adapters.base import ExchangeAdapter
from sybakiller.order_book import OrderBook
from sybakiller.risk import RiskManager, RiskVerdict
from sybakiller.types import Order, OrderId, OrderStatus


@dataclass(slots=True)
class GatewayResult:
    success: bool
    order_id: OrderId | None = None
    message: str = ""


@dataclass
class ExecutionGateway:
    book: OrderBook
    risk: RiskManager
    adapter: ExchangeAdapter
    _exchange_ids: dict[OrderId, OrderId] = field(default_factory=dict)
    _order_symbols: dict[OrderId, str] = field(default_factory=dict)
    _cancel_nonce: dict[OrderId, int] = field(default_factory=dict)
    _on_change: Callable[[], None] | None = None

    def set_on_change(self, hook: Callable[[], None]) -> None:
        self._on_change = hook

    def _notify_change(self) -> None:
        if self._on_change is not None:
            self._on_change()

    async def place_order(self, order: Order, now: float | None = None) -> GatewayResult:
        ts = now if now is not None else time()
        verdict: RiskVerdict = self.risk.check_order(order, self.book, ts)
        if not verdict.allowed:
            order.status = OrderStatus.REJECTED
            return GatewayResult(False, order.client_order_id, verdict.reason)

        self.book.register_order(order)
        await self.adapter.rate_limiter.acquire("order")
        exchange_id = await self.adapter.submit_order(order)
        self._exchange_ids[order.client_order_id] = exchange_id
        self._order_symbols[order.client_order_id] = str(order.symbol).upper()
        self.risk.record_order_sent(ts)
        self._notify_change()
        return GatewayResult(True, order.client_order_id, "submitted")

    async def cancel_order(
        self, client_order_id: OrderId, *, idempotent: bool = True
    ) -> GatewayResult:
        order = self.book.get_order(client_order_id)
        if order is None:
            return GatewayResult(False, client_order_id, "unknown order")

        if order.status is OrderStatus.CANCELLED:
            if idempotent:
                return GatewayResult(True, client_order_id, "already cancelled")
            return GatewayResult(False, client_order_id, "already cancelled")

        if order.is_terminal:
            return GatewayResult(False, client_order_id, f"terminal: {order.status}")

        exchange_id = self._exchange_ids.get(client_order_id)
        if exchange_id is not None:
            await self.adapter.rate_limiter.acquire("cancel")
            symbol = self._order_symbols.get(client_order_id)
            if self.adapter.venue.requires_symbol_on_cancel and symbol is None:
                return GatewayResult(False, client_order_id, "missing symbol for cancel")
            nonce = self._cancel_nonce.get(client_order_id, 0) + 1
            self._cancel_nonce[client_order_id] = nonce
            await self.adapter.cancel_order(exchange_id, symbol=symbol)

        self.book.cancel_order(client_order_id)
        self._notify_change()
        return GatewayResult(True, client_order_id, "cancelled")

    async def replace_order(
        self,
        client_order_id: OrderId,
        *,
        quantity: float | None = None,
        price: float | None = None,
    ) -> GatewayResult:
        old = self.book.get_order(client_order_id)
        if old is None:
            return GatewayResult(False, client_order_id, "unknown order")

        exchange_id = self._exchange_ids.get(client_order_id)
        if exchange_id is not None and self.adapter.venue.supports_replace:
            new_order = Order(
                symbol=old.symbol,
                side=old.side,
                quantity=quantity if quantity is not None else old.quantity,
                price=price if price is not None else old.price,
            )
            replaced = await self.adapter.replace_order(exchange_id, new_order)
            if replaced is not None:
                self._exchange_ids[client_order_id] = replaced
                self._notify_change()
                return GatewayResult(True, client_order_id, "replaced")

        cancel_result = await self.cancel_order(client_order_id)
        if not cancel_result.success:
            return cancel_result

        new_order = Order(
            symbol=old.symbol,
            side=old.side,
            quantity=quantity if quantity is not None else old.quantity,
            price=price if price is not None else old.price,
        )
        return await self.place_order(new_order)

    def export_exchange_map(self) -> dict[str, str]:
        return {str(k): str(v) for k, v in self._exchange_ids.items()}
