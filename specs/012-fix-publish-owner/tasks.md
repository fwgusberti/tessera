---

description: "Task list for Fix Document Publish — Auto-Assign Owner"
---

# Tasks: Fix Document Publish — Auto-Assign Owner

**Input**: Design documents from `specs/012-fix-publish-owner/`

**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/documents-api.md ✅

**Tests**: Included — Constitution Principle IV (TDD) mandates failing tests before implementation.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (US1, US2)

## Path Conventions

Monorepo layout:
- API router: `apps/api/tessera_api/routers/documents.py`
- Auth helper: `apps/api/tessera_api/auth/oidc.py`
- Contract tests: `apps/api/tests/contract/test_documents.py`
- Domain service: `packages/core/tessera_core/services/lifecycle.py` (unchanged)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new infrastructure required — existing monorepo with all dependencies in place.

- [x] T001 Confirm test runner is working by running `cd apps/api && python -m pytest tests/contract/test_documents.py -v` and noting current pass/fail state

---

## Phase 2: Foundational (Failing Tests — TDD Gate)

**Purpose**: Write the three new failing tests before any implementation. Constitution Principle IV requires tests to exist and fail before code is written.

**⚠️ CRITICAL**: All three tests MUST fail before proceeding to Phase 3.

- [x] T002 [US1] Write failing contract test `test_create_document_sets_owner_from_user_info` in `apps/api/tests/contract/test_documents.py` — asserts that `doc_repo.create()` is called with a `Document` whose `owner_user_id` equals the user ID from `require_user`
- [x] T003 [US1] Write failing contract test `test_publish_document_auto_assigns_owner_when_none` in `apps/api/tests/contract/test_documents.py` — mocks a document with `owner_user_id=None`, asserts `doc_repo.set_owner()` is called and publish succeeds with state `"published"`
- [x] T004 [US1] Write failing contract test `test_publish_document_preserves_existing_owner` in `apps/api/tests/contract/test_documents.py` — mocks a document with `owner_user_id` already set, asserts `doc_repo.set_owner()` is NOT called and publish succeeds
- [x] T005 Confirm all three new tests fail: run `cd apps/api && python -m pytest tests/contract/test_documents.py -v -k "owner"` and verify 3 failures before continuing

**Checkpoint**: 3 failing tests confirmed — implementation can now begin

---

## Phase 3: User Story 1 — Publish Without Manual Owner Assignment (Priority: P1) 🎯 MVP

**Goal**: Documents created via `POST /documents` automatically have `owner_user_id` set, and `POST /documents/{id}/publish` succeeds without requiring manual owner assignment.

**Independent Test**: Create a document and immediately publish it — both calls succeed, `document.owner_user_id` is non-null, and `document.state` is `"published"`.

### Implementation for User Story 1

- [x] T006 [P] [US1] Fix `require_user` JWT branch in `apps/api/tessera_api/auth/oidc.py`: add `"id": claims["sub"]` to the returned dict so `user_info["id"]` is consistent between session and JWT auth paths
- [x] T007 [P] [US1] Fix `create_document` in `apps/api/tessera_api/routers/documents.py`: extract `owner_id = uuid.UUID(user_info["id"])` after `require_user` and pass `owner_user_id=owner_id` to the `Document(...)` constructor
- [x] T008 [US1] Fix `publish_document` in `apps/api/tessera_api/routers/documents.py`: replace the `raise HTTPException(status_code=400, detail="Document has no owner…")` block with auto-assignment — call `assign_owner(doc, publisher_id)` from `tessera_core.services.lifecycle` and `await doc_repo.set_owner(document_id, publisher_id)` when `doc.owner_user_id is None`, then continue to `lifecycle_publish` (import `uuid` at top of file if not already present)
- [x] T009 [US1] Run `cd apps/api && python -m pytest tests/contract/test_documents.py -v` and confirm all tests (including the 3 new ones from Phase 2) pass

**Checkpoint**: US1 fully functional — create → publish works end-to-end with no manual owner step

---

## Phase 4: User Story 2 — Informative Error Feedback (Priority: P2)

