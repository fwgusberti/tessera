.PHONY: dev infra migrate api workers mcp web test test-api test-web down

ROOT  := $(shell pwd)
DB    := postgresql+psycopg://tessera:tessera@localhost:5432/tessera
REDIS := redis://localhost:6379/0
HOST  ?= localhost
ANTHROPIC_API_KEY ?= $(shell echo "$ANTHROPIC_API_KEY")

## ── full stack ─────────────────────────────────────────────────────────────

# Start infra + all services (Ctrl-C stops everything)
# Override HOST to expose on your network: make dev HOST=192.168.0.8
dev:
	@HOST=$(HOST) bash scripts/dev.sh

## ── infrastructure ─────────────────────────────────────────────────────────

# Start only postgres, redis, and ollama via Docker
infra:
	cd deploy && docker compose up -d postgres redis ollama

# Stop all infra containers
down:
	cd deploy && docker compose stop postgres redis ollama

## ── database ────────────────────────────────────────────────────────────────

# Apply pending Alembic migrations (must run from root; uses apps/api venv)
migrate:
	cd apps/api && uv sync -q
	DATABASE_URL=$(DB) apps/api/.venv/bin/alembic -c db/migrations/alembic.ini upgrade head

## ── services (run each in its own terminal) ─────────────────────────────────

api:
	cd apps/api && \
		DATABASE_URL=$(DB) REDIS_URL=$(REDIS) SECRET_KEY=dev-secret-key \
		OLLAMA_BASE_URL=http://localhost:11434 \
		ANTHROPIC_API_KEY=$(ANTHROPIC_API_KEY) \
		uv run uvicorn tessera_api.main:app --reload --host 0.0.0.0 --port 8000

workers:
	cd apps/workers && \
		DATABASE_URL=$(DB) REDIS_URL=$(REDIS) OLLAMA_BASE_URL=http://localhost:11434 \
		ANTHROPIC_API_KEY=$(ANTHROPIC_API_KEY) \
		uv run celery -A tessera_workers.celery_app worker --loglevel=info

mcp:
	cd apps/mcp-server && \
		DATABASE_URL=$(DB) API_URL=http://$(HOST):8000 \
		uv run uvicorn tessera_mcp.main:app --host 0.0.0.0 --port 8001

web:
	cd apps/web && NEXT_PUBLIC_API_URL=http://$(HOST):8000 npm run dev -- -H 0.0.0.0

## ── tests ───────────────────────────────────────────────────────────────────

test: test-api test-web

test-api:
	cd apps/api && uv run pytest

test-web:
	cd apps/web && npm test
