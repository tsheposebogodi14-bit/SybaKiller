# SybaKiller architecture

## Layers

```
MarketDataAdapter (per-venue WS protocol)
        ↓ ticks
   Strategy.on_tick → TradeSignal
        ↓
 MultiTenantSignalBus (Oodi / multi-source fan-in)
        ↓
 SignalExecutionRouter (decoupled from strategies)
        ↓
 RiskManager → ExecutionGateway → ExchangeAdapter
        ↓
 OrderBook + Redis snapshot (crash recovery)
```

## Adapter extensibility

| Component | Contract | Venue-specific |
|-----------|----------|----------------|
| `MarketDataAdapter` | `connect`, `next_tick`, `venue` | WS URL, parser (Binance combined vs ECN FIX-json) |
| `ExchangeAdapter` | `submit_order`, `cancel_order`, `venue` | REST/FIX, cancel needs symbol?, replace support |
| `VenueProfile` | rate limits, `WsProtocol`, `VenueKind` | `BINANCE_CEX`, `GENERIC_ECN` |

Rate limits use `VenueRateLimiter` token buckets (`order`, `cancel`, `rest`).

## Strategy decoupling

- Strategies **never** import `ExecutionGateway`.
- They publish `TradeSignal` to `MultiTenantSignalBus`.
- `SignalExecutionRouter` is the only path from bus → gateway.
- External systems POST `/signals` (same bus as internal strategies).

## State recovery

On `engine.start()`:

1. Load `syba:snapshot:{tenant_id}` from Redis.
2. Restore open orders + `exchange_id_map` + positions + kill switch.
3. Resume monitoring without replaying historical fills.

Snapshots are written:

- Every `STATE_SNAPSHOT_INTERVAL_SEC` (default 30s)
- After gateway order changes
- On shutdown

Optional full reconcile: `ExchangeAdapter.reconcile_open_orders()` (Binance implements).

## Adding a new venue

1. Add `VenueProfile` in `sybakiller/venues/types.py`.
2. Implement `MarketDataAdapter` + `ExchangeAdapter` subclasses.
3. Register in `feeds/factory.py` and `exchanges/factory.py`.
