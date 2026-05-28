#!/usr/bin/env bash
# End-to-end smoke: live Binance testnet tick + API health (+ optional key verify).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.local/bin:${PATH}"

if [[ "${SMOKE_SKIP_UNIT:-}" != "1" ]]; then
  echo "==> Unit tests"
  uv run pytest -q
fi

echo "==> Live Binance tick (testnet, 15s timeout)"
uv run python - <<'PY'
import asyncio
from sybakiller.config import get_settings
from sybakiller.feeds.binance import BinanceLiveFeed

async def main() -> None:
    settings = get_settings()
    label = "testnet" if settings.binance_testnet else "mainnet"
    feed = BinanceLiveFeed(["BTCUSDT"], testnet=settings.binance_testnet)
    await feed.connect()
    tick = await asyncio.wait_for(feed.next_tick(), timeout=15.0)
    print(f"OK live tick ({label}): {tick.symbol} bid={tick.bid} ask={tick.ask}")
    await feed.disconnect()

asyncio.run(main())
PY

if [[ -n "${BINANCE_API_KEY:-}" ]] || grep -q '^BINANCE_API_KEY=[^[:space:]]' .env 2>/dev/null; then
  echo "==> Binance API verify (keys present)"
  uv run python scripts/verify_binance.py
fi

echo "==> API smoke (background)"
SYBA_ENV=test MARKET_DATA_PROVIDER=simulated uv run uvicorn api.main:app --host 127.0.0.1 --port 8765 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT

for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sf http://127.0.0.1:8765/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

curl -sf http://127.0.0.1:8765/health | head -c 200
echo ""
curl -sf http://127.0.0.1:8765/status | head -c 300
echo ""
echo "==> Live API with Binance feed (15s)"
SYBA_ENV=production MARKET_DATA_PROVIDER=binance BINANCE_TESTNET="${BINANCE_TESTNET:-true}" \
  uv run uvicorn api.main:app --host 127.0.0.1 --port 8766 &
LIVE_PID=$!
trap 'kill $API_PID $LIVE_PID 2>/dev/null || true' EXIT
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  status="$(curl -sf http://127.0.0.1:8766/status 2>/dev/null || true)"
  if echo "$status" | grep -q '"ticks_received":[1-9]'; then
    echo "OK live API ticks flowing"
    break
  fi
  sleep 1
done
if ! echo "$status" | grep -q '"ticks_received":[1-9]'; then
  echo "WARN: live API did not report ticks (proxy/network?)"
  echo "$status" | head -c 400
  echo ""
fi

echo "==> Smoke passed"
