import time

import pytest
from sybakiller.adapters.rate_limit import VenueRateLimiter
from sybakiller.venues.types import RateLimitProfile


@pytest.mark.asyncio
async def test_rate_limiter_throttles_burst() -> None:
    profile = RateLimitProfile(orders_per_second=5.0, burst=2)
    limiter = VenueRateLimiter(profile)
    start = time.monotonic()
    for _ in range(4):
        await limiter.acquire("order")
    elapsed = time.monotonic() - start
    assert elapsed >= 0.1
