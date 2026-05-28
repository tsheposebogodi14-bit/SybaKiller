#!/usr/bin/env python3
"""Verify Binance API keys and live market data."""

from __future__ import annotations

import asyncio
import sys

from sybakiller.config import get_settings
from sybakiller.exchanges.constants import BINANCE_API, BINANCE_TESTNET_API
from sybakiller.feeds.binance import BinanceLiveFeed


async def main() -> int:
    settings = get_settings()
    base = BINANCE_TESTNET_API if settings.binance_testnet else BINANCE_API
    mode = "testnet" if settings.binance_testnet else "mainnet"

    if not settings.binance_api_key or not settings.binance_api_secret:
        print("FAIL: BINANCE_API_KEY and BINANCE_API_SECRET are empty in .env")
        print("Run: bash scripts/setup-binance-env.sh")
        return 1

    print(f"Mode: {mode} ({base})")

    import aiohttp

    url = f"{base}/api/v3/account"
    ts = int(__import__("time").time() * 1000)
    query = f"timestamp={ts}"
    import hashlib
    import hmac

    sig = hmac.new(
        settings.binance_api_secret.encode(),
        query.encode(),
        hashlib.sha256,
    ).hexdigest()
    headers = {"X-MBX-APIKEY": settings.binance_api_key}
    async with (
        aiohttp.ClientSession(trust_env=False) as session,
        session.get(f"{url}?{query}&signature={sig}", headers=headers) as resp,
    ):
        body = await resp.json()
        if resp.status != 200:
            print(f"FAIL: account check {resp.status}: {body}")
            return 1
        balances = [b for b in body.get("balances", []) if float(b.get("free", 0)) > 0]
        print(f"OK: API auth — account active ({len(balances)} assets with balance)")

    feed = BinanceLiveFeed(
        settings.market_data_symbols_list,
        testnet=settings.binance_testnet,
    )
    await feed.connect()
    try:
        tick = await asyncio.wait_for(feed.next_tick(), timeout=10.0)
    finally:
        await feed.disconnect()

    if tick is None:
        print("FAIL: no live tick received")
        return 1
    print(f"OK: live tick {tick.symbol} bid={tick.bid} ask={tick.ask}")
    print("Binance + SybaKiller are wired together.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
