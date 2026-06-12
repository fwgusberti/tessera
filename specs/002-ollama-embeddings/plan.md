# Implementation Plan: Local Ollama Embedding Provider

**Branch**: `002-ollama-embeddings` | **Date**: 2026-06-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-ollama-embeddings/spec.md`

## Summary

Replace the `VoyageEmbeddingProvider` adapter (which calls `api.voyageai.com`) with a new `OllamaEmbeddingProvider` adapter that calls a locally-running Ollama service via its batch embed HTTP API. The `ollama` service is declared in `docker-compose.yml` and pre-loads the `nomic-embed-text` model (768 dimensions). A one-step Alembic migration drops the existing HNSW index, deletes all chunk rows, changes the `chunks.embedding` column from `vector(1024)` to `vector(768)`, and recreates the index. Four import sites in the application code are updated. No changes to the `EmbeddingProvider` ABC or any domain entity.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI 0.111, Celery, httpx >= 0.27 (already declared), SQLAlchemy 2, Alembic, pydantic-settings, pgvector (PostgreSQL extension)

**Storage**: PostgreSQL 16 with `pgvector` extension

**Testing**: pytest with pytest-asyncio; coverage >= 85% enforced

**Target Platform**: Linux containers (Docker Compose); development workstations (Linux/macOS/Windows with Docker Desktop)

**Project Type**: Multi-app monorepo — FastAPI web service (`apps/api`), Celery worker (`apps/workers`), shared domain package (`packages/core`)

**Performance Goals**: Embedding latency ≤ 2 s per batch after warm-up; first-call warm-up ≤ 30 s (model loading)

**Constraints**:
- Fully offline at runtime after the initial model pull
- `EmbeddingProvider` ABC in `packages/core` must not change
- pgvector dimension change requires deleting all chunk rows (re-indexing required)
- No new Python package dependencies (httpx already present)

**Scale/Scope**: Single developer / small team local development; self-hosted deployment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|-----------|-------|--------|
| I — Domain-Driven Architecture | `OllamaEmbeddingProvider` is an infrastructure adapter; domain entities and ports are unchanged. | ✅ PASS |
| II — Separation of Concerns | The `EmbeddingProvider` port stays technology-agnostic. Swapping adapters requires zero changes to domain or application services. | ✅ PASS |
| III — Data Locality & Consent | All embeddings are generated locally inside Docker. No user data leaves the machine. | ✅ PASS |
| IV — TDD | New `OllamaEmbeddingProvider` must have companion unit tests written before or alongside implementation. Migration must be verified with an integration test. Coverage ≥ 85% maintained. | ✅ PASS (required) |
| V — Quality Gates | Ruff and Black must pass on all new/modified files before commit. | ✅ PASS (required) |
| Stack — Persistent storage | `chunks.embedding` remains in PostgreSQL/pgvector. No secondary store introduced. | ✅ PASS |
| Stack — IaC | `ollama` service declared in `docker-compose.yml`. No manual undeclared infrastructure. | ✅ PASS |
| Security — Secrets | `VOYAGE_API_KEY` removed. `ollama_base_url` is not a secret; no new secrets introduced. | ✅ PASS |

**Post-design re-check**: No violations. The migration (delete rows + ALTER COLUMN) is the only irreversible step; it is intentional and documented.

## Project Structure

### Documentation (this feature)

```text
specs/002-ollama-embeddings/
├── plan.md              # This file
├── research.md          # Phase 0 — API, model, migration, Docker decisions
├── data-model.md        # Phase 1 — schema and config changes
├── quickstart.md        # Phase 1 — end-to-end validation guide
├── contracts/
│   └── ollama-embed-api.md   # Ollama /api/embed contract
└── tasks.md             # Phase 2 output (/speckit-tasks — not yet created)
```

### Source Code (repository root)

```text
apps/api/
├── tessera_api/
│   ├── adapters/
│   │   └── embeddings.py          # DELETE VoyageEmbeddingProvider; ADD OllamaEmbeddingProvider
│   ├── config.py                  # Remove voyage_api_key; add ollama_base_url; update defaults
│   └── routers/
│       ├── search.py              # Update import: Voyage → Ollama
│       └── assistant.py           # Update import: Voyage → Ollama
└── tests/
    └── unit/
        └── test_ollama_embedding.py   # NEW — unit tests for OllamaEmbeddingProvider

