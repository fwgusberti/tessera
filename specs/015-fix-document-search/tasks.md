# Tasks: Fix Document Search Returns No Results

**Input**: Design documents from `specs/015-fix-document-search/`

**Feature**: Restore search to return results for published document title keywords
**Scope**: P1 fix only — three backend bugs + one frontend omission (P2/P3 deferred)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on each other)
- **[US1]**: User Story 1 — Search Returns Matching Documents

---

## Phase 1: Setup

**Purpose**: Confirm test infrastructure is in place; no new dependencies or migrations needed

- [x] T001 Confirm `pytest`, `pytest-anyio`, and `pytest-cov` are available in `apps/api` and `apps/workers` virtual environments (run `uv sync` in each if needed)

---

## Phase 2: User Story 1 — Search Returns Matching Documents (Priority: P1) 🎯 MVP

**Goal**: Published documents whose titles contain the search query must appear in search results; drafts must not; the frontend must show a "No results found" message when zero results are returned.

**Independent Test**: Create a document titled "Quarterly Budget Review", publish it, wait for indexing, search for "quarterly" → document appears in results.

**Bugs addressed**:
- Bug 1+2: `upsert_chunks` builds SQL but never executes it, and omits the `embedding` field
- Bug 3: `publish_document` never dispatches the `index_document_version` Celery task
- Bug 4 (frontend): No "No results found" message when `results` is empty

### Step 1 — Write failing tests (TDD — constitution Principle IV)

> Write ALL tests first. Confirm each FAILS before proceeding to implementation.

- [x] T002 [US1] Write failing test `test_upsert_chunks_executes_insert_for_each_chunk` in `apps/api/tests/unit/test_chunk_repository.py` — verifies `session.execute` is called once per chunk (currently never called)
- [x] T003 [US1] Write failing test `test_upsert_chunks_includes_embedding_in_params` in `apps/api/tests/unit/test_chunk_repository.py` — verifies `embedding` key is present in execute params (currently missing)
- [x] T004 [US1] Write failing test `test_upsert_chunks_skips_null_embedding_gracefully` in `apps/api/tests/unit/test_chunk_repository.py` — verifies chunk with `embedding=None` does not raise
- [x] T005 [P] [US1] Write failing test `test_publish_dispatches_index_task` in `apps/api/tests/unit/test_documents_router.py` — mock `index_document_version.delay`, publish a document, assert `.delay()` called with correct `(version_id, document_id, space_id)` strings (currently never called)
- [x] T006 [P] [US1] Write failing test `test_title_prepended_to_first_chunk_text` in `apps/workers/tests/unit/test_indexing.py` — mock DB + embeddings, run `_do_index`, assert first chunk text starts with the document title (currently title is not prepended)
- [x] T007 [P] [US1] Write failing test `test_title_in_chunk_when_content_does_not_contain_title` in `apps/workers/tests/unit/test_indexing.py` — document title not in `content_markdown`, assert title appears in chunk text after indexing
- [x] T008 [P] [US1] Write failing test `renders_no_results_message_after_empty_search` in `apps/web/tests/search.test.tsx` — mock API returning `{results:[]}`, submit a search, assert "No results found" is visible (currently rendered nothing)
- [x] T009 [P] [US1] Write failing test `does_not_show_no_results_before_any_search` in `apps/web/tests/search.test.tsx` — on mount with no search submitted, assert "No results found" is not present

### Step 2 — Implement fixes (after tests confirmed failing)

- [x] T010 [US1] Fix `upsert_chunks` in `apps/api/tessera_api/adapters/repo.py` — replace broken `insert(type(...)).values(...)` with `await self._session.execute(text("INSERT INTO chunks ... ON CONFLICT (id) DO UPDATE SET ..."), {..., "embedding": str(chunk.embedding) if chunk.embedding else None, ...})` including the `embedding` field; remove `# noqa: F841`
- [x] T011 [P] [US1] Dispatch indexing Celery task from `publish_document` in `apps/api/tessera_api/routers/documents.py` — after the DB transaction block, import and call `index_document_version.delay(str(latest.id), str(document_id), str(doc.space_id))`
- [x] T012 [P] [US1] Prepend document title to content before chunking in `apps/workers/tessera_workers/indexing/_index.py` — after loading `document`, add `title_prefix = f"# {document.title}\n\n"` and create `version_with_title = version.model_copy(update={"content_markdown": title_prefix + version.content_markdown})`, pass `version_with_title` to `chunk_document()`
- [x] T013 [P] [US1] Add `searched` state flag and "No results found" conditional message to `apps/web/app/search/page.tsx` — add `const [searched, setSearched] = useState(false)`, call `setSearched(true)` in `handleSearch`, render `<p>No results found.</p>` when `searched && !loading && mode === "search" && results.length === 0 && !answer`

