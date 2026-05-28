"""In-memory feed for unit tests only — not used in production."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from sybakiller.adapters.base import MarketDataAdapter
from sybakiller.types import Tick
from sybakiller.venues.types import BINANCE_CEX, VenueProfile


@dataclass
class SimulatedFeed(MarketDataAdapter):
    venue_profile: VenueProfile = BINANCE_CEX
    ticks: deque[Tick] = field(default_factory=deque)
    _connected: bool = False

    @property
    def venue(self) -> VenueProfile:
        return self.venue_profile

    def push(self, tick: Tick) -> None:
        self.ticks.append(tick)

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def next_tick(self) -> Tick | None:
        if not self._connected or not self.ticks:
            return None
        return self.ticks.popleft()
