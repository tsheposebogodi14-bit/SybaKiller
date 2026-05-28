"""Build market data feed from settings."""

from __future__ import annotations

from sybakiller.config import Settings
from sybakiller.feeds.binance import BinanceLiveFeed
from sybakiller.feeds.simulated import SimulatedFeed
from sybakiller.market_data import MarketDataFeed


def create_market_feed(settings: Settings) -> MarketDataFeed:
    provider = settings.market_data_provider.lower()
    if provider == "binance":
        return BinanceLiveFeed(
            settings.market_data_symbols_list,
            testnet=settings.binance_testnet,
        )
    if provider == "simulated":
        return SimulatedFeed()
    raise ValueError(f"unknown MARKET_DATA_PROVIDER: {provider}")
