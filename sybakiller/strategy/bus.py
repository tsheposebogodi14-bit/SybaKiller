"""Multi-tenant signal bus — aggregate intents before execution."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from sybakiller.strategy.signals import TradeSignal

logger = logging.getLogger(__name__)


@dataclass(order=True)
class _QueuedSignal:
    priority: int
    seq: int
    signal: TradeSignal = field(compare=False)


class MultiTenantSignalBus:
    """
    Ingest signals from multiple tenants/sources (Oodi-style fan-in).

    Higher priority signals are executed first; FIFO within same priority.
    """

    def __init__(self, max_queue: int = 10_000) -> None:
        self._queue: asyncio.PriorityQueue[_QueuedSignal] = asyncio.PriorityQueue(maxsize=max_queue)
        self._seq = 0
        self._sources: set[tuple[str, str]] = set()
        self._published = 0
        self._dropped = 0

    def register_source(self, tenant_id: str, source_id: str) -> None:
        self._sources.add((tenant_id, source_id))
        logger.info("signal source registered: %s/%s", tenant_id, source_id)

    @property
    def registered_sources(self) -> set[tuple[str, str]]:
        return set(self._sources)

    async def publish(self, signal: TradeSignal) -> bool:
        key = (signal.tenant_id, signal.source_id)
        if self._sources and key not in self._sources:
            logger.warning("reject signal from unregistered source: %s", key)
            return False
        self._seq += 1
        item = _QueuedSignal(
            priority=-signal.priority,
            seq=self._seq,
            signal=signal,
        )
        try:
            self._queue.put_nowait(item)
            self._published += 1
            return True
        except asyncio.QueueFull:
            self._dropped += 1
            logger.warning("signal bus full; dropped %s", signal.signal_id)
            return False

    async def consume(self) -> TradeSignal:
        item = await self._queue.get()
        return item.signal

    def stats(self) -> dict[str, int]:
        return {
            "published": self._published,
            "dropped": self._dropped,
            "queued": self._queue.qsize(),
        }
