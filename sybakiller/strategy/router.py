"""Routes bus signals to execution gateway — strategies never touch the gateway."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from sybakiller.gateway import GatewayResult
from sybakiller.strategy.bus import MultiTenantSignalBus
from sybakiller.strategy.signals import TradeSignal
from sybakiller.types import Order, OrderStatus

logger = logging.getLogger(__name__)

ExecuteFn = Callable[[Order], Awaitable[GatewayResult]]


class SignalExecutionRouter:
    """
    Final execution stage: consume aggregated signals, build orders, call gateway.

    Optional on_result hook for snapshots / metrics without coupling strategies.
    """

    def __init__(
        self,
        bus: MultiTenantSignalBus,
        execute: ExecuteFn,
        *,
        on_result: Callable[[TradeSignal, GatewayResult], Awaitable[None]] | None = None,
    ) -> None:
        self._bus = bus
        self._execute = execute
        self._on_result = on_result
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._processed = 0

    @property
    def processed_count(self) -> int:
        return self._processed

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run(), name="signal-execution-router")

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        while self._running:
            signal = await self._bus.consume()
            order = Order(
                client_order_id=signal.to_order_client_id(),
                symbol=signal.symbol,
                side=signal.side,
                quantity=signal.quantity,
                price=signal.price,
            )
            result = await self._execute(order)
            self._processed += 1
            if not result.success:
                order.status = OrderStatus.REJECTED
                logger.info(
                    "signal %s rejected: %s",
                    signal.signal_id,
                    result.message,
                )
            if self._on_result is not None:
                await self._on_result(signal, result)

    def signal_to_order(self, signal: TradeSignal) -> Order:
        return Order(
            client_order_id=signal.to_order_client_id(),
            symbol=signal.symbol,
            side=signal.side,
            quantity=signal.quantity,
            price=signal.price,
        )
