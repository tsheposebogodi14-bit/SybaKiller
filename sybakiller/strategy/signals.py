"""Trade signals — independent of execution engine internals."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from uuid import uuid4

from sybakiller.types import OrderId, Side, Symbol


@dataclass(slots=True)
class TradeSignal:
    """Intent from a tenant strategy or external Oodi-style source."""

    tenant_id: str
    source_id: str
    symbol: Symbol
    side: Side
    quantity: float
    price: float
    signal_id: str = field(default_factory=lambda: str(uuid4()))
    priority: int = 0
    created_at: float = field(default_factory=time)
    metadata: dict[str, str] = field(default_factory=dict)

    def to_order_client_id(self) -> OrderId:
        return OrderId(f"{self.tenant_id}-{self.source_id}-{self.signal_id}"[:36])