apps/workers/
└── tessera_workers/
    └── indexing/
        └── _index.py              # Update import: Voyage → Ollama

db/migrations/versions/
└── 0002_ollama_embeddings.py      # NEW — dimension migration (1024 → 768)

deploy/
└── docker-compose.yml             # Add ollama service; remove VOYAGE_API_KEY from api & worker
```

**Structure Decision**: Existing multi-app monorepo structure is preserved. The new adapter replaces the old one in the same file (`adapters/embeddings.py`). No new modules, packages, or directories are added to the application code.

## Implementation Details

### 1. `apps/api/tessera_api/adapters/embeddings.py`

Delete `VoyageEmbeddingProvider` entirely. Replace with:

```python
"""Ollama local EmbeddingProvider adapter."""

from __future__ import annotations

import httpx

from tessera_core.ports.providers import EmbeddingProvider
from tessera_api.config import get_settings


class OllamaEmbeddingProvider(EmbeddingProvider):
    _EMBED_PATH = "/api/embed"

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.ollama_base_url
        self._model = settings.embedding_model
        self._dimensions = settings.embedding_dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=60.0) as client:
            response = await client.post(
                self._EMBED_PATH,
                json={"model": self._model, "input": texts},
            )
            response.raise_for_status()
            return response.json()["embeddings"]
```

### 2. `apps/api/tessera_api/config.py`

```python
# Remove:
voyage_api_key: str = ""
embedding_model: str = "voyage-3"
embedding_dimensions: int = 1024

# Add / update:
ollama_base_url: str = "http://ollama:11434"
embedding_model: str = "nomic-embed-text"
embedding_dimensions: int = 768
```

### 3. `apps/api/tessera_api/routers/search.py` and `assistant.py`

In each file, replace:
```python
from tessera_api.adapters.embeddings import VoyageEmbeddingProvider
embedding_provider = VoyageEmbeddingProvider()
```
with:
```python
from tessera_api.adapters.embeddings import OllamaEmbeddingProvider
embedding_provider = OllamaEmbeddingProvider()
```

### 4. `apps/workers/tessera_workers/indexing/_index.py`

Same import replacement as above.

### 5. `db/migrations/versions/0002_ollama_embeddings.py`

```python
"""Switch embedding provider to Ollama (nomic-embed-text, 768 dims)

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-12
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the HNSW index (required before ALTER COLUMN)
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")
    # Delete all chunks — existing 1024-dim vectors are incompatible; re-index required
    op.execute("DELETE FROM chunks")
    # Change dimension
    op.execute("ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(768)")
    # Recreate HNSW index with same parameters
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")
    op.execute("DELETE FROM chunks")
    op.execute("ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(1024)")
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )
```

### 6. `deploy/docker-compose.yml`

Add `ollama` service:

```yaml
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    entrypoint: >
      /bin/sh -c "ollama serve &
      sleep 5 &&
      ollama pull nomic-embed-text &&
      wait"
    healthcheck:
      test: ["CMD-SHELL", "ollama list | grep nomic-embed-text"]
      interval: 10s
      timeout: 30s
      retries: 30
      start_period: 10s
```

Remove `VOYAGE_API_KEY: ${VOYAGE_API_KEY:-}` from the `api` and `worker` services.

Add to `api` and `worker` `depends_on`:
```yaml
      ollama:
        condition: service_healthy
```

Add to the `volumes` block at the bottom:
```yaml
  ollama_data:
```

### 7. Unit Tests — `apps/api/tests/unit/test_ollama_embedding.py`

Tests to write (TDD — write before implementation):

- `test_embed_returns_correct_dimensions`: mock httpx, assert returned vectors have length 768
- `test_embed_passes_model_and_texts_in_body`: mock httpx, assert request body contains `model` and `input`
- `test_embed_raises_on_http_error`: mock httpx returning 500, assert `HTTPStatusError` propagates
- `test_dimensions_property_returns_768`: assert `OllamaEmbeddingProvider().dimensions == 768`

## Complexity Tracking

> No constitution violations. No complexity justification required.
