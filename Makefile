.PHONY: install install-system sync upgrade test lint typecheck api docker-up docker-down verify pre-commit

install:
	bash scripts/install-dev.sh

install-system:
	sudo bash scripts/install-system.sh

sync:
	uv sync --all-extras --dev

upgrade:
	uv lock --upgrade
	uv sync --all-extras --dev
	uv pip install --upgrade -e ".[all]"

test:
	uv run pytest

test-cov:
	uv run pytest --cov=sybakiller --cov=api --cov-report=term-missing

lint:
	uv run ruff check sybakiller api tests
	uv run ruff format --check sybakiller api tests

format:
	uv run ruff check --fix sybakiller api tests
	uv run ruff format sybakiller api tests

typecheck:
	uv run mypy sybakiller api

api:
	uv run uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

docker-up:
	docker compose up -d redis postgres

docker-down:
	docker compose down

docker-obs:
	docker compose --profile observability up -d

verify:
	bash scripts/verify-setup.sh

smoke:
	bash scripts/smoke-live.sh

pre-commit:
	uv run pre-commit run --all-files