**Checkpoint**: All tests pass; search returns matching documents for published documents' title keywords; drafts are excluded; "No results found" shown on empty query.

---

## Phase 3: Polish & Validation

**Purpose**: Coverage gates, integration smoke test, and code quality

- [ ] T014 Run full test suite in `apps/api` and confirm ≥85% statement coverage: `cd apps/api && uv run pytest --cov=tessera_api --cov-fail-under=85`
- [ ] T015 [P] Run full test suite in `apps/workers` and confirm ≥85% statement coverage: `cd apps/workers && uv run pytest --cov=tessera_workers --cov-fail-under=85`
- [x] T016 [P] Run `ruff check` and `black --check` across `apps/api/tessera_api` and `apps/workers/tessera_workers` — fix any violations before committing
- [ ] T017 Follow `specs/015-fix-document-search/quickstart.md` end-to-end scenario: create + publish a document, wait for worker, search for a title keyword, verify result appears in response

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — verify environment only
- **US1 Tests (T002–T009)**: Can all start after T001; T002 through T009 can all run in parallel (different test files)
- **US1 Implementation (T010–T013)**: Each depends only on its own test(s) being written and confirmed failing; T010–T013 can run in parallel with each other (different source files)
- **Polish (Phase 3)**: Depends on all US1 implementation tasks complete

### Task-level Dependencies

| Task | Depends On | Notes |
|------|-----------|-------|
| T002–T009 | T001 | Write tests; independent of each other |
| T010 | T002, T003, T004 | Fix `upsert_chunks`; all three tests cover this method |
| T011 | T005 | Fix publish dispatch; after test confirmed failing |
| T012 | T006, T007 | Fix title prepend; after both title tests confirmed failing |
| T013 | T008, T009 | Fix frontend; after both frontend tests confirmed failing |
| T014, T015, T016 | T010–T013 | Run after all fixes |
| T017 | T014, T015 | End-to-end only after coverage gates pass |

### Parallel Opportunities

```text
# All failing tests can be written in parallel (different files):
T002, T003, T004  →  apps/api/tests/unit/test_chunk_repository.py  (same file — sequential)
T005              →  apps/api/tests/unit/test_documents_router.py  [P] different file
T006  →  apps/workers/tests/unit/test_indexing.py            [P] different file
T008  →  apps/web/tests/search.test.tsx                      [P] different file

# All implementation fixes can run in parallel (different files):
T010  →  apps/api/tessera_api/adapters/repo.py               [P] (after T002-T004)
T011  →  apps/api/tessera_api/routers/documents.py           [P] (after T005)
T012  →  apps/workers/tessera_workers/indexing/_index.py     [P] (after T006-T007)
T013  →  apps/web/app/search/page.tsx                        [P] (after T008-T009)

# Polish tasks:
T014  →  apps/api coverage gate                              [P with T015, T016]
T015  →  apps/workers coverage gate                          [P with T014, T016]
T016  →  ruff + black                                        [P with T014, T015]
```

---

## Implementation Strategy

### MVP (only 1 user story — start here)

1. Complete **Phase 1** (T001): verify environment
2. Write **all failing tests** (T002–T009): confirm each fails
3. Implement **all four fixes** (T010–T013): T010, T011, T012, T013 can be done in parallel
4. Run **Phase 3 polish** (T014–T017): coverage gate + end-to-end validation
5. **STOP and VALIDATE** using `quickstart.md`

### TDD Discipline (Constitution Principle IV)

For each fix group:
1. Write the test → run it → confirm it **FAILS** (red)
2. Implement the fix → run it → confirm it **PASSES** (green)
3. `ruff check` + `black --check` — fix any violations (T016)
4. Commit

---

## Notes

- All four fixes touch **different files** — T010–T013 can be implemented by parallel agents or in parallel by one agent in separate edit sessions
- `upsert_chunks` uses raw SQL intentionally (no `ChunkModel` ORM class exists — consistent with `search()` and `delete_by_document()`)
- The Celery task dispatch in T011 must happen **outside** the `async with get_db()` block so the DB transaction is committed before the worker reads it
- The `# noqa: F841` comment removed in T010 — its only purpose was to hide the unexecuted-statement bug
- Draft exclusion is already enforced by `AND d.state = 'published'` in the search SQL — no change needed there
