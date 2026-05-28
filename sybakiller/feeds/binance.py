"""Binance public WebSocket bookTicker — live bid/ask, no API key."""

from __future__ import annotations

import asyncio
import json
import logging
from time import time
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

from sybakiller.adapters.base import MarketDataAdapter
from sybakiller.types import Symbol, Tick
from sybakiller.venues.types import BINANCE_CEX, VenueProfile

logger = logging.getLogger(__name__)

BINANCE_WS_BASE = "wss://stream.binance.com:9443"
BINANCE_TESTNET_WS_BASE = "wss://stream.testnet.binance.vision"


def parse_binance_book_ticker(payload: dict[str, Any]) -> Tick:
    """Parse bookTicker JSON (direct or wrapped in combined stream)."""
    data = payload.get("data", payload)
    symbol = str(data["s"])
    return Tick(
        symbol=Symbol(symbol),
        bid=float(data["b"]),
        ask=float(data["a"]),
        timestamp=time(),
    )


def _stream_url(symbols: list[str], *, testnet: bool = False) -> str:
    normalized = [s.strip().lower() for s in symbols if s.strip()]
    if not normalized:
        raise ValueError("at least one symbol required for live feed")
    streams = "/".join(f"{sym}@bookTicker" for sym in normalized)
    base = BINANCE_TESTNET_WS_BASE if testnet else BINANCE_WS_BASE
    if len(normalized) == 1:
        return f"{base}/ws/{streams}"
    return f"{base}/stream?streams={streams}"


class BinanceLiveFeed(MarketDataAdapter):
    """Streams live bookTicker updates from Binance (CEX combined-stream protocol)."""

    def __init__(
        self,
        symbols: list[str],
        *,
        testnet: bool = False,
        queue_size: int = 4096,
        venue: VenueProfile = BINANCE_CEX,
    ) -> None:
        self._venue = venue
        self._symbols = symbols
        self._testnet = testnet
        self._queue: asyncio.Queue[Tick] = asyncio.Queue(maxsize=queue_size)
        self._task: asyncio.Task[None] | None = None
        self._connected = False
        self._ticks_received = 0
        self._last_error: str | None = None

    @property
    def venue(self) -> VenueProfile:
        return self._venue

    @property
    def ticks_received(self) -> int:
        return self._ticks_received

    @property
    def last_error(self) -> str | None:
        return self._last_error

    async def connect(self) -> None:
        if self._connected:
            return
        self._connected = True
        self._task = asyncio.create_task(self._run_forever(), name="binance-live-feed")

    async def disconnect(self) -> None:
        self._connected = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def next_tick(self) -> Tick | None:
        if not self._connected:
            return None
        return await self._queue.get()

    async def _run_forever(self) -> None:
        url = _stream_url(self._symbols, testnet=self._testnet)
        backoff = 1.0
        while self._connected:
            try:
                async with websockets.connect(
                    url,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                ) as ws:
                    logger.info("binance feed connected: %s", url)
                    backoff = 1.0
                    self._last_error = None
                    await self._consume(ws)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._last_error = str(exc)
                logger.warning("binance feed error: %s; reconnect in %.1fs", exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    async def _consume(self, ws: ClientConnection) -> None:
        async for raw in ws:
            if not self._connected:
                break
            try:
                message = json.loads(raw)
                tick = parse_binance_book_ticker(message)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                logger.debug("skip malformed tick: %s", exc)
                continue
            self._ticks_received += 1
            try:
                self._queue.put_nowait(tick)
            except asyncio.QueueFull:
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                self._queue.put_nowait(tick)
