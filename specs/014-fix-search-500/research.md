# Research: Fix Search Endpoint 500 Error

**Feature**: 014-fix-search-500  
**Date**: 2026-06-20

## Root Cause Investigation

### Finding 1: Unhandled httpx Exceptions (PRIMARY CAUSE)

**Decision**: Catch `httpx.HTTPError` in `routers/search.py` and raise `HTTPException(503)`.

**Rationale**: `OllamaEmbeddingProvider.embed()` raises `httpx.HTTPStatusError` on non-2xx Ollama responses and `httpx.ConnectError` / `httpx.TimeoutException` on network failures. These are subclasses of `httpx.HTTPError`. None are caught in the router; they propagate to FastAPI's global 500 handler.

**Alternatives considered**:
- Catch in `OllamaEmbeddingProvider.embed()` itself and raise a domain exception — rejected because the adapter layer should raise transport errors; it's the caller's job to map them to HTTP responses.
- Add middleware — rejected as overkill; the fix belongs at the call site.

---

### Finding 2: `ANY(:list)` with Python list in SQLAlchemy text()

**Decision**: Serialize `allowed_confidentiality` to PostgreSQL array literal string `{val1,val2}` and use `CAST(:param AS text[])` in SQL, consistent with how `space_ids` is already handled.

**Rationale**: SQLAlchemy `text()` bind parameters pass values as scalar scalars to the underlying DBAPI. psycopg3 can adapt Python lists to PostgreSQL arrays in ORM/Core column-bound contexts, but in raw `text()` queries the adaptation is unreliable. The existing code already handles `space_ids` correctly via `"{" + ",".join(space_id_strs) + "}"`. The same pattern must be applied to `allowed_confidentiality`.

**Evidence**: The `space_ids` parameter in the same query uses `CAST(:space_ids AS uuid[])` with the `{uuid1,uuid2}` literal format — confirming the project already settled on this pattern.

**Alternatives considered**:
- Use `bindparam()` with `ARRAY` type — adds SQLAlchemy Core dependency to a raw SQL query; inconsistent with surrounding code style.
- Pass a tuple instead of a list — still unreliable for `ANY()` in text() context.

---

### Finding 3: `build_citation()` key access

**Decision**: No fix needed here.

**Rationale**: `build_citation()` accesses `chunk_row["id"]` and `chunk_row["document_version_id"]` which are present in the SQL SELECT column list. No KeyError risk.

---

### Finding 4: Empty `effective_space_ids`

**Decision**: No fix needed; behavior is correct.

**Rationale**: When no spaces exist, `effective_space_ids = []` → SQL receives `CAST('{}' AS uuid[])` → returns zero rows → endpoint returns `{"results": []}`. This is the correct behavior per FR-002.

---

## Test Strategy

| Scenario | Type | Location |
|----------|------|----------|
| Ollama HTTPStatusError → 503 | Unit | `tests/unit/test_search_router.py` |
| Ollama ConnectError → 503 | Unit | `tests/unit/test_search_router.py` |
| Successful embed + empty chunks → 200 + `[]` | Unit | `tests/unit/test_search_router.py` |
| `allowed_confidentiality` binding serialization | Unit | `tests/unit/test_search_router.py` |
| Existing contract tests | Contract | `tests/contract/test_search.py` (unchanged) |

## Dependencies & Constraints

- `httpx` is already a dependency of `tessera-api` — no new packages needed.
- No migration required — schema is correct.
- Ruff + Black must pass; no bare `except` clauses.
- 85% coverage gate must be maintained.
