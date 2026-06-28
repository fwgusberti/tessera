#!/usr/bin/env bash
# Start the full Tessera dev stack: infra (Docker) + API + workers + MCP + web
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="postgresql+psycopg://tessera:tessera@localhost:5432/tessera"
REDIS="redis://localhost:6379/0"
HOST="${HOST:-localhost}"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"

# ── colors ────────────────────────────────────────────────────────────────────
CY='\033[0;36m'   # api
MG='\033[0;35m'   # workers
BL='\033[0;34m'   # mcp
GR='\033[0;32m'   # web
YL='\033[1;33m'   # infra
NC='\033[0m'

prefix() { local color="$1" tag="$2"; while IFS= read -r line; do printf "${color}[%-7s]${NC} %s\n" "$tag" "$line"; done; }

# ── cleanup ───────────────────────────────────────────────────────────────────
PIDS=()
cleanup() {
  echo ""
  echo "Shutting down..."
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  # give processes a moment to exit cleanly
  sleep 1
  for pid in "${PIDS[@]:-}"; do
    kill -9 "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

# ── infra ─────────────────────────────────────────────────────────────────────
echo -e "${YL}[infra  ]${NC} Starting postgres, redis, ollama..."
cd "$ROOT/deploy"
docker compose up -d postgres redis ollama 2>&1 | prefix "$YL" "infra"

echo -e "${YL}[infra  ]${NC} Waiting for postgres..."
until docker compose exec -T postgres pg_isready -U tessera &>/dev/null; do
  sleep 1
done
echo -e "${YL}[infra  ]${NC} Postgres ready."

# ── migrations ────────────────────────────────────────────────────────────────
echo -e "${CY}[api    ]${NC} Syncing API venv..."
(cd "$ROOT/apps/api" && uv sync -q)

echo -e "${CY}[api    ]${NC} Running migrations..."
# Must run from project root so script_location=db/migrations resolves correctly
(cd "$ROOT" && DATABASE_URL="$DB" "$ROOT/apps/api/.venv/bin/alembic" -c db/migrations/alembic.ini upgrade head 2>&1 | prefix "$CY" "api")

# ── services ──────────────────────────────────────────────────────────────────
(cd "$ROOT/apps/api" && \
  DATABASE_URL="$DB" \
  REDIS_URL="$REDIS" \
  SECRET_KEY=dev-secret-key \
  FRONTEND_URL="http://$HOST:3000" \
  OLLAMA_BASE_URL=http://localhost:11434 \
  ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  uv run uvicorn tessera_api.main:app --reload --host 0.0.0.0 --port 8000 2>&1 | prefix "$CY" "api") &
PIDS+=($!)

(cd "$ROOT/apps/workers" && \
  DATABASE_URL="$DB" REDIS_URL="$REDIS" OLLAMA_BASE_URL=http://localhost:11434 \
  uv run celery -A tessera_workers.celery_app worker --loglevel=info 2>&1 | prefix "$MG" "workers") &
PIDS+=($!)

(cd "$ROOT/apps/mcp-server" && \
  DATABASE_URL="$DB" API_URL=http://"$HOST":8000 \
  uv run uvicorn tessera_mcp.main:app --host 0.0.0.0 --port 8001 2>&1 | prefix "$BL" "mcp") &
PIDS+=($!)

(cd "$ROOT/apps/web" && \
  npm install --silent 2>&1 | prefix "$GR" "web" && \
  NEXT_PUBLIC_API_URL=http://"$HOST":8000 npm run dev -- -H 0.0.0.0 2>&1 | prefix "$GR" "web") &
PIDS+=($!)

# ── ready ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GR}All services started.${NC}"
echo -e "  API  →  http://$HOST:8000      (docs: http://$HOST:8000/docs)"
echo -e "  Web  →  http://$HOST:3000"
echo -e "  MCP  →  http://$HOST:8001"
echo ""
echo "Press Ctrl-C to stop all services."
echo ""

wait
