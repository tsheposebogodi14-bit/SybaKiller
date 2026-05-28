"""Venue classification for adapter implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class VenueKind(StrEnum):
    CEX = "cex"
    ECN = "ecn"
    DEX = "dex"


class WsProtocol(StrEnum):
    """How market-data WebSockets are structured per venue."""

    BINANCE_COMBINED = "binance_combined"
    BINANCE_SINGLE = "binance_single"
    FIX_JSON = "fix_json"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class RateLimitProfile:
    """Per-bucket limits (orders, cancels, REST, WS subscribe)."""

    orders_per_second: float = 10.0
    cancels_per_second: float = 10.0
    rest_per_second: float = 20.0
    ws_subscriptions_max: int = 200
    burst: int = 5


@dataclass(frozen=True, slots=True)
class VenueProfile:
    venue_id: str
    kind: VenueKind
    ws_protocol: WsProtocol
    rate_limits: RateLimitProfile = field(default_factory=RateLimitProfile)
    supports_replace: bool = True
    requires_symbol_on_cancel: bool = True
    # ECN venues often need client-defined session semantics
    session_heartbeat_sec: float = 30.0


BINANCE_CEX = VenueProfile(
    venue_id="binance",
    kind=VenueKind.CEX,
    ws_protocol=WsProtocol.BINANCE_COMBINED,
    rate_limits=RateLimitProfile(
        orders_per_second=10.0,
        cancels_per_second=10.0,
        rest_per_second=20.0,
        ws_subscriptions_max=1024,
        burst=10,
    ),
    supports_replace=True,
    requires_symbol_on_cancel=True,
)

GENERIC_ECN = VenueProfile(
    venue_id="generic_ecn",
    kind=VenueKind.ECN,
    ws_protocol=WsProtocol.FIX_JSON,
    rate_limits=RateLimitProfile(
        orders_per_second=50.0,
        cancels_per_second=50.0,
        rest_per_second=100.0,
        ws_subscriptions_max=50,
        burst=20,
    ),
    supports_replace=False,
    requires_symbol_on_cancel=False,
    session_heartbeat_sec=15.0,
)
