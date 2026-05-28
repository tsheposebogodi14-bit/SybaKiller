import pytest
from sybakiller.strategy.bus import MultiTenantSignalBus
from sybakiller.strategy.signals import TradeSignal
from sybakiller.types import Side, Symbol


@pytest.mark.asyncio
async def test_priority_ordering() -> None:
    bus = MultiTenantSignalBus()
    bus.register_source("t1", "low")
    bus.register_source("t1", "high")

    low = TradeSignal(
        tenant_id="t1",
        source_id="low",
        symbol=Symbol("BTCUSDT"),
        side=Side.BUY,
        quantity=1,
        price=1,
        priority=0,
    )
    high = TradeSignal(
        tenant_id="t1",
        source_id="high",
        symbol=Symbol("BTCUSDT"),
        side=Side.SELL,
        quantity=1,
        price=2,
        priority=10,
    )
    await bus.publish(low)
    await bus.publish(high)

    first = await bus.consume()
    assert first.priority == 10
    second = await bus.consume()
    assert second.priority == 0


@pytest.mark.asyncio
async def test_unregistered_source_rejected() -> None:
    bus = MultiTenantSignalBus()
    bus.register_source("t1", "a")
    signal = TradeSignal(
        tenant_id="t1",
        source_id="unknown",
        symbol=Symbol("ETHUSDT"),
        side=Side.BUY,
        quantity=1,
        price=1,
    )
    assert await bus.publish(signal) is False
