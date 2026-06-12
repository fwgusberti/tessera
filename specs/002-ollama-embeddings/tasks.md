# Tasks: Local Ollama Embedding Provider

**Input**: Design documents from `specs/002-ollama-embeddings/`

**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ollama-embed-api.md ✅ quickstart.md ✅

**Tests**: Included — Constitution Principle IV (TDD) is non-negotiable. Test tasks are mandatory.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on sibling tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Blocking Prerequisite)

**Purpose**: Update application configuration — this change gates every other task because both the adapter and the compose file reference the new settings.

- [X] T001 Update `apps/api/tessera_api/config.py`: remove `voyage_api_key: str = ""`, add `ollama_base_url: str = "http://ollama:11434"`, change `embedding_model` default to `"nomic-embed-text"`, change `embedding_dimensions` default to `768`

**Checkpoint**: Config is updated. Adapter and compose changes can now proceed.

---

## Phase 2: Foundational — OllamaEmbeddingProvider Adapter

**Purpose**: Implement the new embedding adapter with TDD. Every user story depends on this adapter existing and being correct.

**⚠️ CRITICAL**: TDD mandate (Constitution IV) — write failing tests FIRST, confirm they fail, THEN implement.

- [X] T002 Write failing unit tests for `OllamaEmbeddingProvider` in `apps/api/tests/unit/test_ollama_embedding.py` (create file and directory if absent): four tests — (1) `test_dimensions_property_returns_768`, (2) `test_embed_passes_model_and_texts_in_body` (mock httpx, assert request JSON contains `model` and `input`), (3) `test_embed_returns_embeddings_from_response` (mock httpx returning `{"embeddings": [[0.1]*768]}`, assert return value), (4) `test_embed_raises_on_http_error` (mock httpx returning 500, assert `httpx.HTTPStatusError` propagates). Run tests and confirm all four FAIL before proceeding to T003.
- [X] T003 Replace `VoyageEmbeddingProvider` with `OllamaEmbeddingProvider` in `apps/api/tessera_api/adapters/embeddings.py`: delete the entire `VoyageEmbeddingProvider` class and its `_VOYAGE_API_URL` constant; add `OllamaEmbeddingProvider` reading `ollama_base_url`, `embedding_model`, `embedding_dimensions` from settings; `embed()` POSTs to `/api/embed` with `{"model": self._model, "input": texts}` using `httpx.AsyncClient(base_url=self._base_url, timeout=60.0)` and returns `response.json()["embeddings"]`; `dimensions` property returns `self._dimensions` (depends on T001, T002)
- [X] T004 Run the unit tests from T002 against the implementation from T003; confirm all four pass; confirm statement coverage ≥ 85% for `apps/api/tessera_api/adapters/embeddings.py` (depends on T003)

**Checkpoint**: `OllamaEmbeddingProvider` exists, is tested, and all tests pass. User story phases can now proceed.

---

## Phase 3: User Story 1 — Developer Runs Without External Credentials (Priority: P1) 🎯 MVP

**Goal**: A developer starts the full compose stack and generates embeddings locally with no API key.

**Independent Test**: `docker compose -f deploy/docker-compose.yml up -d`; confirm stack starts healthy; `docker compose exec api env | grep -i voyage` returns nothing; `curl http://localhost:11434/api/embed -d '{"model":"nomic-embed-text","input":["hello"]}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['embeddings'][0]))"` prints `768`.

- [X] T005 [US1] Update `deploy/docker-compose.yml`: (a) add `ollama` service — image `ollama/ollama:latest`, port `11434:11434`, volume `ollama_data:/root/.ollama`, entrypoint `/bin/sh -c "ollama serve & sleep 5 && ollama pull nomic-embed-text && wait"`, healthcheck `test: ["CMD-SHELL", "ollama list | grep nomic-embed-text"]` with `interval: 10s`, `timeout: 30s`, `retries: 30`, `start_period: 10s`; (b) remove `VOYAGE_API_KEY: ${VOYAGE_API_KEY:-}` from both `api` and `worker` `environment` blocks; (c) add `ollama: condition: service_healthy` to `depends_on` in both `api` and `worker`; (d) add `ollama_data:` to the top-level `volumes` block (depends on T003)

