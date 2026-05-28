"""Token-bucket rate limiting keyed by venue profile buckets."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from sybakiller.venues.types import RateLimitProfile


@dataclass
class _BucketState:
    tokens: float
    last_refill: float


class VenueRateLimiter:
    """Async rate limiter — one limiter instance per adapter/venue."""

    def __init__(self, profile: RateLimitProfile) -> None:
        self._limits = {
            "order": profile.orders_per_second,
            "cancel": profile.cancels_per_second,
            "rest": profile.rest_per_second,
        }
        self._burst = profile.burst
        self._states: dict[str, _BucketState] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, bucket: str) -> None:
        rate = self._limits.get(bucket, self._limits["rest"])
        while True:
            async with self._lock:
                now = time.monotonic()
                state = self._states.setdefault(
                    bucket, _BucketState(tokens=float(self._burst), last_refill=now)
                )
                elapsed = now - state.last_refill
                state.tokens = min(
                    float(self._burst),
                    state.tokens + elapsed * rate,
                )
                state.last_refill = now
                if state.tokens >= 1.0:
                    state.tokens -= 1.0
                    return
                deficit = 1.0 - state.tokens
                wait = deficit / rate if rate > 0 else 0.1
            await asyncio.sleep(wait)
