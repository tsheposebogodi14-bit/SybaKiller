#!/usr/bin/env bash
# Start full SybaKiller stack: verify keys, optional Redis, API server.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.local/bin:${PATH}"

echo "==> GitHub"
gh auth status -h github.com

echo "==> Binance"
if grep -q '^BINANCE_API_KEY=$' .env 2>/dev/null || ! grep -q '^BINANCE_API_KEY=' .env 2>/dev/null; then
  echo "Binance keys missing — run: bash scripts/setup-binance-env.sh"
  echo "Starting API anyway (live data only, no orders)."
else
  uv run python scripts/verify_binance.py
fi

if command -v docker >/dev/null 2>&1; then
  if docker compose ps redis 2>/dev/null | grep -q running; then
    echo "==> Redis already running"
  else
    echo "==> Starting Redis (optional)"
    docker compose up -d redis 2>/dev/null || true
  fi
fi

echo "==> Starting API on http://127.0.0.1:8000"
echo "    WebSocket ticks: ws://127.0.0.1:8000/ws/market"
exec env -u ALL_PROXY -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u all_proxy \
  uv run uvicorn api.main:app --host 127.0.0.1 --port 8000
