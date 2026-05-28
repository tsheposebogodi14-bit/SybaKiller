"""Apply snapshots on startup — resume open-order monitoring without history fetch."""

from __future__ import annotations

import logging

from sybakiller.gateway import ExecutionGateway
from sybakiller.order_book import OrderBook
from sybakiller.risk import RiskManager
from sybakiller.state.snapshot import EngineSnapshot, OrderSnapshot
from sybakiller.state.store import RedisStateStore
from sybakiller.types import Order, OrderId, OrderStatus, Position, Side, Symbol, Tick

logger = logging.getLogger(__name__)


class StateRecovery:
    def __init__(self, store: RedisStateStore) -> None:
        self._store = store

    async def load_snapshot(self) -> EngineSnapshot | None:
        return await self._store.load()

    def apply(
        self,
        snapshot: EngineSnapshot,
        book: OrderBook,
        risk: RiskManager,
        gateway: ExecutionGateway | None,
    ) -> int:
        restored = 0
        if snapshot.kill_switch:
            risk.engage_kill_switch()

        for sym, pos_data in snapshot.positions.items():
            book._positions[Symbol(sym)] = Position(
                symbol=Symbol(sym),
                quantity=pos_data.get("quantity", 0.0),
                average_price=pos_data.get("average_price", 0.0),
            )

        for row in snapshot.open_orders:
            if row.status not in (
                OrderStatus.OPEN.value,
                OrderStatus.PARTIALLY_FILLED.value,
                OrderStatus.PENDING.value,
            ):
                continue
            order = self._order_from_snapshot(row)
            book._orders[order.client_order_id] = order
            restored += 1
            if gateway is not None and row.exchange_order_id:
                gateway._exchange_ids[OrderId(row.client_order_id)] = OrderId(row.exchange_order_id)

        logger.info(
            "recovered %d open orders from snapshot (saved_at=%s)",
            restored,
            snapshot.saved_at,
        )
        return restored

    @staticmethod
    def _order_from_snapshot(row: OrderSnapshot) -> Order:
        return Order(
            client_order_id=OrderId(row.client_order_id),
            symbol=Symbol(row.symbol),
            side=Side(row.side),
            quantity=row.quantity,
            price=row.price,
            filled_quantity=row.filled_quantity,
            status=OrderStatus(row.status),
        )

    @staticmethod
    def build_snapshot(
        *,
        tenant_id: str,
        book: OrderBook,
        risk: RiskManager,
        gateway: ExecutionGateway | None,
        tick_count: int,
        last_tick: Tick | None,
    ) -> EngineSnapshot:
        open_rows: list[OrderSnapshot] = []
        exchange_map: dict[str, str] = {}

        for order in book.open_orders():
            ex_id = None
            if gateway is not None:
                ex_id = gateway._exchange_ids.get(order.client_order_id)
                if ex_id is not None:
                    exchange_map[str(order.client_order_id)] = str(ex_id)
            open_rows.append(
                OrderSnapshot(
                    client_order_id=str(order.client_order_id),
                    exchange_order_id=str(ex_id) if ex_id else None,
                    symbol=str(order.symbol),
                    side=order.side.value,
                    quantity=order.quantity,
                    price=order.price,
                    filled_quantity=order.filled_quantity,
                    status=order.status.value,
                )
            )

        positions = {
            str(sym): {"quantity": pos.quantity, "average_price": pos.average_price}
            for sym, pos in book.all_positions().items()
        }

        last_tick_payload = None
        if last_tick is not None:
            last_tick_payload = {
                "symbol": str(last_tick.symbol),
                "bid": last_tick.bid,
                "ask": last_tick.ask,
                "timestamp": last_tick.timestamp,
            }

        return EngineSnapshot(
            tenant_id=tenant_id,
            kill_switch=risk.kill_switch_engaged,
            tick_count=tick_count,
            last_tick=last_tick_payload,
            open_orders=open_rows,
            exchange_id_map=exchange_map,
            positions=positions,
        )
