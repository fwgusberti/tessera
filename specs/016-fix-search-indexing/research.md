# Research: Fix Search Indexing — Worker Env + Reindex Endpoints

**Date**: 2026-06-20

## Decision 1: Root Cause of Continued Search Failure

**Decision**: The primary cause is that `OLLAMA_BASE_URL` is not set in the Celery worker process during local development.

**Rationale**: The API (`tessera_api`) config defaults `ollama_base_url` to `http://ollama:11434` — the Docker Compose internal hostname. The API process is started with `OLLAMA_BASE_URL=http://localhost:11434` (fixed in spec-014/754d38b), but the worker process (`scripts/dev.sh`, `Makefile`) never received this env var. So every indexing task attempts to connect to the Docker-internal hostname from a host process and fails with a connection error. Since `_do_index` has no try/except around the embed call, the exception propagates and Celery marks the task as failed — but nothing is logged at the application level, so the failure is invisible.

**Alternatives considered**:
- Change the config default to `http://localhost:11434` — rejected: would break Docker Compose deployments where Ollama is at `http://ollama:11434`
- Use a separate config class for workers — rejected: unnecessary complexity; env var injection is the correct twelve-factor pattern

---

## Decision 2: Authorization Model for Per-Document Reindex

**Decision**: Check `doc.owner_user_id == user_id OR user_info.is_admin`. No space-level ACL check.

**Rationale**: The existing `publish_document` endpoint uses `require_user` + `owner_user_id` assignment. The codebase has an `is_admin` boolean on the user JWT claims (set by `oidc.py`). Space-level role permissions (`RolePermission`) are keyed by IDP group, not by user ID, so a direct per-user space-admin check would require IDP group resolution — disproportionate complexity for a recovery endpoint. Keeping it owner-or-system-admin is the simplest safe policy that mirrors the existing pattern.

**Alternatives considered**:
- Any authenticated user can reindex — rejected: prevents abuse (hammering the embedding service)
- IDP group / space-admin check — rejected: requires group-to-user resolution not available in the token claims

---

## Decision 3: Bulk Reindex Query Strategy

**Decision**: Use a raw SQL `NOT EXISTS` subquery to find published documents with zero chunks.

**Rationale**: No ORM aggregate exists in `SqlChunkRepository`. The existing pattern in `repo.py` uses raw `text()` SQL for all chunk operations (`upsert_chunks`, `search`, `delete_by_document`). A `NOT EXISTS (SELECT 1 FROM chunks WHERE document_id = d.id)` is the most efficient approach — it short-circuits on the first chunk found and uses the existing `document_id` index on the `chunks` table.

**Alternatives considered**:
- `LEFT JOIN chunks ... WHERE c.id IS NULL` — equivalent performance; `NOT EXISTS` is slightly more readable
- Python-side filter (fetch all docs, then check each) — rejected: N+1 query pattern, unacceptable at scale

---

## Decision 4: Error Logging Library

**Decision**: Use `structlog` (already a worker dependency).

**Rationale**: `structlog` is listed in `apps/workers/pyproject.toml`. Structured JSON logs are essential for observability; `logger.error("indexing_embedding_failed", document_id=..., error=...)` emits a key-value record that is trivially parsed by log aggregators. Re-raising the exception after logging ensures Celery marks the task failed so it can be retried or inspected.

**Alternatives considered**:
- Python stdlib `logging` — less structured; would require a formatter to get key-value logs
- Swallow the exception and return — rejected: silent failures are the root cause of the original problem
