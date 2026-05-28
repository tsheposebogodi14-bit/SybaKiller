"""Wire engine from environment — live feed by default."""

from __future__ import annotations

import logging

from sybakiller.config import Settings, get_settings
from sybakiller.engine import TradingEngine
from sybakiller.exchanges.factory import create_exchange_adapter
from sybakiller.feeds.factory import create_market_feed

logger = logging.getLogger(__name__)


def build_engine(settings: Settings | None = None) -> TradingEngine:
    cfg = settings or get_settings()
    engine = TradingEngine()
    feed = create_market_feed(cfg)
    adapter = create_exchange_adapter(cfg)
    engine.wire(adapter, feed=feed, settings=cfg)
    if adapter is None:
        logger.warning(
            "live execution disabled: set BINANCE_API_KEY and BINANCE_API_SECRET "
            "for real orders (market data still live)"
        )
    return engine
