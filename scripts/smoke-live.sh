#!/usr/bin/env bash
# End-to-end smoke: live Binance tick + API health (no API keys required for data).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.local/bin:${PATH}"

echo "==> Unit tests"
uv run pytest -q

echo "==> Live Binance tick (10s timeout)"
uv run python - <<'PY'
import asyncio
from sybakiller.feeds.binance import BinanceLiveFeed

async def main() -> None:
    feed = BinanceLiveFeed(["BTCUSDT"])
    await feed.connect()
    tick = await asyncio.wait_for(feed.next_tick(), timeout=10.0)
    print(f"OK live tick: {tick.symbol} bid={tick.bid} ask={tick.ask}")
    await feed.disconnect()

asyncio.run(main())
PY

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
echo "==> Smoke passed"
