# tessera

A living-docs platform that keeps technical documentation in sync with your codebase. Tessera ingests docs from Git repositories, generates embeddings via Ollama, and exposes search, proposals, and admin APIs — with a Next.js web UI and an MCP server for AI agent access.

## Architecture

| Component | Technology | Port |
|-----------|-----------|------|
| `apps/api` | FastAPI (Python 3.12) | 8000 |
| `apps/workers` | Celery + Redis (Python) | — |
| `apps/mcp-server` | MCP server (Python) | 8001 |
| `apps/web` | Next.js 15 | 3000 |
| `packages/core` | Shared Python library | — |

Infrastructure: PostgreSQL 16 + pgvector, Redis 7, Ollama (nomic-embed-text).

## Running the dev environment

### Prerequisites

- Docker + Docker Compose
- Node.js 20+ and npm (for running the web UI locally)
- Python 3.12+ and [uv](https://docs.astral.sh/uv/) (for running Python services locally)

### Option A — everything in Docker (simplest)

```bash
# Edit deploy/.env with your values, then:
cd deploy
docker compose up
```

Services come up at:
- API: http://localhost:8000
- Web: http://localhost:3000
- MCP: http://localhost:8001

> Ollama pulls the `nomic-embed-text` model on first boot — this may take a few minutes.

### Option B — infra in Docker, services locally (recommended for development)

Start only the infrastructure services:

```bash
cd deploy
docker compose up postgres redis ollama
```

In separate terminals, start each service:

**API** (hot-reloads on file changes):
```bash
cd apps/api
uv sync
DATABASE_URL=postgresql+psycopg://tessera:tessera@localhost:5432/tessera \
REDIS_URL=redis://localhost:6379/0 \
SECRET_KEY=dev-secret-key \
uv run uvicorn tessera_api.main:app --reload --port 8000
```

**Workers**:
```bash
cd apps/workers
uv sync
DATABASE_URL=postgresql+psycopg://tessera:tessera@localhost:5432/tessera \
REDIS_URL=redis://localhost:6379/0 \
uv run celery -A tessera_workers.celery_app worker --loglevel=info
```

**MCP server**:
```bash
cd apps/mcp-server
uv sync
DATABASE_URL=postgresql+psycopg://tessera:tessera@localhost:5432/tessera \
API_URL=http://localhost:8000 \
uv run uvicorn tessera_mcp.main:app --port 8001
```

**Web UI**:
```bash
cd apps/web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Open http://localhost:3000.

### Database migrations

```bash
cd apps/api
uv run alembic upgrade head
```

## Environment variables

Copy `deploy/.env` and fill in the required values:

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Session signing key — any random string for local dev |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for AI features |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `OIDC_ISSUER` | No | OIDC provider URL (auth is disabled if unset) |
| `OIDC_CLIENT_ID` | No | OIDC client ID |
| `OIDC_CLIENT_SECRET` | No | OIDC client secret |

## Running tests

**Python (API, workers, core)**:
```bash
cd apps/api   # or apps/workers, packages/core
uv run pytest
```

**Web UI**:
```bash
cd apps/web
npm test
```

**End-to-end validation** (requires a running stack):
```bash
export API_URL=http://localhost:8000
export ADMIN_TOKEN=<session-token>
python scripts/validate_e2e.py
```
