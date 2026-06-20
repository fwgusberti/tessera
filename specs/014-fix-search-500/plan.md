# Implementation Plan: Fix Search Endpoint 500 Error

**Branch**: `014-fix-search-500` | **Date**: 2026-06-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/014-fix-search-500/spec.md`

## Summary

The `POST /v1/search` endpoint returns HTTP 500 for all queries because unhandled exceptions from the Ollama embedding service and potentially malformed SQL parameter bindings propagate to the global error handler. The fix adds graceful error handling for the embedding service (returning 503 instead of 500), validates SQL array parameter binding for `allowed_confidentiality`, and adds defensive empty-result handling for degenerate inputs.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI 0.115+, SQLAlchemy 2.0 (async), psycopg 3.x, pgvector 0.3, httpx 0.27, pydantic 2.0, structlog 24.0

**Storage**: PostgreSQL 15+ with pgvector extension; `chunks` table with `vector(768)` embedding column (migration 0002)

**Testing**: pytest with anyio, `--cov-fail-under=85` enforced; tests live in `apps/api/tests/{unit,integration,contract,security}`

**Target Platform**: Linux server (Docker/Kubernetes)

**Project Type**: Web service (FastAPI)

**Performance Goals**: Search response under 5 seconds including Ollama round-trip

**Constraints**: No new dependencies; fix must not change the public API contract; all existing tests must continue to pass

**Scale/Scope**: Single search endpoint (`POST /v1/search`); no schema migrations needed

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. DDD — domain separate from infrastructure | ✅ Pass | Error handling stays in the router/adapter layer; no domain changes |
| II. Separation of Concerns | ✅ Pass | Router handles HTTP concerns; adapter handles Ollama I/O |
| III. Data Locality & Consent | ✅ N/A | No client-side persistence involved |
| IV. TDD (NON-NEGOTIABLE) | ✅ Pass | Unit tests for error paths written before code; 85% coverage maintained |
| V. Quality Gates (Ruff + Black) | ✅ Pass | All changes must pass `ruff check` and `black --check` |
| Stack — PostgreSQL only | ✅ Pass | No storage changes |
| Stack — Redis only for caching | ✅ N/A | No caching layer touched |
| Security — JWT auth | ✅ Pass | `require_user` already in place; not changing auth |
| Security — Audit logging | ✅ N/A | Search is a read-only operation; no state change to audit |

*Re-check post-design*: No violations found after Phase 1 design. No Complexity Tracking required.

## Project Structure

### Documentation (this feature)

```text
specs/014-fix-search-500/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── search.yaml      # Phase 1 output
└── tasks.md             # Phase 2 output (via /speckit-tasks)
```

### Source Code (repository root)

```text
apps/api/
├── tessera_api/
│   ├── routers/
│   │   └── search.py              # MODIFIED — add error handling
│   ├── adapters/
│   │   ├── embeddings.py          # MODIFIED — wrap httpx errors
│   │   └── repo.py                # MODIFIED — fix array parameter binding
│   └── rag/
│       └── retrieval.py           # UNCHANGED (logic is correct)
└── tests/
    ├── unit/
    │   ├── test_ollama_embedding.py    # EXISTING — may need new error-path tests
    │   └── test_search_router.py       # NEW — unit tests for router error handling
    ├── contract/
    │   └── test_search.py              # EXISTING — should still pass unchanged
    └── integration/
        └── test_search_integration.py  # NEW — integration test for happy path
```

**Structure Decision**: Single web service; modifications confined to `apps/api/`. No new files except test files.

## Phase 0: Research

See [research.md](research.md).

## Phase 1: Design

### Root Cause Analysis

Three distinct failure modes cause the 500 error:

**Cause 1 — Unhandled `httpx` exceptions from Ollama (most likely for "mamadeira")**

`OllamaEmbeddingProvider.embed()` calls `response.raise_for_status()` which raises `httpx.HTTPStatusError` on non-2xx responses, and network failures raise `httpx.ConnectError` / `httpx.ConnectTimeout`. Neither is caught in the search router, so they propagate to the global `@app.exception_handler(Exception)` → 500.

**Fix**: Catch `httpx.HTTPError` in the search router and raise `fastapi.HTTPException(status_code=503)`.

**Cause 2 — `allowed_confidentiality` Python list passed to `ANY()`**

In `SqlChunkRepository.search()`:
```python
"allowed_confidentiality": allowed_levels,   # Python list ['internal', 'confidential']
```
and in SQL:
```sql
AND c.confidentiality = ANY(:allowed_confidentiality)
```
When SQLAlchemy `text()` receives a Python `list` as a bind value, the behavior with psycopg3 is adapter-dependent. The safe approach is to pass it as a PostgreSQL array literal `{internal,confidential}` and use `CAST(:allowed_confidentiality AS text[])`.

**Fix**: Serialize `allowed_confidentiality` the same way `space_ids` is serialized — as a `{val1,val2}` string and cast it explicitly in SQL.

**Cause 3 — No graceful handling of empty `effective_space_ids`**

If no spaces exist in the database, `effective_space_ids = []` and the SQL gets `CAST('{}' AS uuid[])`. This is technically valid PostgreSQL, but will always return zero rows — not an error. This is already handled gracefully and is not a bug, but worth documenting.

### Changes Required

#### `apps/api/tessera_api/routers/search.py`

Wrap the Ollama call in a try/except and raise HTTP 503:

```python
import httpx
from fastapi import HTTPException

try:
    embeddings = await embedding_provider.embed([body.query])
except httpx.HTTPError as exc:
    raise HTTPException(status_code=503, detail="Embedding service unavailable") from exc

query_embedding = embeddings[0]
```

#### `apps/api/tessera_api/adapters/repo.py` — `SqlChunkRepository.search()`

Fix the `allowed_confidentiality` binding:

```python
# Before
"allowed_confidentiality": allowed_levels,

# After
"allowed_confidentiality": "{" + ",".join(allowed_levels) + "}",
```

And in the SQL:
```sql
-- Before
AND c.confidentiality = ANY(:allowed_confidentiality)

-- After
AND c.confidentiality = ANY(CAST(:allowed_confidentiality AS text[]))
```

#### New test: `apps/api/tests/unit/test_search_router.py`

Unit tests covering:
- Ollama `httpx.HTTPStatusError` → router returns 503
- Ollama `httpx.ConnectError` → router returns 503
- Successful Ollama response with empty chunk results → router returns 200 with `{"results": []}`

### No Schema Changes Needed

The `chunks` table schema is correct (migration 0002 sets `vector(768)`). No new migrations.

### API Contract (unchanged)

The public API contract for `POST /v1/search` is unchanged. The only behavioral change is:
- 500 → 503 when Ollama is unavailable
- 500 → 200 when SQL array binding was the issue

See [contracts/search.yaml](contracts/search.yaml) for the full OpenAPI contract.
