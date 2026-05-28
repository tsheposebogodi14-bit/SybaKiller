"""Persist engine snapshots to Redis."""

from __future__ import annotations

import logging
from typing import Any

from sybakiller.config import Settings
from sybakiller.state.snapshot import EngineSnapshot

logger = logging.getLogger(__name__)


class RedisStateStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Any = None

    def _key(self) -> str:
        return f"syba:snapshot:{self._settings.syba_tenant_id}"

    async def _redis(self) -> Any | None:
        if not self._settings.state_snapshot_enabled:
            return None
        if self._client is not None:
            return self._client
        try:
            from redis.asyncio import Redis

            self._client = Redis.from_url(self._settings.redis_url, decode_responses=False)
            await self._client.ping()
            return self._client
        except Exception as exc:
            logger.warning("redis snapshot store unavailable: %s", exc)
            return None

    async def save(self, snapshot: EngineSnapshot) -> bool:
        client = await self._redis()
        if client is None:
            return False
        try:
            await client.set(self._key(), snapshot.to_bytes())
        except Exception as exc:
            logger.warning("snapshot save failed: %s", exc)
            return False
        logger.debug("state snapshot saved: %s orders", len(snapshot.open_orders))
        return True

    async def load(self) -> EngineSnapshot | None:
        client = await self._redis()
        if client is None:
            return None
        raw = await client.get(self._key())
        if not raw:
            return None
        try:
            return EngineSnapshot.from_bytes(raw)
        except Exception as exc:
            logger.warning("corrupt snapshot ignored: %s", exc)
            return None

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
