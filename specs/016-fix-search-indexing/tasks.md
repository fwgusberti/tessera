# Tasks: Fix Search Indexing — Worker Env + Reindex Endpoints

**Input**: Design documents from `specs/016-fix-search-indexing/`

**Feature**: Fix search returning no results by correcting worker startup env, adding structured error logging, and adding per-document + bulk reindex endpoints.
**Scope**: P1 env-fix + worker error logging; P2 per-document reindex; P2 bulk admin reindex

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on each other)
- **[US1]**: User Story 1 — Search Returns Matching Documents (env fix + error logging)
- **[US2]**: User Story 2 — Re-index Already Published Documents (per-document endpoint)
- **[US3]**: User Story 3 — Bulk Recovery Reindex (admin bulk endpoint)

---

## Phase 1: Setup

**Purpose**: Confirm test infrastructure is in place

- [x] T001 Confirm pytest, pytest-anyio, and structlog are available in `apps/api` and `apps/workers` venvs — run `uv sync` in each if needed

---

## Phase 2: User Story 1 — Search Returns Matching Documents (Priority: P1) 🎯 MVP

**Goal**: Start the worker with the correct `OLLAMA_BASE_URL` so embedding succeeds in local dev; add structured error logging so failures are never silent.

**Independent Test**: Run `make dev`, publish a document, wait 5 seconds, search for a title keyword — the document appears in results. Worker log shows a structured error if Ollama is stopped before indexing.

### Step 1 — Write failing tests (TDD — Constitution Principle IV)

> Write ALL tests first. Confirm each FAILS before proceeding to implementation.

- [x] T002 [US1] Write failing test `test_embedding_failure_logs_document_id` in `apps/workers/tests/unit/test_indexing_error_handling.py` — mock `embed()` to raise `httpx.ConnectError`, capture structlog output, assert `document_id` key is present in the log record (currently no try/except exists so nothing is logged)
- [x] T003 [US1] Write failing test `test_embedding_failure_re_raises` in `apps/workers/tests/unit/test_indexing_error_handling.py` — mock `embed()` to raise, assert `_do_index` re-raises the exception (currently the exception propagates but without a structured log)

### Step 2 — Implement fixes (after tests confirmed failing)

- [x] T004 [P] [US1] Add `OLLAMA_BASE_URL=http://localhost:11434` to the workers startup line in `scripts/dev.sh` — replace `DATABASE_URL="$DB" REDIS_URL="$REDIS" \` with `DATABASE_URL="$DB" REDIS_URL="$REDIS" OLLAMA_BASE_URL=http://localhost:11434 \` for the `uv run celery` command
- [x] T005 [P] [US1] Add `OLLAMA_BASE_URL=http://localhost:11434` to the `workers` target in `Makefile` — replace `DATABASE_URL=$(DB) REDIS_URL=$(REDIS) \` with `DATABASE_URL=$(DB) REDIS_URL=$(REDIS) OLLAMA_BASE_URL=http://localhost:11434 \`
- [x] T006 [P] [US1] Add `OLLAMA_BASE_URL: http://ollama:11434` to the `worker` service environment in `deploy/docker-compose.yml` — add the line after `REDIS_URL: redis://redis:6379/0`
- [x] T007 [US1] Add structured error logging to `apps/workers/tessera_workers/indexing/_index.py` — import `structlog`, add `logger = structlog.get_logger()`, wrap the `embeddings = await embedding_provider.embed(texts)` block in `try/except Exception as exc:` that calls `logger.error("indexing_embedding_failed", document_id=str(document_id), version_id=str(version_id), error=str(exc))` and then `raise`

**Checkpoint**: Tests T002–T003 pass; `make dev` and `make workers` both export `OLLAMA_BASE_URL=http://localhost:11434`; docker-compose has explicit `OLLAMA_BASE_URL` for the worker.

---

## Phase 3: User Story 2 — Re-index Already Published Documents (Priority: P2)

**Goal**: A document owner or system admin can POST to `/v1/documents/{id}/reindex` to queue an already-published document for re-indexing without re-publishing it.

