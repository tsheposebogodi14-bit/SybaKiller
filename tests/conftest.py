import os

os.environ.setdefault("SYBA_ENV", "test")
os.environ.setdefault("MARKET_DATA_PROVIDER", "simulated")

import pytest
from sybakiller.exchanges.paper import PaperExchangeAdapter
from sybakiller.order_book import OrderBook
from sybakiller.risk import RiskManager
from sybakiller.types import Order, Side, Symbol


@pytest.fixture
def book() -> OrderBook:
    return OrderBook()


@pytest.fixture
def risk() -> RiskManager:
    return RiskManager()


@pytest.fixture
def adapter() -> PaperExchangeAdapter:
    return PaperExchangeAdapter()


@pytest.fixture
def sample_order() -> Order:
    return Order(symbol=Symbol("BTCUSDT"), side=Side.BUY, quantity=1.0, price=50_000.0)
