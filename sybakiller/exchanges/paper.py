"""Paper adapter for automated tests only."""

from sybakiller.adapters.base import ExchangeAdapter
from sybakiller.types import Order, OrderId
from sybakiller.venues.types import BINANCE_CEX, VenueProfile


class PaperExchangeAdapter(ExchangeAdapter):
    submitted: list[Order]
    cancelled: list[tuple[OrderId, str | None]]

    def __init__(self, venue: VenueProfile = BINANCE_CEX) -> None:
        self._venue = venue
        self.submitted = []
        self.cancelled = []

    @property
    def venue(self) -> VenueProfile:
        return self._venue

    async def submit_order(self, order: Order) -> OrderId:
        self.submitted.append(order)
        return OrderId(f"ex-{order.client_order_id}")

    async def cancel_order(
        self,
        exchange_order_id: OrderId,
        *,
        symbol: str | None = None,
    ) -> bool:
        self.cancelled.append((exchange_order_id, symbol))
        return True
