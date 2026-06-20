# Tasks: Fix Document Content Display

**Input**: Design documents from `specs/011-fix-doc-content-display/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Tests**: Included — Constitution IV (TDD) is non-negotiable. Tests MUST be written first and confirmed to FAIL before the fix is applied.

**Organization**: Two user stories, one foundational fix. US2 is satisfied by the same code change as US1 — no separate implementation phase required.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

---

## Phase 1: Setup

**Purpose**: Confirm the test file location and lint toolchain are ready before writing any code.

- [x] T001 Verify pytest can discover `apps/api/tests/contract/` by running `cd apps/api && python -m pytest tests/contract/ --collect-only` and confirming no import errors
- [x] T002 [P] Confirm Ruff and Black are available: `cd apps/api && python -m ruff check . --select ALL --statistics 2>/dev/null | head -5` and `python -m black --check . 2>/dev/null | tail -3`

**Checkpoint**: Test infrastructure confirmed — ready to write tests.

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: Understand the exact call site and session scope before modifying anything.

**⚠️ CRITICAL**: Read the source before writing the test or the fix.

- [x] T003 Read `apps/api/tessera_api/routers/documents.py` lines 55–83 and confirm `set_current_version` is NOT called in `create_document`; note that `set_current_version` is imported via `SqlDocumentRepository` which is already instantiated as `doc_repo` within the same `async with get_db() as session:` block

**Checkpoint**: Call site confirmed — test and fix targets are known.

---

## Phase 3: User Story 1 — View Content of a Newly Created Document (Priority: P1) 🎯 MVP

**Goal**: A document created with non-empty content must display that content immediately on the detail page without requiring a publish action.

**Independent Test**: Create a document via POST /v1/documents with non-empty `content_markdown` → GET /v1/documents/{id} must return `current_version` with matching content.

### Tests for User Story 1 ⚠️ Write FIRST — confirm FAIL before T007

- [x] T004 [US1] Create `apps/api/tests/contract/test_documents.py` with a test class `TestCreateDocumentContract` containing one test: mock `SqlDocumentRepository.create`, `SqlDocumentVersionRepository.create`, and `SqlDocumentRepository.set_current_version`; call `create_document` handler directly; assert `set_current_version` was called once with `(created_doc.id, created_version.id)` — this test MUST FAIL before T007
- [x] T005 [US1] Add a second test in `apps/api/tests/contract/test_documents.py`: `test_create_document_response_has_current_version_id` — mock repos as above; assert `response["document"]["current_version_id"]` equals `created_version.id` — this test MUST FAIL before T007
- [x] T006 [US1] Run `cd apps/api && python -m pytest tests/contract/test_documents.py -v` and confirm both T004/T005 tests FAIL (AssertionError: set_current_version not called / current_version_id is None)

### Implementation for User Story 1

- [x] T007 [US1] In `apps/api/tessera_api/routers/documents.py` inside `create_document`, after `created_version = await ver_repo.create(version)`, add `created_doc = await doc_repo.set_current_version(created_doc.id, created_version.id)` — reassign `created_doc` so the response body reflects the updated pointer
- [x] T008 [US1] Run `cd apps/api && python -m pytest tests/contract/test_documents.py -v` and confirm both tests now PASS
- [x] T009 [US1] Run `cd apps/api && python -m pytest tests/ -v --ignore=tests/perf` and confirm no regressions in the full test suite
- [x] T010 [US1] Run `cd apps/api && python -m ruff check tessera_api/routers/documents.py` and `python -m black tessera_api/routers/documents.py --check`; fix any violations (Constitution V)

**Checkpoint**: US1 is complete. `current_version_id` is now set on creation; detail page will show content immediately.

---

## Phase 4: User Story 2 — Version History Shows Initial Version (Priority: P2)

**Goal**: The Version History table on the detail page shows version 1 immediately after document creation.

**Independent Test**: After creating a document, GET /v1/documents/{id}/versions must return a list containing exactly one entry with `version_number: 1`.

> **Note**: No additional implementation is required. Version 1 was already being persisted by `ver_repo.create()` before this fix. The `GET /v1/documents/{id}/versions` endpoint calls `list_by_document` which returns all versions regardless of `current_version_id`. US2 is satisfied by the existing code — confirmed by inspection in T003.

- [x] T011 [US2] Add a third test in `apps/api/tests/contract/test_documents.py`: `test_create_document_creates_version_number_1` — mock repos as above; assert `ver_repo.create` was called with a `DocumentVersion` where `version_number == 1` and `document_id == created_doc.id`
- [x] T012 [US2] Run `cd apps/api && python -m pytest tests/contract/test_documents.py::TestCreateDocumentContract::test_create_document_creates_version_number_1 -v` and confirm it passes (version creation was not broken — this validates the invariant)

**Checkpoint**: All user stories verified. Both US1 and US2 confirmed working.

---

## Phase 5: Polish & Validation

**Purpose**: End-to-end smoke test and documentation confirmation.

- [ ] T013 [P] Follow `specs/011-fix-doc-content-display/quickstart.md` Scenario 1 against a running API instance: POST a document with content → GET the document → confirm `current_version.content_markdown` matches
- [ ] T014 [P] Follow quickstart.md Scenario 4 (frontend smoke test): create a document via the UI, navigate to its detail page, confirm content is visible without clicking Publish
- [ ] T015 [P] Verify the publish flow is unaffected per quickstart.md final section: publish an existing ingested document and confirm state transitions correctly

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 ✅
- **US1 (Phase 3)**: Depends on Phase 2 ✅ — write tests first (T004–T006), then fix (T007–T010)
- **US2 (Phase 4)**: Depends on Phase 3 fix being in place (T007) — T011/T012 validate the invariant
- **Polish (Phase 5)**: Depends on Phases 3 and 4 complete

### Within Phase 3 (TDD order — enforced)

```
T003 (read source) → T004 (write test) → T005 (write test) → T006 (confirm FAIL)
  → T007 (apply fix) → T008 (confirm PASS) → T009 (regression suite) → T010 (lint)
```

### Parallel Opportunities

- T001 and T002 can run in parallel (Phase 1)
- T013, T014, T015 can run in parallel (Phase 5, different validation channels)

---

## Parallel Example: Phase 1

```bash
# Run these simultaneously — independent checks:
cd apps/api && python -m pytest tests/contract/ --collect-only   # T001
cd apps/api && python -m ruff check . --select ALL --statistics  # T002
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. Phase 1: Setup (T001–T002)
2. Phase 2: Foundational (T003)
3. Phase 3: TDD fix cycle (T004–T010)
4. **STOP and VALIDATE**: `GET /v1/documents/{id}` returns content immediately post-creation
5. Ship — US2 is automatically satisfied by the same fix

### Full Delivery (both stories + polish)

Continue with Phase 4 (T011–T012) then Phase 5 (T013–T015).

---

## Notes

- This is a single-line backend fix (`create_document` in `documents.py`) gated by a TDD test cycle
- No schema changes, no frontend changes, no new dependencies
- The publish flow is read-only for this fix — its `set_current_version` call remains unchanged
- `set_current_version` returns the updated `Document`; reassign `created_doc` so the response body is consistent (T007 instruction)
- Existing documents created before this fix are out of scope — they will continue to show "No content available" unless manually republished