**Independent Test**: With a published document that has no chunks, call `POST /v1/documents/{id}/reindex` with the owner's JWT → 200 returned, document searchable after ~5 seconds.

### Step 1 — Write failing tests (TDD — Constitution Principle IV)

> Write ALL tests first. Confirm each FAILS before proceeding to implementation.

- [x] T008 [US2] Write failing test `test_reindex_owner_dispatches_task` in `apps/api/tests/unit/test_reindex_router.py` — mock `get_celery_app().send_task`, mock DB returning a published doc whose `owner_user_id` matches caller; POST `/v1/documents/{id}/reindex`; assert `send_task` called with `"tessera.index_document_version"` and correct args; assert 200
- [x] T009 [US2] Write failing test `test_reindex_admin_dispatches_task` in `apps/api/tests/unit/test_reindex_router.py` — same as T008 but caller has `is_admin=True` and is NOT the owner; assert task dispatched and 200 returned
- [x] T010 [US2] Write failing test `test_reindex_non_owner_returns_403` in `apps/api/tests/unit/test_reindex_router.py` — caller is authenticated but neither owner nor admin; assert 403
- [x] T011 [US2] Write failing test `test_reindex_missing_document_returns_404` in `apps/api/tests/unit/test_reindex_router.py` — doc repo returns `None`; assert 404
- [x] T012 [US2] Write failing test `test_reindex_draft_document_returns_400` in `apps/api/tests/unit/test_reindex_router.py` — doc exists but `state.value == "draft"`; assert 400

### Step 2 — Implement endpoint (after tests confirmed failing)

- [x] T013 [US2] Add `POST /v1/documents/{document_id}/reindex` endpoint to `apps/api/tessera_api/routers/documents.py` after `publish_document` — implement authorization check (`is_admin OR doc.owner_user_id == user_id`), state check (`state.value != "published"` → 400), version fetch (no versions → 400), then `get_celery_app().send_task("tessera.index_document_version", args=[str(latest.id), str(document_id), str(doc.space_id)])`, return `{"queued": True, "document_id": str(document_id)}`

**Checkpoint**: Tests T008–T012 pass; per-document reindex endpoint works for owners and admins, rejects others.

---

## Phase 4: User Story 3 — Bulk Recovery Reindex (Priority: P2)

**Goal**: A system admin can POST to `/v1/admin/reindex` to dispatch indexing tasks for all published documents with zero chunks in one call.

**Independent Test**: With 2 published documents and no chunks, call `POST /v1/admin/reindex` with admin JWT → `{"dispatched": 2}`; both documents searchable after ~10 seconds.

### Step 1 — Write failing tests (TDD — Constitution Principle IV)

> Write ALL tests first. Confirm each FAILS before proceeding to implementation.

- [x] T014 [US3] Write failing test `test_bulk_reindex_admin_dispatches_for_unchunked_docs` in `apps/api/tests/unit/test_reindex_router.py` — mock DB query returning 2 rows (published docs with no chunks); mock `send_task`; POST `/v1/admin/reindex` as admin; assert `send_task` called twice with correct args; assert response `{"dispatched": 2}`
- [x] T015 [US3] Write failing test `test_bulk_reindex_non_admin_returns_403` in `apps/api/tests/unit/test_reindex_router.py` — non-admin authenticated user; POST `/v1/admin/reindex`; assert 403
- [x] T016 [US3] Write failing test `test_bulk_reindex_skips_docs_with_existing_chunks` in `apps/api/tests/unit/test_reindex_router.py` — mock DB query returning 0 rows; assert `send_task` not called; assert response `{"dispatched": 0}`

### Step 2 — Implement endpoint (after tests confirmed failing)

- [x] T017 [US3] Add `POST /v1/admin/reindex` endpoint to `apps/api/tessera_api/routers/admin.py` — require `is_admin` (raise 403 otherwise), execute raw SQL `SELECT d.id, d.space_id, dv.id AS version_id FROM documents d JOIN document_versions dv ON dv.id = d.current_version_id WHERE d.state = 'published' AND d.current_version_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM chunks c WHERE c.document_id = d.id)`, call `celery.send_task("tessera.index_document_version", args=[...])` for each row, return `{"dispatched": len(rows)}`

