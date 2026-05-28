"""Order and position state — single source of truth."""

from __future__ import annotations

from sybakiller.types import Fill, Order, OrderId, OrderStatus, Position, Symbol


class OrderBook:
    """Tracks open orders and positions per symbol."""

    def __init__(self) -> None:
        self._orders: dict[OrderId, Order] = {}
        self._positions: dict[Symbol, Position] = {}

    def register_order(self, order: Order) -> None:
        if order.client_order_id in self._orders:
            raise ValueError(f"duplicate order id: {order.client_order_id}")
        order.status = OrderStatus.OPEN
        self._orders[order.client_order_id] = order

    def get_order(self, order_id: OrderId) -> Order | None:
        return self._orders.get(order_id)

    def open_orders(self, symbol: Symbol | None = None) -> list[Order]:
        orders = [
            o
            for o in self._orders.values()
            if o.status in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED)
        ]
        if symbol is not None:
            orders = [o for o in orders if o.symbol == symbol]
        return sorted(orders, key=lambda o: o.created_at)

    def cancel_order(self, order_id: OrderId) -> Order:
        order = self._require_order(order_id)
        if order.is_terminal:
            raise ValueError(f"cannot cancel terminal order: {order_id}")
        order.status = OrderStatus.CANCELLED
        return order

    def apply_fill(self, fill: Fill) -> Order:
        order = self._require_order(fill.order_id)
        if order.symbol != fill.symbol:
            raise ValueError("fill symbol mismatch")
        if order.is_terminal:
            raise ValueError(f"cannot fill terminal order: {fill.order_id}")

        fill_qty = min(fill.quantity, order.remaining_quantity)
        if fill_qty <= 0:
            raise ValueError("fill quantity must be positive")

        order.filled_quantity += fill_qty
        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED
        else:
            order.status = OrderStatus.PARTIALLY_FILLED

        position = self._positions.setdefault(fill.symbol, Position(symbol=fill.symbol))
        position.apply_fill(fill.side, fill_qty, fill.price)
        return order

    def position(self, symbol: Symbol) -> Position:
        return self._positions.get(symbol, Position(symbol=symbol))

    def all_positions(self) -> dict[Symbol, Position]:
        return dict(self._positions)

    def _require_order(self, order_id: OrderId) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise KeyError(f"unknown order: {order_id}")
        return order
