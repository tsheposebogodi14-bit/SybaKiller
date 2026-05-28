# SybaKiller upgrade path

## v0.1 → v0.2 (in progress)

### Done in this cycle

- Testnet-first `.env` defaults and `make binance-setup` / `verify-binance` / `run`
- Live smoke in CI (public testnet WebSocket, no API keys)
- Proxy-safe Binance WS (`proxy=None`) and REST (`trust_env=False`)
- Gateway maps exchange `RuntimeError` to rejected orders (no HTTP 500)

### Dependency upgrades

```bash
make upgrade    # refresh uv.lock + sync all extras
make test
make smoke
```

Pin breaking majors in `pyproject.toml` if needed after `make upgrade`.

### Next features (v0.2)

| Priority | Item | Why |
|----------|------|-----|
| P0 | User Data Stream (order/fill WS) | Live order state without polling |
| P0 | Exchange filter cache (`exchangeInfo`) | Avoid NOTIONAL / PRICE_FILTER 400s |
| P1 | Redis + snapshot on by default in `docker compose` | Recovery across API restarts |
| P1 | Prometheus metrics on `/metrics` | Latency, reject rate, feed lag |
| P2 | TimescaleDB tick + order history | Research and audit |
| P2 | `rust/` module for book hot path | Sub-µs local book updates |

### Mainnet checklist (later)

- `BINANCE_TESTNET=false` only after testnet soak
- IP whitelist on Binance key
- Secrets via env manager (not `.env` in prod)
- Kill switch runbook + max notional review
