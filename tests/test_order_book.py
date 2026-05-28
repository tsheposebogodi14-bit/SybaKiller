import pytest
from sybakiller.order_book import OrderBook
from sybakiller.types import Fill, Order, OrderStatus, Side, Symbol


def test_register_and_open_orders(book: OrderBook, sample_order: Order) -> None:
    book.register_order(sample_order)
    open_orders = book.open_orders(Symbol("BTCUSDT"))
    assert len(open_orders) == 1
    assert open_orders[0].status is OrderStatus.OPEN


def test_partial_then_full_fill(book: OrderBook, sample_order: Order) -> None:
    book.register_order(sample_order)
    book.apply_fill(
        Fill(
            order_id=sample_order.client_order_id,
            symbol=Symbol("BTCUSDT"),
            side=Side.BUY,
            quantity=0.4,
            price=50_000.0,
        )
    )
    order = book.get_order(sample_order.client_order_id)
    assert order is not None
    assert order.status is OrderStatus.PARTIALLY_FILLED
    assert order.filled_quantity == pytest.approx(0.4)

    book.apply_fill(
        Fill(
            order_id=sample_order.client_order_id,
            symbol=Symbol("BTCUSDT"),
            side=Side.BUY,
            quantity=0.6,
            price=50_100.0,
        )
    )
    order = book.get_order(sample_order.client_order_id)
    assert order is not None
    assert order.status is OrderStatus.FILLED
    pos = book.position(Symbol("BTCUSDT"))
    assert pos.quantity == pytest.approx(1.0)


def test_cancel_open_order(book: OrderBook, sample_order: Order) -> None:
    book.register_order(sample_order)
    cancelled = book.cancel_order(sample_order.client_order_id)
    assert cancelled.status is OrderStatus.CANCELLED
    assert book.open_orders() == []


def test_cannot_fill_terminal(book: OrderBook, sample_order: Order) -> None:
    book.register_order(sample_order)
    book.cancel_order(sample_order.client_order_id)
    with pytest.raises(ValueError, match="terminal"):
        book.apply_fill(
            Fill(
                order_id=sample_order.client_order_id,
                symbol=Symbol("BTCUSDT"),
                side=Side.BUY,
                quantity=1.0,
                price=50_000.0,
            )
        )


def test_duplicate_order_id(book: OrderBook, sample_order: Order) -> None:
    book.register_order(sample_order)
    dup = Order(
        client_order_id=sample_order.client_order_id,
        symbol=Symbol("BTCUSDT"),
        side=Side.SELL,
        quantity=1.0,
        price=49_000.0,
    )
    with pytest.raises(ValueError, match="duplicate"):
        book.register_order(dup)
