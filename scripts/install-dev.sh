#!/usr/bin/env bash
# User-space dev stack: uv venv, all Python extras, Rust, pre-commit, upgrades.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"

echo "==> Ensuring uv"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${PATH}"
fi

echo "==> Python venv + all dependency groups (latest)"
rm -rf .venv
uv venv
uv lock --upgrade
uv sync --all-extras --dev

echo "==> pre-commit hooks"
uv run pre-commit install || true

echo "==> Rust toolchain (for future hot-path modules)"
if ! command -v rustc >/dev/null 2>&1; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
  export PATH="${HOME}/.cargo/bin:${PATH}"
fi
# Useful Rust components for trading infra
rustup component add rustfmt clippy 2>/dev/null || true
rustup update stable 2>/dev/null || true

echo "==> Copy .env if missing"
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "==> Lint (auto-fix)"
uv run ruff check --fix sybakiller api tests
uv run ruff format sybakiller api tests

echo "==> Verify"
uv run pytest -q
uv run ruff check sybakiller api tests
echo ""
echo "Done. Optional next steps:"
echo "  sudo bash scripts/install-system.sh   # apt packages + Docker"
echo "  docker compose up -d                  # Redis + TimescaleDB"
echo "  make api                              # start control plane"
