import pytest
from sybakiller.exchanges.paper import PaperExchangeAdapter
from sybakiller.gateway import ExecutionGateway
from sybakiller.order_book import OrderBook
from sybakiller.risk import RiskManager
from sybakiller.types import Order, OrderId, OrderStatus


@pytest.fixture
def gateway(book: OrderBook, risk: RiskManager, adapter) -> ExecutionGateway:
    return ExecutionGateway(book=book, risk=risk, adapter=adapter)


@pytest.mark.asyncio
async def test_place_order_success(gateway: ExecutionGateway, sample_order: Order, adapter) -> None:
    result = await gateway.place_order(sample_order, now=10.0)
    assert result.success
    stored = gateway.book.get_order(sample_order.client_order_id)
    assert stored is not None
    assert stored.status is OrderStatus.OPEN
    assert len(adapter.submitted) == 1


@pytest.mark.asyncio
async def test_kill_switch_rejects(gateway: ExecutionGateway, sample_order: Order) -> None:
    gateway.risk.engage_kill_switch()
    result = await gateway.place_order(sample_order, now=10.0)
    assert not result.success
    assert gateway.book.get_order(sample_order.client_order_id) is None


@pytest.mark.asyncio
async def test_idempotent_cancel(gateway: ExecutionGateway, sample_order: Order, adapter) -> None:
    await gateway.place_order(sample_order, now=10.0)
    first = await gateway.cancel_order(sample_order.client_order_id)
    second = await gateway.cancel_order(sample_order.client_order_id)
    assert first.success
    assert second.success
    assert second.message == "already cancelled"
    assert len(adapter.cancelled) == 1


class _FailingAdapter(PaperExchangeAdapter):
    async def submit_order(self, order: Order) -> OrderId:
        raise RuntimeError("binance 400: {'code': -1013}")


@pytest.mark.asyncio
async def test_exchange_error_rejected(
    book: OrderBook, risk: RiskManager, sample_order: Order
) -> None:
    gateway = ExecutionGateway(book=book, risk=risk, adapter=_FailingAdapter())
    result = await gateway.place_order(sample_order, now=10.0)
    assert not result.success
    assert "binance 400" in result.message
    stored = gateway.book.get_order(sample_order.client_order_id)
    assert stored is not None
    assert stored.status is OrderStatus.REJECTED


@pytest.mark.asyncio
async def test_replace_order(gateway: ExecutionGateway, sample_order: Order) -> None:
    await gateway.place_order(sample_order, now=10.0)
    old_id = sample_order.client_order_id
    result = await gateway.replace_order(old_id, quantity=2.0, price=49_500.0)
    assert result.success
    old = gateway.book.get_order(old_id)
    assert old is not None
    assert old.status is OrderStatus.CANCELLED
    new = gateway.book.get_order(result.order_id)
    assert new is not None
    assert new.quantity == pytest.approx(2.0)
