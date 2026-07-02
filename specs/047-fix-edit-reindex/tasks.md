# Tasks: Reindex Document on Finishing an Edit

**Input**: Design documents from `specs/047-fix-edit-reindex/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**TDD**: Constitution Principle IV is non-negotiable — each new test below MUST be written and confirmed FAILING before its corresponding implementation task.

**Organization**: All three user stories converge on one guarded conditional in `finish_document_draft`. US1's implementation task (T004) is the only code change; US2 and US3 are proven by tests that exercise the same guard from different angles, per the same pattern used in `specs/013-fix-publish-version-update/tasks.md`.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Verify Environment)

**Purpose**: Confirm the test environment is functional before making changes. No new files or dependencies required for this fix.

- [X] T001 Confirm the draft router test suite runs and all existing tests pass: `cd apps/api && .venv/bin/python -m pytest tests/unit/test_documents_draft_router.py -v --no-cov`

---

## Phase 2: Foundational (Shared Test Helpers — Blocks All User Stories)

**Purpose**: Extend the shared test helpers in `test_documents_draft_router.py` so every story's test can control document state and assert on Celery dispatch. Both edits land in the same file, so this is one task, not two parallel ones.

**⚠️ CRITICAL**: No user story test can be written until this phase is complete.

- [X] T002 In `apps/api/tests/unit/test_documents_draft_router.py`: (a) add an optional `state: DocumentLifecycleState = DocumentLifecycleState.INGESTED` parameter to `_build_doc()` (preserves current default for all existing call sites, importing `DocumentLifecycleState` at module level if not already available there) and pass it through to the `Document(...)` constructor's `state=` field; (b) add an optional `celery=None` parameter to `_patched_router()` that adds `patch("tessera_api.routers.documents.get_celery_app", return_value=celery or MagicMock())` to its `with` block, following the exact pattern already used in `apps/api/tests/unit/test_reindex_router.py:159-160`.

**Checkpoint**: Test helpers ready — US1/US2/US3 tests can now be written.

---

## Phase 3: User Story 1 - Search reflects a document's latest edited content (Priority: P1) 🎯 MVP

**Goal**: Finishing an edit that creates a new version on a published document dispatches the same `tessera.index_document_version` Celery task already used by `publish_document`/`reindex_document`.

**Independent Test**: Finish an edit with real content changes on a published document and confirm `get_celery_app().send_task(...)` is called with the new version's id, the document id, and the space id.

### Tests for User Story 1 (TDD — MUST FAIL before T004)

> **⚠️ Write and confirm FAILING before starting T004**

- [X] T003 [US1] Add `test_finish_with_change_on_published_doc_dispatches_reindex` to `TestFinishDraft` in `apps/api/tests/unit/test_documents_draft_router.py`: build the document with `state=DocumentLifecycleState.PUBLISHED` via `_build_doc(...)`, use differing draft/current content (same setup shape as `test_finish_with_differing_draft_creates_new_version`), pass `celery=MagicMock(send_task=MagicMock())` into `_patched_router(...)`, call `POST /v1/documents/{doc_id}/draft/finish`, and assert the mock's `send_task` was called once with `("tessera.index_document_version",)` as `call_args[0]` and `args=[str(new_version_id), str(doc_id), str(space_id)]` as the keyword/positional args used by the existing `publish_document`/`reindex_document` calls. Run it and confirm it FAILS (no dispatch exists yet).

### Implementation for User Story 1

- [X] T004 [US1] In `finish_document_draft` in `apps/api/tessera_api/routers/documents.py`, after the `write_audit(...)` call (currently ending at line 337) and before the `return` statement (line 339), add:
  ```python
  if doc.state == DocumentLifecycleState.PUBLISHED:
      get_celery_app().send_task(
          "tessera.index_document_version",
          args=[str(created_version.id), str(document_id), str(doc.space_id)],
      )
  ```
  matching the exact dispatch shape already used in `publish_document` (line 392-395) and `reindex_document` (line 440-443) in the same file. `get_celery_app` is already imported at the top of the module. (depends on T003)
- [X] T005 [US1] Run `cd apps/api && .venv/bin/python -m pytest tests/unit/test_documents_draft_router.py -v --no-cov` and confirm T003's new test now passes and no other test in the file regressed. (depends on T004)

**Checkpoint**: MVP complete — finishing an edit on a published document with real changes now triggers reindexing.

---

## Phase 4: User Story 2 - No-op edits don't trigger unnecessary reindexing (Priority: P2)

**Goal**: Finishing an edit session that creates no new version (unchanged content) never dispatches a reindex, even on a published document.

**Independent Test**: Finish an edit with draft content identical to the current version's content on a published document, and confirm no version is created and `send_task` is never called.

### Implementation for User Story 2

- [X] T006 [US2] Extend `test_finish_with_unchanged_content_returns_null_version_and_deletes_draft` in `apps/api/tests/unit/test_documents_draft_router.py`: change its `_build_doc(...)` call to pass `state=DocumentLifecycleState.PUBLISHED` (proving the guard's *content-changed* condition, not just its *published* condition, is what prevents dispatch), pass `celery=MagicMock(send_task=MagicMock())` into `_patched_router(...)`, and add `assert not <celery_mock>.send_task.called` alongside the existing assertions. This should pass immediately given T004's placement inside the "new version created" branch — if it fails, fix the placement in T004, do not add new production code. (depends on T004)

**Checkpoint**: US1 and US2 both verified — no-op finishes are confirmed inert even on published documents.

---

## Phase 5: User Story 3 - Editing an unpublished document doesn't trigger reindexing (Priority: P3)

**Goal**: Finishing an edit that creates a new version on a document that is not currently published never dispatches a reindex.

**Independent Test**: Finish an edit with real content changes on a document whose state is not `PUBLISHED`, and confirm a new version is created but `send_task` is never called.

### Implementation for User Story 3

- [X] T007 [US3] Extend `test_finish_with_differing_draft_creates_new_version` in `apps/api/tests/unit/test_documents_draft_router.py`: it already builds its document via `_build_doc(doc_id, space_id, version_id=current_version_id)`, which defaults to `state=DocumentLifecycleState.INGESTED` after T002 — leave that default in place, pass `celery=MagicMock(send_task=MagicMock())` into `_patched_router(...)`, and add `assert not <celery_mock>.send_task.called` alongside the existing assertions (the test already asserts a new version IS created). This should pass immediately given T004's `doc.state == PUBLISHED` guard — if it fails, fix the guard in T004, do not add new production code. (depends on T004)

**Checkpoint**: All three user stories verified — reindexing on finished edits is now correctly scoped to "published document, real content change."

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Meet Constitution Principle V (Ruff + Black) and confirm no regressions in neighboring test files that also assert on `get_celery_app`/`send_task`.

- [X] T008 [P] Run Ruff on modified files: `cd apps/api && .venv/bin/ruff check tessera_api/routers/documents.py tests/unit/test_documents_draft_router.py`
- [X] T009 [P] Run Black on modified files: `cd apps/api && .venv/bin/black tessera_api/routers/documents.py tests/unit/test_documents_draft_router.py`
- [X] T010 Run the full API unit test suite to confirm no regressions, including the pre-existing publish/reindex dispatch tests: `cd apps/api && .venv/bin/python -m pytest tests/unit/test_documents_draft_router.py tests/unit/test_documents_router.py tests/unit/test_reindex_router.py -v --no-cov`
- [X] T011 Walk through `specs/047-fix-edit-reindex/quickstart.md` Scenarios 1-3 against a local `make dev` stack to confirm end-to-end behavior (search reflects edits, no-op finishes are inert, unpublished-doc finishes are inert).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user story tasks.
- **User Story 1 (Phase 3)**: Depends on Foundational. Contains the only production code change (T004); US2 and US3 both depend on T004.
- **User Story 2 (Phase 4)**: Depends on T004 (US1's implementation) — no independent code change of its own.
- **User Story 3 (Phase 5)**: Depends on T004 (US1's implementation) — no independent code change of its own.
- **Polish (Phase 6)**: Depends on Phases 3-5 being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational. This is the MVP and the only story with a production code change.
- **User Story 2 (P2)**: Depends on US1's implementation (T004) existing — it verifies a guard condition US1 already put in place. Its test can be written any time after T002, but the assertion only passes once T004 lands.
- **User Story 3 (P3)**: Same relationship to US1 as US2 — verifies the other half of T004's guard condition.

### Within Each User Story

- Tests are written before (US1) or alongside/after (US2, US3) the single shared implementation task, per the constitution's TDD rule for the new behavior introduced in T004.
- T006 and T007 touch the same file as each other (but different test methods) — do not run them as truly parallel edits; do them sequentially to avoid merge conflicts, in either order.

---

## Parallel Example: Phase 6 only

```bash
# T008 and T009 touch the same two files but are non-conflicting tooling passes;
# safe to run back-to-back or in parallel processes:
Task: "Run Ruff on tessera_api/routers/documents.py and tests/unit/test_documents_draft_router.py"
Task: "Run Black on tessera_api/routers/documents.py and tests/unit/test_documents_draft_router.py"
```

No other phase has genuinely parallel tasks — this feature is a single-file production change with a single-file test suite, so nearly everything is sequential by nature.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (test helper changes)
3. Complete Phase 3: User Story 1 (T003 failing test → T004 implementation → T005 green)
4. **STOP and VALIDATE**: `finish_document_draft` now dispatches reindexing for published documents with real changes — this is the entire bug fix.

### Incremental Delivery

1. Setup + Foundational → helpers ready.
2. US1 → the fix itself lands and is proven correct → this alone resolves the reported bug.
3. US2 → proves the fix doesn't over-trigger on no-op finishes (regression guard).
4. US3 → proves the fix doesn't over-trigger on unpublished documents (regression guard).
5. Polish → lint/format/full-suite/quickstart pass.

### Notes

- There is no parallel "team strategy" split worth documenting: this is a ~10-line guarded conditional in one existing function, plus three test additions in one existing test file. Treat T001-T011 as a single sequential unit of work for one engineer.
- Commit after each checkpoint (end of Phase 3, Phase 4, Phase 5, Phase 6), not after every individual task.
