"""Binance Spot REST — CEX execution adapter."""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any
from urllib.parse import urlencode

import aiohttp

from sybakiller.adapters.base import ExchangeAdapter
from sybakiller.exchanges.constants import BINANCE_API, BINANCE_TESTNET_API
from sybakiller.exchanges.filters import ExchangeFilterCache
from sybakiller.types import Order, OrderId
from sybakiller.venues.types import BINANCE_CEX, VenueProfile

logger = logging.getLogger(__name__)


class BinanceExchangeAdapter(ExchangeAdapter):
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        *,
        testnet: bool = False,
        venue: VenueProfile = BINANCE_CEX,
    ) -> None:
        self._venue = venue
        self._api_key = api_key
        self._api_secret = api_secret
        self._base = BINANCE_TESTNET_API if testnet else BINANCE_API
        self._session: aiohttp.ClientSession | None = None
        self._limiter = self.rate_limiter
        self._filters = ExchangeFilterCache(testnet=testnet)
        self._quotes: dict[str, tuple[float, float]] = {}

    @property
    def venue(self) -> VenueProfile:
        return self._venue

    async def _session_get(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"X-MBX-APIKEY": self._api_key},
                timeout=aiohttp.ClientTimeout(total=10),
                trust_env=False,
            )
        return self._session

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()

    def _sign(self, params: dict[str, Any]) -> str:
        query = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode(),
            query.encode(),
            hashlib.sha256,
        ).hexdigest()
        return f"{query}&signature={signature}"

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any],
        *,
        signed: bool = False,
    ) -> dict[str, Any]:
        await self._limiter.acquire("rest")
        session = await self._session_get()
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            query = self._sign(params)
            url = f"{self._base}{path}?{query}"
        else:
            url = f"{self._base}{path}?{urlencode(params)}"

        async with session.request(method, url) as resp:
            body = await resp.json()
            if resp.status >= 400:
                raise RuntimeError(f"binance {resp.status}: {body}")
            if not isinstance(body, dict):
                raise RuntimeError(f"unexpected binance response: {body}")
            return body

    def note_quote(self, symbol: str, bid: float, ask: float) -> None:
        self._quotes[symbol.upper()] = (bid, ask)

    async def submit_order(self, order: Order) -> OrderId:
        sym = str(order.symbol).upper()
        rules = await self._filters.get(sym)
        bid, ask = self._quotes.get(sym, (order.price, order.price))
        filter_err = rules.validate_limit_order(
            side=order.side.value,
            quantity=order.quantity,
            price=order.price,
            ref_bid=bid,
            ref_ask=ask,
        )
        if filter_err is not None:
            raise RuntimeError(f"binance filter: {filter_err}")

        params: dict[str, Any] = {
            "symbol": str(order.symbol).upper(),
            "side": order.side.value.upper(),
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": f"{order.quantity:.8f}".rstrip("0").rstrip("."),
            "price": f"{order.price:.8f}".rstrip("0").rstrip("."),
            "newClientOrderId": str(order.client_order_id)[:36],
        }
        result = await self._request("POST", "/api/v3/order", params, signed=True)
        exchange_id = str(result.get("orderId", order.client_order_id))
        logger.info("binance order placed %s -> %s", order.client_order_id, exchange_id)
        return OrderId(exchange_id)

    async def cancel_order(
        self,
        exchange_order_id: OrderId,
        *,
        symbol: str | None = None,
    ) -> bool:
        if symbol is None:
            return False
        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "orderId": str(exchange_order_id),
        }
        try:
            await self._request("DELETE", "/api/v3/order", params, signed=True)
            return True
        except RuntimeError:
            return False

    async def reconcile_open_orders(self) -> list[dict[str, Any]]:
        """Fetch open orders from Binance after restart (optional full reconcile)."""
        try:
            result = await self._request("GET", "/api/v3/openOrders", {}, signed=True)
            if isinstance(result, list):
                return result
        except RuntimeError as exc:
            logger.warning("open order reconcile failed: %s", exc)
        return []
