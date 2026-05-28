"""Optional Redis pub/sub for live tick distribution."""

from __future__ import annotations

import logging
from typing import Any

import orjson

from sybakiller.config import Settings
from sybakiller.types import Tick

logger = logging.getLogger(__name__)

CHANNEL = "syba:ticks"
_client: Any = None


async def get_redis(settings: Settings) -> Any | None:
    global _client
    if not settings.redis_ticks_enabled:
        return None
    if _client is not None:
        return _client
    try:
        from redis.asyncio import Redis

        _client = Redis.from_url(settings.redis_url, decode_responses=False)
        await _client.ping()
        return _client
    except Exception as exc:
        logger.warning("redis unavailable for tick publish: %s", exc)
        return None


async def publish_tick(settings: Settings, tick: Tick) -> None:
    client = await get_redis(settings)
    if client is None:
        return
    payload = orjson.dumps(
        {
            "symbol": str(tick.symbol),
            "bid": tick.bid,
            "ask": tick.ask,
            "timestamp": tick.timestamp,
        }
    )
    await client.publish(CHANNEL, payload)


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
