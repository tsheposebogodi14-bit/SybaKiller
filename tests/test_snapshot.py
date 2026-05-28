from sybakiller.config import Settings
from sybakiller.exchanges.paper import PaperExchangeAdapter
from sybakiller.gateway import ExecutionGateway
from sybakiller.order_book import OrderBook
from sybakiller.risk import RiskManager
from sybakiller.state.recovery import StateRecovery
from sybakiller.state.snapshot import EngineSnapshot
from sybakiller.state.store import RedisStateStore
from sybakiller.types import Order, OrderId, OrderStatus, Side, Symbol


def test_snapshot_roundtrip() -> None:
    book = OrderBook()
    risk = RiskManager()
    order = Order(
        symbol=Symbol("BTCUSDT"),
        side=Side.BUY,
        quantity=1.0,
        price=50_000.0,
    )
    book.register_order(order)

    snap = StateRecovery.build_snapshot(
        tenant_id="default",
        book=book,
        risk=risk,
        gateway=None,
        tick_count=42,
        last_tick=None,
    )
    raw = snap.to_bytes()
    loaded = EngineSnapshot.from_bytes(raw)
    assert loaded.tick_count == 42
    assert len(loaded.open_orders) == 1
    assert loaded.open_orders[0].client_order_id == str(order.client_order_id)


def test_recovery_restores_open_orders() -> None:
    book = OrderBook()
    risk = RiskManager()
    order = Order(
        client_order_id=OrderId("cid-1"),
        symbol=Symbol("BTCUSDT"),
        side=Side.BUY,
        quantity=0.5,
        price=40_000.0,
    )
    book.register_order(order)

    snap = StateRecovery.build_snapshot(
        tenant_id="default",
        book=book,
        risk=risk,
        gateway=None,
        tick_count=0,
        last_tick=None,
    )
    snap.exchange_id_map = {"cid-1": "999"}
    snap.open_orders[0].exchange_order_id = "999"

    new_book = OrderBook()
    gateway = ExecutionGateway(
        book=new_book,
        risk=risk,
        adapter=PaperExchangeAdapter(),
    )
    recovery = StateRecovery(RedisStateStore(Settings(_env_file=None)))
    n = recovery.apply(snap, new_book, risk, gateway)
    assert n == 1
    assert gateway._exchange_ids[OrderId("cid-1")] == OrderId("999")
    restored = new_book.get_order(OrderId("cid-1"))
    assert restored is not None
    assert restored.status is OrderStatus.OPEN