**Checkpoint**: User Story 1 is complete and independently testable. Stack starts offline-capable (after first model pull).

---

## Phase 4: User Story 2 — Existing Search Behaviour Preserved (Priority: P2)

**Goal**: All API endpoints that call `embed()` use the new provider; semantic search returns results.

**Independent Test**: After completing Phase 2 + Phase 3 + this phase, submit a search query (`POST /search`) and confirm it returns results without errors referencing Voyage or requiring an API key.

- [X] T006 [P] [US2] Update `apps/api/tessera_api/routers/search.py`: replace `from tessera_api.adapters.embeddings import VoyageEmbeddingProvider` with `from tessera_api.adapters.embeddings import OllamaEmbeddingProvider`; replace `VoyageEmbeddingProvider()` instantiation with `OllamaEmbeddingProvider()` (depends on T003)
- [X] T007 [P] [US2] Update `apps/api/tessera_api/routers/assistant.py`: same import and instantiation replacement as T006 — `VoyageEmbeddingProvider` → `OllamaEmbeddingProvider` (depends on T003)
- [X] T008 [P] [US2] Update `apps/workers/tessera_workers/indexing/_index.py`: replace `from tessera_api.adapters.embeddings import VoyageEmbeddingProvider` with `from tessera_api.adapters.embeddings import OllamaEmbeddingProvider`; replace `VoyageEmbeddingProvider()` with `OllamaEmbeddingProvider()` (depends on T003)

**Checkpoint**: User Story 2 is complete. Zero references to `VoyageEmbeddingProvider` remain in `apps/` — verify with `grep -rn VoyageEmbeddingProvider apps/ --include="*.py"`.

---

## Phase 5: User Story 3 — Existing Vector Data Migrated (Priority: P3)

**Goal**: The `chunks.embedding` column is changed to `vector(768)` via a reversible Alembic migration; the HNSW index is recreated; existing vectors are cleared.

**Independent Test**: `docker compose exec api alembic -c /app/db/migrations/alembic.ini upgrade head`; then `docker compose exec postgres psql -U tessera tessera -c "\d chunks" | grep embedding` shows `vector(768)`; then ingest a document and confirm `array_length(embedding::real[], 1) = 768` in the chunks table.

**⚠️ CRITICAL**: TDD mandate (Constitution IV) — write the failing integration test FIRST, confirm it fails, THEN create the migration.

- [X] T009 [US3] Write failing integration test for migration 0002 in `apps/api/tests/integration/test_migration_0002.py` (create file and directory if absent): the test must (1) initialize a test database at Alembic revision `0001`, (2) apply `upgrade()` to revision `0002`, (3) assert the `chunks.embedding` column type is `vector(768)` by querying `information_schema.columns` or `pg_attribute`, (4) assert index `ix_chunks_embedding_hnsw` exists on the `chunks` table by querying `pg_indexes`, (5) apply `downgrade()` and assert the column returns to `vector(1024)`. Run and confirm the test FAILS before proceeding to T010.
- [X] T010 [US3] Create `db/migrations/versions/0002_ollama_embeddings.py`: set `revision = "0002"`, `down_revision = "0001"`; `upgrade()` must (1) `op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")`, (2) `op.execute("DELETE FROM chunks")`, (3) `op.execute("ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(768)")`, (4) `op.execute("CREATE INDEX ix_chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)")`; `downgrade()` must reverse these steps with `vector(1024)`; run T009 tests and confirm all pass (depends on T009)

**Checkpoint**: User Story 3 is complete. Integration test passes, migration applies cleanly from both a fresh schema and an existing database.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Linting, formatting, and end-to-end validation.

