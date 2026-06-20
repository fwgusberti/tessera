# Tasks: Fix Search Endpoint 500 Error

**Input**: Design documents from `specs/014-fix-search-500/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/search.yaml ✅, quickstart.md ✅

**Tests**: Included — Constitution Principle IV (TDD) is non-negotiable: write failing tests before any implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in every task description

---

## Phase 1: Setup

**Purpose**: Verify the development environment and understand the failure surface before writing any code.

- [X] T001 Read `apps/api/tessera_api/routers/search.py` and `apps/api/tessera_api/adapters/repo.py` to confirm the two root causes identified in research.md: (1) unhandled `httpx.HTTPError` in the router, (2) Python list passed to `ANY()` in `SqlChunkRepository.search()`
- [X] T002 Run existing test suite to establish baseline: `cd apps/api && uv run pytest --tb=short -q` — document any pre-existing failures

**Checkpoint**: Baseline established. Root causes confirmed in code.

---

## Phase 2: Foundational — Failing Tests (TDD)

**Purpose**: Write all tests FIRST and verify they FAIL before any implementation. This phase MUST complete before Phase 3.

**⚠️ CRITICAL**: Per Constitution Principle IV, tests must be written and confirmed FAILING before code changes.

- [X] T003 Create `apps/api/tests/unit/test_search_router.py` with a test `test_search_returns_503_when_ollama_raises_http_status_error` — mock `OllamaEmbeddingProvider.embed` to raise `httpx.HTTPStatusError`; assert response status is 503 (will FAIL until fix is applied)
- [X] T004 [P] Add test `test_search_returns_503_when_ollama_raises_connect_error` to `apps/api/tests/unit/test_search_router.py` — mock embed to raise `httpx.ConnectError`; assert 503 (will FAIL)
- [X] T005 [P] Add test `test_search_returns_200_with_empty_results_when_no_chunks_match` to `apps/api/tests/unit/test_search_router.py` — mock embed to return valid embedding, mock `acl_first_search` to return `[]`; assert 200 with `{"results": []}` (will FAIL or may already pass; confirm)
- [X] T006 Add test `test_allowed_confidentiality_is_serialized_as_pg_array_string` to `apps/api/tests/unit/test_search_router.py` — call `SqlChunkRepository.search()` with a mocked session; verify the bind parameter `allowed_confidentiality` is a `{...}` string, not a Python list (will FAIL until fix)
- [X] T007 Run `cd apps/api && uv run pytest tests/unit/test_search_router.py -v` and confirm T003, T004, T006 FAIL (and T005 status is noted)

**Checkpoint**: Failing tests confirmed. Implementation may now begin.

---

## Phase 3: User Story 1 — Search Returns 200 (Priority: P1) 🎯 MVP

**Goal**: Eliminate the 500 error — any authenticated search query returns 200 (or 503 if Ollama is down, never 500).

**Independent Test**: `POST /v1/search {"query": "mamadeira"}` with valid JWT → HTTP 200 with `{"results": [...]}`.

### Implementation for User Story 1

- [X] T008 [US1] In `apps/api/tessera_api/routers/search.py`: add `import httpx` at the top of the file (it is already a project dependency — no new packages needed)
- [X] T009 [US1] In `apps/api/tessera_api/routers/search.py`: wrap the `embedding_provider.embed([body.query])` call in a `try/except httpx.HTTPError` block that raises `HTTPException(status_code=503, detail="Embedding service unavailable")` — place the try/except around lines 31–32 in the current file
- [X] T010 [US1] In `apps/api/tessera_api/adapters/repo.py` `SqlChunkRepository.search()`: change `"allowed_confidentiality": allowed_levels` to `"allowed_confidentiality": "{" + ",".join(allowed_levels) + "}"` (same serialization pattern as `space_ids`)
- [X] T011 [US1] In `apps/api/tessera_api/adapters/repo.py` `SqlChunkRepository.search()`: in the SQL string, change `AND c.confidentiality = ANY(:allowed_confidentiality)` to `AND c.confidentiality = ANY(CAST(:allowed_confidentiality AS text[]))`
- [X] T012 [US1] Run `cd apps/api && uv run pytest tests/unit/test_search_router.py -v` — confirm T003, T004, T006 now PASS
- [X] T013 [US1] Run `cd apps/api && uv run ruff check tessera_api/routers/search.py tessera_api/adapters/repo.py` and `uv run black --check tessera_api/routers/search.py tessera_api/adapters/repo.py` — fix any Ruff/Black violations

**Checkpoint**: US1 complete. `POST /v1/search` returns 200 (not 500). Ollama failures return 503. Tests T003, T004, T006 GREEN.

---

## Phase 4: User Story 2 — Empty Results (Priority: P2)

**Goal**: Confirm that a search with no matching documents returns `{"results": []}` with HTTP 200, not an error.

**Independent Test**: `POST /v1/search {"query": "zzz-no-match-xyz"}` → HTTP 200 with `{"results": []}`.

### Implementation for User Story 2

- [X] T014 [US2] Verify test T005 (from Phase 2) now passes after US1 changes — run `cd apps/api && uv run pytest tests/unit/test_search_router.py::test_search_returns_200_with_empty_results_when_no_chunks_match -v`
- [X] T015 [US2] If T005 was already passing before US1 changes, add a note in the test confirming the empty-path was always safe; if it was FAILING, confirm it now passes
- [X] T016 [US2] Review `apps/api/tessera_api/routers/search.py` lines 51–61 (the result comprehension) — confirm that when `raw_results = []`, the list comprehension produces `[]` and the return is `{"results": []}` with no exception

**Checkpoint**: US2 confirmed. Empty search results return 200 + `[]` as specified in FR-002.

---

## Phase 5: User Story 3 — ACL & Published-Only Filter (Priority: P3)

**Goal**: Confirm that the existing `state = 'published'` and confidentiality filters are preserved and still enforced after the array-binding fix.

**Independent Test**: Existing contract tests in `tests/contract/test_search.py` pass without modification.

### Implementation for User Story 3

- [X] T017 [US3] Run existing contract tests: `cd apps/api && uv run pytest tests/contract/test_search.py -v` — all 3 tests must pass (`test_search_result_has_required_fields`, `test_search_only_returns_published_docs`, `test_restricted_documents_excluded_from_results`)
- [X] T018 [US3] Review the SQL in `apps/api/tessera_api/adapters/repo.py` after T011 — confirm `AND d.state = 'published'` and `AND c.embedding IS NOT NULL` are still present and unmodified
- [X] T019 [US3] Verify `filter_published` and `filter_by_confidentiality` in `apps/api/tessera_api/rag/retrieval.py` are untouched — these functions are tested by the existing contract suite and must not change

**Checkpoint**: US3 confirmed. ACL and published-only invariants intact. Contract tests GREEN.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Coverage gate, full suite health, quality gates.

- [X] T020 [P] Run full test suite with coverage: `cd apps/api && uv run pytest --cov=tessera_api --cov-report=term-missing` — confirm coverage ≥ 85% (Constitution Principle IV gate). Note: 85% gate failure is pre-existing across unrelated routers; search.py is at 100%.
- [X] T021 [P] Run `cd apps/api && uv run ruff check tessera_api/` — zero violations
- [X] T022 [P] Run `cd apps/api && uv run black --check tessera_api/` — zero violations
- [ ] T023 Run quickstart.md Scenario 1 manually against a running stack: `POST /v1/search {"query": "mamadeira"}` → confirm HTTP 200
- [X] T024 [P] If coverage is below 85%: add missing test cases to `apps/api/tests/unit/test_search_router.py` to cover any uncovered branches in `search.py` and `repo.py`

**Checkpoint**: All gates pass. Feature is complete.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (TDD — Failing Tests)**: Depends on Phase 1 — BLOCKS Phases 3–5
- **Phase 3 (US1)**: Depends on Phase 2 — this is the core fix
- **Phase 4 (US2)**: Depends on Phase 3 (empty-path verification relies on the array-binding fix)
- **Phase 5 (US3)**: Can run in parallel with Phase 4 — only reads existing code and tests
- **Phase 6 (Polish)**: Depends on Phases 3, 4, 5

### User Story Dependencies

- **US1 (P1)**: No story dependencies — directly implements the fix
- **US2 (P2)**: Depends on US1 changes being in place (T014 verifies T005 after US1)
- **US3 (P3)**: Independent of US1/US2 — validates existing ACL behavior is preserved

### Within Each Phase

- T003 must exist before T004/T005/T006 (all in the same new file)
- T008 (import) before T009 (try/except) — same file, sequential edits
- T010 and T011 are in the same function in `repo.py` — do both together

### Parallel Opportunities

- T003, T004, T005, T006 are all in the same new file — write sequentially
- T010 + T011 are in the same function — apply together as one edit
- T008 + T009 are in the same function — apply together as one edit
- T020, T021, T022, T024 (Polish) can run in parallel

---

## Parallel Example: Phase 2 (Failing Tests)

```text
# All four test stubs can be written in one pass into the new file:
Task T003: test_search_returns_503_when_ollama_raises_http_status_error
Task T004: test_search_returns_503_when_ollama_raises_connect_error
Task T005: test_search_returns_200_with_empty_results_when_no_chunks_match
Task T006: test_allowed_confidentiality_is_serialized_as_pg_array_string
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Write failing tests (T003–T007)
3. Complete Phase 3: Apply both fixes (T008–T013)
4. **STOP and VALIDATE**: `POST /v1/search {"query": "mamadeira"}` returns 200
5. Run Phase 6 quality gates (T020–T022)
6. Ship — US1 alone eliminates the reported bug

### Incremental Delivery

1. Setup + TDD → failing tests baseline
2. US1 fixes → green tests + 200 response → MVP shipped
3. US2 verification → empty-results path confirmed safe
4. US3 verification → ACL invariants confirmed intact
5. Polish → 85% coverage gate + full Ruff/Black clean

---

## Notes

- [P] tasks = touch different files or are otherwise parallelizable
- [USn] label maps each task to its user story for traceability
- Constitution Principle IV (TDD) is mandatory — tests MUST fail before implementation
- Constitution Principle V (Ruff + Black) gates must pass before any commit
- No new packages, no schema migrations — this is a pure code fix
- `apps/api/tessera_api/rag/retrieval.py` is NOT touched — its logic is correct
