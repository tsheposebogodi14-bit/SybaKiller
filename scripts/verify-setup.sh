#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"

ok=0
fail=0

check() {
  if eval "$2" >/dev/null 2>&1; then
    printf "  OK  %s\n" "$1"
    ok=$((ok + 1))
  else
    printf "  --  %s (missing)\n" "$1"
    fail=$((fail + 1))
  fi
}

echo "SybaKiller environment check"
echo "----------------------------"
check "uv" "command -v uv"
check "python venv" "test -x .venv/bin/python"
check "pytest" "uv run pytest --version"
check "ruff" "uv run ruff --version"
check "rustc" "command -v rustc"
check "cargo" "command -v cargo"
check "git" "command -v git"
check "curl" "command -v curl"
check "docker" "command -v docker"
check "redis-cli" "command -v redis-cli"
check ".env" "test -f .env"

if [[ -x .venv/bin/python ]]; then
  uv run pytest -q
  echo "Tests passed."
else
  echo "Run: bash scripts/install-dev.sh"
  exit 1
fi

echo "----------------------------"
echo "Ready: $ok | Missing (optional): $fail"
