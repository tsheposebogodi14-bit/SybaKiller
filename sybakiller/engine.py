"""Orchestrates ingest → strategy signals → risk → gateway."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field

from sybakiller.adapters.base import ExchangeAdapter
from sybakiller.config import Settings, get_settings
from sybakiller.exchanges.binance import BinanceExchangeAdapter
from sybakiller.gateway import ExecutionGateway, GatewayResult
from sybakiller.market_data import MarketDataFeed
from sybakiller.order_book import OrderBook
from sybakiller.risk import RiskManager
from sybakiller.state.recovery import StateRecovery
from sybakiller.state.store import RedisStateStore
from sybakiller.strategy.bus import MultiTenantSignalBus
from sybakiller.strategy.router import SignalExecutionRouter
from sybakiller.types import Order, OrderId, Symbol, Tick

logger = logging.getLogger(__name__)

TickHandler = Callable[[Tick], Coroutine[None, None, None]]


@dataclass
class TradingEngine:
    book: OrderBook = field(default_factory=OrderBook)
    risk: RiskManager = field(default_factory=RiskManager)
    gateway: ExecutionGateway | None = None
    feed: MarketDataFeed | None = None
    signal_bus: MultiTenantSignalBus = field(default_factory=MultiTenantSignalBus)
    signal_router: SignalExecutionRouter | None = None
    last_tick: Tick | None = None
    tick_count: int = 0
    _settings: Settings = field(default_factory=get_settings)
    _state_store: RedisStateStore | None = None
    _recovery: StateRecovery | None = None
    _running: bool = False
    _feed_task: asyncio.Task[None] | None = None
    _snapshot_task: asyncio.Task[None] | None = None
    _tick_handlers: list[TickHandler] = field(default_factory=list)
    _strategies: list[object] = field(default_factory=list)

    def wire(
        self,
        adapter: ExchangeAdapter | None = None,
        feed: MarketDataFeed | None = None,
        settings: Settings | None = None,
    ) -> None:
        if settings is not None:
            self._settings = settings
        self._state_store = RedisStateStore(self._settings)
        self._recovery = StateRecovery(self._state_store)

        if adapter is not None:
            self.gateway = ExecutionGateway(book=self.book, risk=self.risk, adapter=adapter)
            self.gateway.set_on_change(self._schedule_snapshot)
            execute = self._execute_order
            self.signal_router = SignalExecutionRouter(
                self.signal_bus,
                execute,
                on_result=self._on_signal_result,
            )

        self.feed = feed

    def register_strategy(self, strategy: object) -> None:
        """Attach a Strategy; must expose on_tick(tick) and tenant/source ids."""
        self._strategies.append(strategy)
        tenant = getattr(strategy, "tenant_id", "default")
        source = getattr(strategy, "source_id", strategy.__class__.__name__)
        self.signal_bus.register_source(tenant, source)

    def on_tick(self, handler: TickHandler) -> None:
        self._tick_handlers.append(handler)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def live_execution_enabled(self) -> bool:
        return self.gateway is not None

    async def recover_state(self) -> int:
        if self._recovery is None or self._state_store is None:
            return 0
        snapshot = await self._recovery.load_snapshot()
        if snapshot is None:
            return 0
        if snapshot.last_tick:
            self.last_tick = Tick(
                symbol=Symbol(str(snapshot.last_tick["symbol"])),
                bid=float(snapshot.last_tick["bid"]),
                ask=float(snapshot.last_tick["ask"]),
                timestamp=float(snapshot.last_tick["timestamp"]),
            )
        self.tick_count = snapshot.tick_count
        return self._recovery.apply(snapshot, self.book, self.risk, self.gateway)

    async def persist_snapshot(self) -> bool:
        if self._state_store is None or self._recovery is None:
            return False
        snapshot = StateRecovery.build_snapshot(
            tenant_id=self._settings.syba_tenant_id,
            book=self.book,
            risk=self.risk,
            gateway=self.gateway,
            tick_count=self.tick_count,
            last_tick=self.last_tick,
        )
        return await self._state_store.save(snapshot)

    def _schedule_snapshot(self) -> None:
        if self._running and self._settings.state_snapshot_enabled:
            asyncio.create_task(self.persist_snapshot())

    async def _on_signal_result(self, _signal: object, _result: GatewayResult) -> None:
        await self.persist_snapshot()

    async def _execute_order(self, order: Order) -> GatewayResult:
        if self.gateway is None:
            return GatewayResult(False, order.client_order_id, "execution disabled")
        return await self.gateway.place_order(order)

    async def start(self) -> None:
        if self.feed is None and self.gateway is None:
            raise RuntimeError("wire a live feed and/or exchange adapter first")

        restored = await self.recover_state()
        if restored:
            logger.info("monitoring %d recovered open orders", restored)

        if self.feed is not None:
            await self.feed.connect()
            self._feed_task = asyncio.create_task(self._market_data_loop(), name="syba-market-data")

        if self.signal_router is not None:
            await self.signal_router.start()

        if self._settings.state_snapshot_enabled and self._state_store is not None:
            self._snapshot_task = asyncio.create_task(
                self._snapshot_loop(), name="syba-state-snapshot"
            )

        for strategy in self._strategies:
            start = getattr(strategy, "start", None)
            if start is not None:
                await start()

        self._running = True

    async def stop(self) -> None:
        self._running = False

        for strategy in self._strategies:
            stop = getattr(strategy, "stop", None)
            if stop is not None:
                await stop()

        if self.signal_router is not None:
            await self.signal_router.stop()

        if self._snapshot_task is not None:
            self._snapshot_task.cancel()
            try:
                await self._snapshot_task
            except asyncio.CancelledError:
                pass
            self._snapshot_task = None

        await self.persist_snapshot()

        if self._feed_task is not None:
            self._feed_task.cancel()
            try:
                await self._feed_task
            except asyncio.CancelledError:
                pass
            self._feed_task = None

        if self.feed is not None:
            await self.feed.disconnect()

        if self.gateway is not None:
            await self.gateway.adapter.close()

        if self._state_store is not None:
            await self._state_store.close()

    async def _snapshot_loop(self) -> None:
        interval = self._settings.state_snapshot_interval_sec
        while self._running:
            await asyncio.sleep(interval)
            await self.persist_snapshot()

    async def _market_data_loop(self) -> None:
        if self.feed is None:
            return
        while self._running:
            try:
                tick = await self.feed.next_tick()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("market data loop error: %s", exc)
                await asyncio.sleep(1.0)
                continue
            if tick is None:
                await asyncio.sleep(0.05)
                continue
            self.last_tick = tick
            self.tick_count += 1
            if self.gateway is not None and isinstance(
                self.gateway.adapter, BinanceExchangeAdapter
            ):
                self.gateway.adapter.note_quote(str(tick.symbol), tick.bid, tick.ask)

            for strategy in self._strategies:
                on_tick = getattr(strategy, "on_tick", None)
                if on_tick is not None:
                    try:
                        await on_tick(tick)
                    except Exception as exc:
                        logger.warning("strategy error: %s", exc)

            for handler in self._tick_handlers:
                try:
                    await handler(tick)
                except Exception as exc:
                    logger.warning("tick handler error: %s", exc)

    async def poll_market_data(self) -> Tick | None:
        return self.last_tick

    async def submit(self, order: Order) -> GatewayResult:
        if self.gateway is None:
            raise RuntimeError("live execution not configured")
        return await self.gateway.place_order(order)

    async def cancel(self, order_id: OrderId) -> GatewayResult:
        if self.gateway is None:
            raise RuntimeError("live execution not configured")
        return await self.gateway.cancel_order(order_id)
