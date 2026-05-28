"""Build exchange adapter when credentials are configured."""

from __future__ import annotations

from sybakiller.adapters.base import ExchangeAdapter
from sybakiller.config import Settings
from sybakiller.exchanges.binance import BinanceExchangeAdapter
from sybakiller.exchanges.paper import PaperExchangeAdapter


def create_exchange_adapter(settings: Settings) -> ExchangeAdapter | None:
    if settings.syba_env.lower() == "test":
        return PaperExchangeAdapter()

    if not settings.binance_api_key or not settings.binance_api_secret:
        return None

    return BinanceExchangeAdapter(
        settings.binance_api_key,
        settings.binance_api_secret,
        testnet=settings.binance_testnet,
    )
