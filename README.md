# SybaKiller

Low-latency trading bot foundation: order book, risk, execution gateway, and FastAPI control plane.

## One-shot setup

```bash
cd /home/syba/Ghost

# User-space (Python, Rust, hooks) — no sudo
bash scripts/install-dev.sh

# System packages + Docker (once, needs sudo)
sudo bash scripts/install-system.sh

# Optional local infra
docker compose up -d          # Redis + TimescaleDB
make verify                   # health check + tests
```

## Daily commands

| Command | Purpose |
|---------|---------|
| `make api` | Start FastAPI control plane |
| `make test` | Run unit tests |
| `make test-cov` | Tests with coverage |
| `make lint` / `make format` | Ruff check / fix |
| `make typecheck` | Mypy strict |
| `make upgrade` | Upgrade all locked deps |
| `make docker-up` | Redis + Postgres |
| `make docker-obs` | + Prometheus + Grafana |

## Dependency groups

| Extra | Packages | Use |
|-------|----------|-----|
| (core) | FastAPI, aiohttp, websockets, redis, numpy, pandas, structlog, prometheus | Runtime |
| `dev` | pytest, ruff, mypy, pre-commit, ipython | Quality + DX |
| `backtest` | JAX, matplotlib, pyarrow | Offline sim / research |
| `data` | SQLAlchemy, asyncpg, alembic | Persistence |
| `all` | Everything above | Full workstation |

Install subset: `uv sync --extra dev --extra data`

## Layout

```
sybakiller/       Core library
api/              FastAPI control plane
tests/            Unit tests
scripts/          install-dev.sh, install-system.sh, verify-setup.sh
infra/            Prometheus config
docker-compose.yml
```

## Live market data

Default: **Binance public WebSocket** (`bookTicker`) — real bid/ask, no API key.

```bash
# Watch live ticks in terminal
websocat ws://127.0.0.1:8000/ws/market

# Or check status
curl http://127.0.0.1:8000/status
```

Configure symbols in `.env`: `MARKET_DATA_SYMBOLS=BTCUSDT,ETHUSDT`

## Wire GitHub + Binance + SybaKiller

1. **GitHub** (already done if `gh auth status` is green): `gh auth setup-git`
2. **Binance testnet keys**: open [testnet.binance.vision](https://testnet.binance.vision/) → **Log in with GitHub** → create HMAC API key
3. **Save keys into `.env`** (never commit):

```bash
make binance-setup    # interactive — sets BINANCE_TESTNET, key, secret
make verify-binance # signed account check + live testnet tick
make run            # gh + binance verify + API on :8000
```

`.env` defaults to `BINANCE_TESTNET=true` so market data and orders use testnet endpoints.

Without keys, testnet **market data still works**; `/orders` returns 503 until keys are set.

## Control plane

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness + feed stats |
| `/status` | GET | Last live tick, feed, positions |
| `/ws/market` | WebSocket | Push live ticks (JSON) |
| `/kill` | POST | Engage kill switch |
| `/kill/release` | POST | Release kill switch |
| `/orders` | POST | Place live order (keys required) |
| `/orders/{id}` | DELETE | Cancel order |

## Environment

Copy `.env.example` → `.env`. Keys: `REDIS_URL`, `DATABASE_URL`, risk limits, exchange credentials (when live).

## Privacy

Enable **Cursor Privacy Mode** for proprietary strategy code.

## Upgrading

```bash
make upgrade   # bump locked dependencies
make test && make smoke
```

Roadmap: [docs/UPGRADE.md](docs/UPGRADE.md)

## Next build targets

- User Data Stream (live fill/order updates)
- Exchange filter cache (`exchangeInfo`)
- Prometheus `/metrics` + Timescale tick history
