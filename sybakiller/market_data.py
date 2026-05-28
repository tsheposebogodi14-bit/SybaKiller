"""Market data ingest — alias to adapter contract."""

from sybakiller.adapters.base import MarketDataAdapter

# Backward-compatible name used across engine/tests.
MarketDataFeed = MarketDataAdapter

__all__ = ["MarketDataAdapter", "MarketDataFeed"]
