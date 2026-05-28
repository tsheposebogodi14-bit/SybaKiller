"""Strategy contract — produces signals only, never calls the gateway directly."""

from __future__ import annotations

from abc import ABC, abstractmethod

from sybakiller.strategy.bus import MultiTenantSignalBus
from sybakiller.types import Tick


class Strategy(ABC):
    """
    Latency-sensitive strategies implement on_tick and publish signals.

    Execution is always handled by SignalExecutionRouter so logic stays
    decoupled from risk checks and venue adapters.
    """

    def __init__(self, tenant_id: str, source_id: str, bus: MultiTenantSignalBus) -> None:
        self.tenant_id = tenant_id
        self.source_id = source_id
        self.bus = bus

    @abstractmethod
    async def on_tick(self, tick: Tick) -> None:
        """React to market data; publish TradeSignal via self.bus when ready."""

    async def start(self) -> None:
        """Optional setup hook."""

    async def stop(self) -> None:
        """Optional teardown hook."""
