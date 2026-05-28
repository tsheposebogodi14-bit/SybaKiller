"""FastAPI control plane — live market data, optional live execution."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import orjson
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sybakiller.bootstrap import build_engine
from sybakiller.config import get_settings
from sybakiller.engine import TradingEngine
from sybakiller.redis_ticks import close_redis, publish_tick
from sybakiller.strategy.signals import TradeSignal
from sybakiller.types import Order, OrderId, OrderStatus, Side, Symbol, Tick

logging.basicConfig(level=get_settings().syba_log_level)
logger = logging.getLogger(__name__)

settings = get_settings()
engine: TradingEngine = build_engine(settings)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async def _redis_publish(tick: Tick) -> None:
        await publish_tick(settings, tick)

    engine.on_tick(_redis_publish)
    await engine.start()
    logger.info(
        "engine started | feed=%s symbols=%s execution=%s",
        settings.market_data_provider,
        settings.market_data_symbols,
        engine.live_execution_enabled,
    )
    yield
    await engine.stop()
    await close_redis()
    logger.info("engine stopped")


app = FastAPI(title="SybaKiller Control Plane", lifespan=lifespan)


class OrderRequest(BaseModel):
    symbol: str
    side: Side
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)


class SignalRequest(BaseModel):
    """External signal ingest (Oodi / other tenants) — routed via bus, not direct gateway."""

    tenant_id: str = Field(default="default")
    source_id: str
    symbol: str
    side: Side
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    priority: int = 0


def _tick_payload(tick: Tick) -> dict[str, Any]:
    return {
        "symbol": str(tick.symbol),
        "bid": tick.bid,
        "ask": tick.ask,
        "mid": (tick.bid + tick.ask) / 2.0,
        "spread": tick.ask - tick.bid,
        "timestamp": tick.timestamp,
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "live_feed": engine.feed is not None,
        "live_execution": engine.live_execution_enabled,
        "ticks_received": engine.tick_count,
        "signal_bus": engine.signal_bus.stats(),
        "signals_processed": (engine.signal_router.processed_count if engine.signal_router else 0),
    }


@app.get("/status")
async def status() -> dict[str, Any]:
    positions = {
        sym: {"quantity": pos.quantity, "average_price": pos.average_price}
        for sym, pos in engine.book.all_positions().items()
    }
    open_orders = [
        {
            "client_order_id": o.client_order_id,
            "symbol": str(o.symbol),
            "side": o.side.value,
            "quantity": o.quantity,
            "filled_quantity": o.filled_quantity,
            "status": o.status.value,
        }
        for o in engine.book.open_orders()
    ]
    feed_meta: dict[str, Any] = {
        "provider": settings.market_data_provider,
        "symbols": settings.market_data_symbols_list,
    }
    if engine.feed is not None:
        feed_meta["ticks_received"] = engine.tick_count
        last_error = getattr(engine.feed, "last_error", None)
        if last_error:
            feed_meta["last_error"] = last_error

    return {
        "running": engine.is_running,
        "kill_switch": engine.risk.kill_switch_engaged,
        "last_tick": _tick_payload(engine.last_tick) if engine.last_tick else None,
        "feed": feed_meta,
        "positions": positions,
        "open_orders": open_orders,
        "signal_bus": engine.signal_bus.stats(),
        "signal_sources": [
            {"tenant_id": t, "source_id": s} for t, s in engine.signal_bus.registered_sources
        ],
        "state_snapshot": settings.state_snapshot_enabled,
    }


@app.post("/signals")
async def ingest_signal(body: SignalRequest) -> dict[str, Any]:
    """
    Multi-tenant signal fan-in.

    Strategies inside the process publish the same way; external systems
    (e.g. Project Oodi) can POST here before execution.
    """
    if engine.signal_router is None:
        raise HTTPException(503, "execution router not configured")
    signal = TradeSignal(
        tenant_id=body.tenant_id,
        source_id=body.source_id,
        symbol=Symbol(body.symbol.upper()),
        side=body.side,
        quantity=body.quantity,
        price=body.price,
        priority=body.priority,
    )
    engine.signal_bus.register_source(body.tenant_id, body.source_id)
    accepted = await engine.signal_bus.publish(signal)
    if not accepted:
        raise HTTPException(429, "signal bus full or unregistered source")
    return {
        "signal_id": signal.signal_id,
        "queued": True,
        "bus": engine.signal_bus.stats(),
    }


@app.websocket("/ws/market")
async def ws_market(websocket: WebSocket) -> None:
    """Push live ticks to connected clients."""
    await websocket.accept()
    queue: asyncio.Queue[Tick] = asyncio.Queue(maxsize=512)

    async def push_tick(tick: Tick) -> None:
        try:
            queue.put_nowait(tick)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            queue.put_nowait(tick)

    engine.on_tick(push_tick)
    try:
        if engine.last_tick is not None:
            await websocket.send_bytes(
                orjson.dumps({"type": "tick", "data": _tick_payload(engine.last_tick)})
            )
        while True:
            tick = await queue.get()
            await websocket.send_bytes(orjson.dumps({"type": "tick", "data": _tick_payload(tick)}))
    except WebSocketDisconnect:
        pass
    finally:
        if push_tick in engine._tick_handlers:
            engine._tick_handlers.remove(push_tick)


@app.post("/kill")
async def engage_kill() -> dict[str, bool]:
    engine.risk.engage_kill_switch()
    return {"kill_switch": True}


@app.post("/kill/release")
async def release_kill() -> dict[str, bool]:
    engine.risk.release_kill_switch()
    return {"kill_switch": False}


@app.post("/orders")
async def place_order(body: OrderRequest) -> dict[str, Any]:
    if engine.gateway is None:
        raise HTTPException(
            503,
            "live execution not configured: set BINANCE_API_KEY and BINANCE_API_SECRET",
        )
    order = Order(
        symbol=Symbol(body.symbol.upper()),
        side=body.side,
        quantity=body.quantity,
        price=body.price,
    )
    result = await engine.gateway.place_order(order)
    order_id = result.order_id
    if not result.success or order_id is None:
        raise HTTPException(400, result.message)
    stored = engine.book.get_order(order_id)
    return {
        "client_order_id": order_id,
        "status": stored.status.value if stored else OrderStatus.REJECTED.value,
        "message": result.message,
    }


@app.delete("/orders/{client_order_id}")
async def cancel_order(client_order_id: str) -> dict[str, Any]:
    if engine.gateway is None:
        raise HTTPException(503, "live execution not configured")
    result = await engine.gateway.cancel_order(OrderId(client_order_id))
    if not result.success:
        raise HTTPException(400, result.message)
    return {"client_order_id": client_order_id, "message": result.message}


def run() -> None:
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.syba_api_host,
        port=settings.syba_api_port,
        reload=False,
    )
