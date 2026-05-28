from sybakiller.order_book import OrderBook
from sybakiller.risk import RiskLimits, RiskManager
from sybakiller.types import Order, Side, Symbol


def test_kill_switch_blocks(book: OrderBook) -> None:
    risk = RiskManager()
    risk.engage_kill_switch()
    order = Order(symbol=Symbol("ETHUSD"), side=Side.BUY, quantity=1.0, price=3000.0)
    verdict = risk.check_order(order, book, now=1.0)
    assert not verdict.allowed
    assert "kill switch" in verdict.reason


def test_order_notional_limit(book: OrderBook) -> None:
    risk = RiskManager(RiskLimits(max_order_notional=10_000.0))
    order = Order(symbol=Symbol("BTCUSDT"), side=Side.BUY, quantity=1.0, price=50_000.0)
    verdict = risk.check_order(order, book, now=1.0)
    assert not verdict.allowed


def test_rate_limit(book: OrderBook) -> None:
    risk = RiskManager(RiskLimits(max_orders_per_second=2.0))
    order = Order(symbol=Symbol("BTCUSDT"), side=Side.BUY, quantity=0.01, price=100.0)
    assert risk.check_order(order, book, now=1.0).allowed
    risk.record_order_sent(1.0)
    risk.record_order_sent(1.0)
    verdict = risk.check_order(order, book, now=1.1)
    assert not verdict.allowed
