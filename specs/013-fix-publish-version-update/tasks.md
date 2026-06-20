# Tasks: Fix Publish — Record Approval on Existing Version

**Input**: Design documents from `specs/013-fix-publish-version-update/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**TDD**: Constitution Principle IV is non-negotiable — contract test MUST be written and confirmed FAILING before any implementation task is started.

**Organization**: Tasks grouped by phase and user story. US1 and US2 are coupled (same endpoint) but verified by separate acceptance scenarios.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Verify Environment)

**Purpose**: Confirm the test environment is functional. No new files or dependencies required for this fix.

- [x] T001 Confirm contract test suite runs and existing tests pass: `cd apps/api && .venv/bin/python -m pytest tests/contract/test_documents.py -v --no-cov`

---

## Phase 2: Foundational (Port Method — Blocks All User Stories)

**Purpose**: Add the `update_approval` abstract method to the domain port. Both US1 and US2 require this contract to exist before the SQL adapter or router can be written.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Add abstract method `update_approval(version_id, approver_id, approved_at)` to `DocumentVersionRepository` in `packages/core/tessera_core/ports/repositories.py` (add `datetime` import if not present)

**Checkpoint**: Port contract defined — SQL adapter and router changes can now be written.

---

## Phase 3: User Story 1 — Publish Succeeds Without Server Error (Priority: P1) 🎯 MVP

**Goal**: Calling `POST /v1/documents/{id}/publish` on a document with content returns 200 OK and transitions the document to "published" state. Currently returns 500 unconditionally.

**Independent Test**: Create a document, add content, publish it — document state is "published," no 500 error.

### Tests for User Story 1 (TDD — MUST FAIL before T004)

> **⚠️ Write and confirm FAILING before starting T004**

- [x] T003 [US1] Add contract test `test_publish_document_records_approval_without_creating_version` to `apps/api/tests/contract/test_documents.py` — mock doc with owner + one version; assert `ver_repo.update_approval` IS called and `ver_repo.create` is NOT called; confirm test FAILS

### Implementation for User Story 1

- [x] T004 [US1] Implement `SqlDocumentVersionRepository.update_approval(version_id, approver_id, approved_at)` in `apps/api/tessera_api/adapters/repo.py` — issue SQLAlchemy UPDATE on `DocumentVersionModel` then SELECT and return updated domain entity (depends on T002)
- [x] T005 [US1] Replace `ver_repo.create(approved_version)` with `await ver_repo.update_approval(latest.id, publisher_id, now)` in `publish_document` in `apps/api/tessera_api/routers/documents.py` — remove the `approved_version = latest.model_copy(...)` line entirely (depends on T004)
- [x] T006 [US1] Run contract tests and confirm T003's test now passes: `cd apps/api && .venv/bin/python -m pytest tests/contract/test_documents.py -v --no-cov`

**Checkpoint**: T003–T006 complete — `POST /v1/documents/{id}/publish` no longer returns 500.

---

## Phase 4: User Story 2 — Approval Metadata Preserved After Publish (Priority: P2)

**Goal**: After a successful publish, `approver_user_id` and `approved_at` are non-null on the version and accurately reflect the publishing user and timestamp.

**Independent Test**: After publish, retrieve the version — confirm `approver_user_id == publisher_id` and `approved_at` is a valid non-null timestamp.

> **Note**: US2 is validated by the same `update_approval` implementation used in US1. The existing contract test `test_publish_document_preserves_existing_owner` already asserts `approved_version_arg.approver_user_id == publisher_id`. Verify that the full suite, including this test, passes.

### Implementation for User Story 2

- [x] T007 [US2] Verify `test_publish_document_preserves_existing_owner` and `test_publish_document_auto_assigns_owner_when_none` both pass with the new `update_approval` implementation (no new code if T004–T005 are correct; investigate and fix any failures)
- [x] T008 [P] [US2] Verify the `update_approval` SQL adapter correctly passes `approver_user_id` and `approved_at` back in the returned `DocumentVersion` domain entity — trace through `_version_from_model` to confirm field mapping in `apps/api/tessera_api/adapters/repo.py`

**Checkpoint**: All 8 contract tests pass (7 existing + 1 new from T003).

---

## Phase 5: Polish & Quality Gates

**Purpose**: Ensure the fix meets Constitution Principle V (Ruff + Black) and audit requirements.

- [x] T009 [P] Run Ruff on all modified files and fix any lint errors: `cd apps/api && .venv/bin/ruff check tessera_api/adapters/repo.py tessera_api/routers/documents.py tests/contract/test_documents.py` and `cd packages/core && .venv/bin/ruff check tessera_core/ports/repositories.py`
- [x] T010 [P] Run Black on all modified files: `cd apps/api && .venv/bin/black tessera_api/adapters/repo.py tessera_api/routers/documents.py tests/contract/test_documents.py` and `cd packages/core && .venv/bin/black tessera_core/ports/repositories.py`
- [x] T011 Run full contract + domain test suites to confirm no regressions: `cd apps/api && .venv/bin/python -m pytest tests/contract/ -v --no-cov` and `cd packages/core && .venv/bin/python -m pytest -v --no-cov`
- [x] T012 Validate audit log path: confirm the existing `write_audit` call in `publish_document` is still reachable and not bypassed by the router change (read `apps/api/tessera_api/routers/documents.py` post-implementation)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user story work
- **US1 (Phase 3)**: Depends on Phase 2 (port method must exist)
- **US2 (Phase 4)**: Depends on Phase 3 being complete (reuses T004 implementation)
- **Polish (Phase 5)**: Depends on Phase 4 completion

### Within Phase 3

- T003 (test) → must FAIL before T004 begins (TDD gate)
- T004 (SQL adapter) → must complete before T005 (router)
- T005 (router) → must complete before T006 (verify)

### Parallel Opportunities

- T009 and T010 (lint/format) can run in parallel
- T007 and T008 (US2 verification) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Step 1: Write and run failing test
Task T003: "Write test_publish_document_records_approval_without_creating_version"
→ Confirm: pytest exits RED

# Step 2: Implement (sequential)
Task T004: "Implement SqlDocumentVersionRepository.update_approval"
Task T005: "Update publish_document router"

# Step 3: Verify
Task T006: "Run contract tests — all pass"
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. T001 — confirm env
2. T002 — add port method
3. T003 — write failing test
4. T004–T005 — implement adapter + router
5. T006 — verify green
6. **STOP and VALIDATE**: publish endpoint works end-to-end

### Full Delivery

1. MVP above (US1 done)
2. T007–T008 — verify approval metadata (US2 done)
3. T009–T012 — quality gates (Polish done)

---

## Notes

- [P] tasks = different files, no inter-task dependencies
- TDD is MANDATORY (Constitution Principle IV) — T003 MUST fail before T004 starts
- No migration needed — only existing nullable columns updated
- Only 4 files change: `repositories.py`, `repo.py`, `documents.py`, `test_documents.py`
- Ruff + Black must pass before committing (Constitution Principle V)