**Goal**: When publishing fails for reasons other than missing owner (e.g., no content versions), the error message remains clear and actionable.

**Independent Test**: Attempt to publish a document with no versions — API returns a 400 with `"No versions to publish"` (existing behavior, verified not broken by Phase 3 changes).

### Implementation for User Story 2

- [x] T010 [P] [US2] Write contract test `test_publish_document_fails_with_clear_message_when_no_versions` in `apps/api/tests/contract/test_documents.py` — mocks a document with `owner_user_id` set and an empty versions list, asserts 400 response with detail containing `"No versions"`
- [x] T011 [US2] Run `cd apps/api && python -m pytest tests/contract/test_documents.py -v` and confirm T010 test passes (this verifies the existing "no versions" guard survives the Phase 3 changes)

**Checkpoint**: All error paths verified — US1 and US2 both independently functional

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Lint, format, and full domain test suite verification.

- [x] T012 [P] Run domain lifecycle tests to confirm no regressions: `cd packages/core && python -m pytest tests/ -v`
- [x] T013 [P] Run Ruff linter on modified files: `ruff check apps/api/tessera_api/auth/oidc.py apps/api/tessera_api/routers/documents.py apps/api/tests/contract/test_documents.py`
- [x] T014 [P] Run Black formatter check: `black --check apps/api/tessera_api/auth/oidc.py apps/api/tessera_api/routers/documents.py apps/api/tests/contract/test_documents.py`
- [x] T015 Apply any formatter fixes flagged by T014: `black apps/api/tessera_api/auth/oidc.py apps/api/tessera_api/routers/documents.py apps/api/tests/contract/test_documents.py`
- [x] T016 Run end-to-end validation from `specs/012-fix-publish-owner/quickstart.md` Scenario 1 (create + publish) and confirm success

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — run first
- **Phase 2 (Failing Tests)**: Depends on Phase 1 — BLOCKS Phase 3
- **Phase 3 (US1)**: Depends on Phase 2 completion
- **Phase 4 (US2)**: Depends on Phase 3 completion (T010 uses T008's publish fix)
- **Phase 5 (Polish)**: Depends on Phase 4

### User Story Dependencies

- **US1 (P1)**: Independent — no dependency on US2
- **US2 (P2)**: Depends on US1 (the publish fix must be in place to test non-owner failure paths cleanly)

### Within Phase 3 (US1)

- T006 and T007 are independent files — run in parallel
- T008 depends on T006 (needs `user_info["id"]` to be reliable) and T007 (shares the same file)
- T009 depends on T006 + T007 + T008

### Parallel Opportunities

- T006 and T007 can be executed in parallel (different files, no code dependency)
- T012, T013, T014 in Phase 5 can all run in parallel

---

## Parallel Example: Phase 3 (US1)

```bash
# These two tasks touch different files — run in parallel:
Task T006: Fix require_user in apps/api/tessera_api/auth/oidc.py
Task T007: Fix create_document in apps/api/tessera_api/routers/documents.py

# T008 depends on T006 output — run after T006 completes:
Task T008: Fix publish_document in apps/api/tessera_api/routers/documents.py

# Verify:
Task T009: Run full contract test suite
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup check)
2. Complete Phase 2 (3 failing tests confirmed)
3. Complete Phase 3 (US1 — 3 implementation changes)
4. **STOP and VALIDATE**: All tests pass, create → publish works
5. Deploy / demo

### Incremental Delivery

1. Phase 1 + 2 → Failing tests in place (TDD gate set)
2. Phase 3 → US1 fix → Tests pass → MVP ready
3. Phase 4 → US2 verified → All error paths clean
4. Phase 5 → Quality gates pass → Ready to merge

---

## Notes

- T006 and T007 modify different files — safe to run in parallel
- T008 modifies the same file as T007 (`documents.py`) — run sequentially after T007
- Confirm each new test FAILS before the corresponding implementation
- The `assign_owner` domain function and `doc_repo.set_owner` SQL method already exist — no new domain or repo code is needed
- `uuid` import may already be present in `documents.py`; check before adding