- [X] T011 [P] Run `ruff check apps/api/tessera_api/adapters/embeddings.py apps/api/tessera_api/config.py apps/api/tessera_api/routers/search.py apps/api/tessera_api/routers/assistant.py apps/workers/tessera_workers/indexing/_index.py db/migrations/versions/0002_ollama_embeddings.py apps/api/tests/integration/test_migration_0002.py` and fix any violations; run `black` on the same files
- [X] T012 Execute quickstart.md validation: confirm zero voyage references (`grep -rn "VoyageEmbeddingProvider\|voyage_api_key\|VOYAGE_API_KEY" apps/ packages/ deploy/ --include="*.py" --include="*.yml" --include="*.yaml"` returns nothing), run embed curl from quickstart step 3, apply migration from step 4, verify chunk dimension from step 5

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **blocks all user story phases**
- **US1 (Phase 3)**: Depends on Phase 2 (adapter must exist before compose is meaningful to test)
- **US2 (Phase 4)**: Depends on Phase 2 (adapter must exist for import sites to compile)
- **US3 (Phase 5)**: Depends on Phase 1 only; T009 (failing test) can start after Phase 1, T010 (migration) depends on T009; entire Phase 5 can run in parallel with Phases 3–4
- **Polish (Phase 6)**: Depends on all user story phases complete

### User Story Dependencies

- **US1 (P1)**: Requires Foundation (Phase 2) — no dependency on US2 or US3
- **US2 (P2)**: Requires Foundation (Phase 2) — no dependency on US1 or US3; T006/T007/T008 are parallel to each other
- **US3 (P3)**: Requires only Phase 1 (config) — independent of US1 and US2; can start in parallel with Phase 2

### Within Each User Story

- **Phase 2**: T002 (failing tests) → T003 (implementation) → T004 (verify pass) — strictly sequential
- **Phase 3**: T005 (single compose file change) — single task
- **Phase 4**: T006, T007, T008 — fully parallel (different files)
- **Phase 5**: T009 (failing integration test) → T010 (migration implementation) — sequential

---

## Parallel Execution Examples

### Maximum parallelism after Phase 2 completes

```text
# All three of these can run simultaneously:
Task T006: Update search.py import
Task T007: Update assistant.py import
Task T008: Update _index.py import

# US3 can start as soon as Phase 1 (config) is done — runs in parallel with Phases 2–4:
Task T009: Write failing migration integration test
Task T010: Create migration 0002_ollama_embeddings.py (after T009 confirmed failing)
```

### Parallel within Phase 6

```text
Task T011: Ruff/Black on all modified files   ← parallel
Task T012: Quickstart validation               ← depends on T011
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational — TDD + Adapter (T002 → T003 → T004)
3. Complete Phase 3: US1 — Compose changes (T005)
4. **STOP and VALIDATE**: `docker compose up -d`; confirm offline embed works; confirm no VOYAGE_API_KEY
5. Ship / demo MVP

### Incremental Delivery

1. Setup + Foundational → new adapter ready
2. US1 complete → offline local dev works (MVP)
3. US2 complete → search and assistant endpoints use new provider
4. US3 complete → DB migrated; document re-indexing can proceed
5. Polish → clean commit ready for review

### Parallel Team Strategy

With two developers after Phase 2 is done:
- Developer A: US1 (T005) then US2 (T006–T008)
- Developer B: US3 (T009) then start Polish (T010)

---

## Notes

- `[P]` tasks operate on different files with no shared state — safe to run concurrently
- TDD mandate: T002 tests must be committed and confirmed FAILING before T003 begins
- The compose entrypoint script pulls `nomic-embed-text` only if not already in the volume — subsequent restarts are instant and offline
- After T010 (migration), documents must be re-indexed by the worker to repopulate `chunks`; this is operational, not a code task
- Verify the absence of Voyage references at T011 with grep — not by visual inspection