**Checkpoint**: Tests T014–T016 pass; bulk reindex endpoint dispatches correct number of tasks, rejects non-admins.

---

## Phase 5: Polish & Validation

**Purpose**: Coverage gates, code quality, end-to-end smoke test

- [x] T018 Run `ruff check` and `black --check` across changed Python files: `apps/api/tessera_api/routers/documents.py`, `apps/api/tessera_api/routers/admin.py`, `apps/workers/tessera_workers/indexing/_index.py` — fix any violations before marking done
- [x] T019 [P] Run full test suite in `apps/api` and confirm ≥85% statement coverage: `cd apps/api && uv run pytest --cov=tessera_api --cov-fail-under=85`
- [x] T020 [P] Run full test suite in `apps/workers` and confirm ≥85% statement coverage: `cd apps/workers && uv run pytest --cov=tessera_workers --cov-fail-under=85`
- [x] T021 Follow `specs/016-fix-search-indexing/quickstart.md` end-to-end: start `make dev`, publish a document, wait 5 seconds, search for title keyword, verify result appears

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — verify environment only
- **US1 (Phase 2)**: Can start after T001; T002–T003 (tests) are written first; T004–T006 are all [P] once T001 done; T007 after T002–T003 confirmed failing
- **US2 (Phase 3)**: Depends on Phase 2 complete; T008–T012 (tests) written first; T013 after T008–T012 confirmed failing
- **US3 (Phase 4)**: Depends on T013 (same test file); T014–T016 written first; T017 after T014–T016 confirmed failing
- **Polish (Phase 5)**: Depends on all implementation tasks complete

### Task-level Dependencies

| Task | Depends On | Notes |
|------|-----------|-------|
| T002–T003 | T001 | Write tests; same file — sequential |
| T004–T006 | T001 | Fix env vars; different files — all [P] |
| T007 | T002, T003 | Implement logging after tests confirmed failing |
| T008–T012 | T007 | Write per-doc endpoint tests; same file — sequential |
| T013 | T008–T012 | Implement endpoint after all 5 tests confirmed failing |
| T014–T016 | T013 | Write bulk endpoint tests (same file as T008–T012) — sequential |
| T017 | T014–T016 | Implement bulk endpoint after 3 tests confirmed failing |
| T018–T020 | T017 | Polish after all implementation done |
| T021 | T019, T020 | End-to-end only after coverage gates pass |

### Parallel Opportunities

```text
T004  →  scripts/dev.sh                          [P with T005, T006]
T005  →  Makefile                                [P with T004, T006]
T006  →  deploy/docker-compose.yml               [P with T004, T005]

T019  →  apps/api coverage gate                  [P with T020]
T020  →  apps/workers coverage gate              [P with T019]
```

---

## Implementation Strategy

### MVP (User Story 1 only — start here)

1. **Phase 1** (T001): verify environment
2. **US1 Tests** (T002–T003): write and confirm failing
3. **US1 Implementation** (T004–T007): T004–T006 in parallel, T007 sequential
4. **STOP and VALIDATE**: `make dev`, publish a doc, search — result appears
5. Once US1 validated, proceed to US2 then US3

### TDD Discipline (Constitution Principle IV)

For each implementation task group:
1. Write the test → run it → confirm it **FAILS** (red)
2. Implement the fix → run it → confirm it **PASSES** (green)
3. `ruff check` + `black --check` (T018)
4. Commit

---

## Notes

- T004, T005, T006 touch different files and can be applied simultaneously
- T007 adds `import structlog` + `logger = structlog.get_logger()` at module level; keep the try/except tight around just the `embed()` call and the embedding assignment loop
- T013: the `is_admin` check uses `user_info.get("is_admin", False)` — same pattern as existing admin endpoints in `admin.py` and `agent_credentials.py`
- T017: raw SQL follows the existing pattern in `repo.py` (all chunk ops use `text()`); `document_versions` table aliased to `dv`, join on `d.current_version_id = dv.id`
- The `NOT EXISTS (SELECT 1 FROM chunks WHERE document_id = d.id)` clause is more efficient than a `COUNT` aggregate — short-circuits on the first chunk found
