#!/usr/bin/env bash
# Interactive Binance key setup — writes to .env (never commit .env).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"

echo "SybaKiller — Binance API setup (testnet recommended first)"
echo "Get keys: https://testnet.binance.vision/ → Log in with GitHub → API Management"
echo ""

read -r -p "Use Binance TESTNET? [Y/n]: " use_testnet
use_testnet="${use_testnet:-Y}"
if [[ "$use_testnet" =~ ^[Nn] ]]; then
  testnet="false"
else
  testnet="true"
fi

read -r -p "BINANCE_API_KEY: " api_key
read -r -s -p "BINANCE_API_SECRET (hidden): " api_secret
echo ""

if [[ -z "$api_key" || -z "$api_secret" ]]; then
  echo "Error: key and secret are required."
  exit 1
fi

# Update or create .env keys
touch "$ENV_FILE"
for var in BINANCE_TESTNET BINANCE_API_KEY BINANCE_API_SECRET MARKET_DATA_PROVIDER; do
  sed -i "/^${var}=/d" "$ENV_FILE" 2>/dev/null || true
done

{
  echo "BINANCE_TESTNET=$testnet"
  echo "BINANCE_API_KEY=$api_key"
  echo "BINANCE_API_SECRET=$api_secret"
  echo "MARKET_DATA_PROVIDER=binance"
} >> "$ENV_FILE"

echo ""
echo "Saved to .env"
echo "Verifying connection..."
export PATH="${HOME}/.local/bin:${PATH}"
cd "$ROOT"
uv run python scripts/verify_binance.py
