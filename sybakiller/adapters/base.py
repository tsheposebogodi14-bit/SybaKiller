"""Extensible adapter contracts for execution and market data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from sybakiller.adapters.rate_limit import VenueRateLimiter
from sybakiller.types import Order, OrderId, Tick
from sybakiller.venues.types import VenueProfile, WsProtocol


class ExchangeAdapter(ABC):
    """
    Execution venue adapter.

    Subclasses implement venue-specific REST/FIX semantics while the gateway
    handles risk, idempotency, and local book state.
    """

    @property
    @abstractmethod
    def venue(self) -> VenueProfile:
        """Venue metadata (kind, rate limits, cancel semantics)."""

    @property
    def rate_limiter(self) -> VenueRateLimiter:
        return VenueRateLimiter(self.venue.rate_limits)

    @abstractmethod
    async def submit_order(self, order: Order) -> OrderId:
        """Send order to venue; return exchange order id."""

    @abstractmethod
    async def cancel_order(
        self,
        exchange_order_id: OrderId,
        *,
        symbol: str | None = None,
    ) -> bool:
        """Cancel on venue. Pass symbol when venue.requires_symbol_on_cancel."""

    async def replace_order(
        self,
        exchange_order_id: OrderId,
        order: Order,
    ) -> OrderId | None:
        """Optional native replace; return None to use gateway cancel+submit."""
        if not self.venue.supports_replace:
            return None
        return None

    async def reconcile_open_orders(self) -> list[dict[str, Any]]:
        """Optional: fetch open orders from venue after restart."""
        return []

    async def close(self) -> None:
        """Release HTTP sessions / FIX connections."""


class MarketDataAdapter(ABC):
    """
    Market-data ingest — decoupled from execution.

    CEX (Binance) vs ECN feeds differ in WebSocket URL shape and message format;
    subclasses encapsulate that while exposing a uniform Tick stream.
    """

    @property
    @abstractmethod
    def venue(self) -> VenueProfile:
        """Venue this feed connects to."""

    @property
    def ws_protocol(self) -> WsProtocol:
        return self.venue.ws_protocol

    @abstractmethod
    async def connect(self) -> None:
        """Establish feed connection."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close feed connection."""

    @abstractmethod
    async def next_tick(self) -> Tick | None:
        """Return next tick (blocks until available)."""

    async def subscribe(self, symbols: list[str]) -> None:
        """Optional dynamic subscribe (ECN session-oriented feeds)."""

    def max_subscriptions(self) -> int:
        return self.venue.rate_limits.ws_subscriptions_max
