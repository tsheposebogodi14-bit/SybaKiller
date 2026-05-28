"""Binance exchangeInfo symbol filters — cached for order validation."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

import aiohttp

from sybakiller.exchanges.constants import BINANCE_API, BINANCE_TESTNET_API

logger = logging.getLogger(__name__)

_CACHE_TTL_SEC = 300.0


@dataclass(frozen=True, slots=True)
class SymbolFilters:
    symbol: str
    min_qty: float
    max_qty: float
    step_size: float
    min_notional: float
    min_price: float
    max_price: float
    tick_size: float
    bid_multiplier_down: float
    ask_multiplier_up: float

    def validate_limit_order(
        self, *, side: str, quantity: float, price: float, ref_bid: float, ref_ask: float
    ) -> str | None:
        if quantity < self.min_qty or quantity > self.max_qty:
            return f"quantity {quantity} outside [{self.min_qty}, {self.max_qty}]"
        if not _step_ok(quantity, self.step_size):
            return f"quantity step must be multiple of {self.step_size}"
        if price < self.min_price or price > self.max_price:
            return f"price {price} outside [{self.min_price}, {self.max_price}]"
        if not _step_ok(price, self.tick_size):
            return f"price tick must be multiple of {self.tick_size}"
        notional = quantity * price
        if notional < self.min_notional:
            return f"notional {notional:.4f} below min {self.min_notional}"
        if ref_bid > 0 and ref_ask > 0:
            mid = (ref_bid + ref_ask) / 2.0
            if side.upper() == "BUY":
                floor = mid * self.bid_multiplier_down
                if price < floor:
                    return f"buy price below PERCENT_PRICE_BY_SIDE floor {floor:.4f}"
            else:
                cap = mid * self.ask_multiplier_up
                if price > cap:
                    return f"sell price above PERCENT_PRICE_BY_SIDE cap {cap:.4f}"
        return None


def _step_ok(value: float, step: float) -> bool:
    if step <= 0:
        return True
    ratio = value / step
    return abs(ratio - round(ratio)) < 1e-9


def _filter_value(
    filters: list[dict[str, Any]], name: str, key: str, default: float = 0.0
) -> float:
    for f in filters:
        if f.get("filterType") == name:
            return float(f.get(key, default))
    return default


def parse_symbol_filters(symbol: str, payload: dict[str, Any]) -> SymbolFilters:
    filters = payload.get("filters", [])
    return SymbolFilters(
        symbol=symbol.upper(),
        min_qty=_filter_value(filters, "LOT_SIZE", "minQty"),
        max_qty=_filter_value(filters, "LOT_SIZE", "maxQty", 1e12),
        step_size=_filter_value(filters, "LOT_SIZE", "stepSize", 1e-8),
        min_notional=_filter_value(filters, "NOTIONAL", "minNotional")
        or _filter_value(filters, "MIN_NOTIONAL", "minNotional"),
        min_price=_filter_value(filters, "PRICE_FILTER", "minPrice"),
        max_price=_filter_value(filters, "PRICE_FILTER", "maxPrice", 1e12),
        tick_size=_filter_value(filters, "PRICE_FILTER", "tickSize", 1e-8),
        bid_multiplier_down=_filter_value(
            filters, "PERCENT_PRICE_BY_SIDE", "bidMultiplierDown", 0.0
        ),
        ask_multiplier_up=_filter_value(filters, "PERCENT_PRICE_BY_SIDE", "askMultiplierUp", 1e12),
    )


class ExchangeFilterCache:
    def __init__(self, *, testnet: bool = False, ttl_sec: float = _CACHE_TTL_SEC) -> None:
        self._base = BINANCE_TESTNET_API if testnet else BINANCE_API
        self._ttl = ttl_sec
        self._symbols: dict[str, SymbolFilters] = {}
        self._fetched_at = 0.0
        self._lock = asyncio.Lock()

    async def get(self, symbol: str) -> SymbolFilters:
        sym = symbol.upper()
        async with self._lock:
            if time.time() - self._fetched_at > self._ttl or sym not in self._symbols:
                await self._refresh()
        filters = self._symbols.get(sym)
        if filters is None:
            raise KeyError(f"unknown symbol on exchange: {sym}")
        return filters

    async def _refresh(self) -> None:
        url = f"{self._base}/api/v3/exchangeInfo"
        async with aiohttp.ClientSession(trust_env=False) as session, session.get(url) as resp:
            body = await resp.json()
            if resp.status >= 400:
                raise RuntimeError(f"exchangeInfo {resp.status}: {body}")
        symbols: dict[str, SymbolFilters] = {}
        for entry in body.get("symbols", []):
            if entry.get("status") != "TRADING":
                continue
            sym = str(entry.get("symbol", ""))
            if sym:
                symbols[sym] = parse_symbol_filters(sym, entry)
        self._symbols = symbols
        self._fetched_at = time.time()
        logger.info("exchange filter cache refreshed (%d symbols)", len(symbols))
