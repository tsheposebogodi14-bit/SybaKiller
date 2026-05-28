# SybaKiller — full workstation setup

## Installed automatically (no sudo)

| Tool | Purpose |
|------|---------|
| **uv** | Fast Python package manager |
| **Python 3.14 venv** | All runtime + dev + backtest + data deps |
| **Rust stable** | Future hot-path modules (`rustfmt`, `clippy`) |
| **pre-commit** | Ruff hooks on commit |
| **`.env`** | Copied from `.env.example` |

Run again anytime: `bash scripts/install-dev.sh` or `make upgrade`

## Requires sudo (run once)

```bash
sudo bash scripts/install-system.sh
```

Installs: `ripgrep`, `python3-venv`, `redis-tools`, `postgresql-client`, **Docker** + compose plugin.

After Docker install, log out and back in (docker group), then:

```bash
docker compose up -d
```

## Optional infrastructure

| Service | Port | Profile |
|---------|------|---------|
| Redis | 6379 | default |
| TimescaleDB | 5432 | default |
| Prometheus | 9090 | `observability` |
| Grafana | 3000 | `observability` |

```bash
make docker-obs
```

Grafana login: `admin` / `syba` (change in production).

## Verify

```bash
make verify
```

## What we added beyond the minimal bot

- **Networking:** `aiohttp`, `websockets`, `httpx`
- **Serialization:** `orjson`
- **Observability:** `structlog`, `prometheus-client`
- **Bus / cache:** `redis[hiredis]`
- **Analytics:** `numpy`, `pandas`
- **Backtest:** `jax`, `matplotlib`, `pyarrow`
- **Persistence:** `sqlalchemy`, `asyncpg`, `alembic`
- **Quality:** `ruff`, `mypy`, `pytest-cov`, `pytest-xdist`, `pre-commit`
- **Config:** `pydantic-settings` + `.env`
- **Docker stack** for local Redis/DB/metrics

## Cursor / IDE

1. Open `/home/syba/Ghost` as workspace root.
2. Select interpreter: `.venv/bin/python`
3. Enable **Privacy Mode** for strategy code.
4. Add exchange API docs under **Features → Docs** for `@Docs` in chat.

## Binance API keys (testnet first)

```bash
# Browser: https://testnet.binance.vision/ → Log in with GitHub → API key
make binance-setup
make verify-binance
```

## Still manual (venue-specific)

- Mainnet keys only when you intentionally set `BINANCE_TESTNET=false`
- MT5 / MQL5 bridge (Windows terminal)
- Production TLS and secrets manager
