---

description: "Task list for Space-Filtered Document Listing"
---

# Tasks: Space-Filtered Document Listing

**Input**: Design documents from `/specs/020-space-filtered-docs/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/documents-api.md ✅

**Tests**: Included — TDD is NON-NEGOTIABLE per Constitution §IV. Tests must be written first and confirmed to fail before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to ([US1], [US2], [US3])
- Exact file paths are included in every task description

---

## Phase 1: Setup

**Purpose**: Establish a green baseline before making any changes.

- [X] T001 Run existing test suites to confirm a passing baseline: `cd packages/core && uv run pytest tests/ -v` and `cd apps/api && uv run pytest tests/ -v`

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: Add the `list_by_space_ids()` port method — this abstract method must exist before the adapter implementation and port tests can be written.

**⚠️ CRITICAL**: No user-story work can begin until this phase is complete.

- [X] T002 Add `list_by_space_ids(self, space_ids: list[UUID], state: DocumentLifecycleState | None = None) -> list[Document]` as an `@abstractmethod` to `DocumentRepository` in `packages/core/tessera_core/ports/repositories.py`

**Checkpoint**: Port contract updated — user-story phases can now begin.

---

## Phase 3: User Story 1 — Instant Document View on Page Open (Priority: P1) 🎯 MVP

**Goal**: When a user navigates to `/documents`, documents from all accessible spaces load automatically — no space selection required. Backend: fix two stubs (`list_for_user()` and the no-`space_id` router branch) + implement `list_by_space_ids()`. Frontend: remove the `if (!selectedSpaceId) return` guard and unify fetching into a single helper.

**Independent Test**: Navigate to `/documents` as a logged-in user with access to at least one space; documents appear without manual space selection.

### Tests for User Story 1 ⚠️ Write these FIRST — confirm they FAIL before implementing

- [X] T003 [P] [US1] Write failing port contract test for `list_by_space_ids()` (empty list returns `[]` without a DB call; populated list returns matching documents) in `packages/core/tests/test_ports.py`
- [X] T004 [P] [US1] Write failing contract test for `GET /v1/documents` with no `space_id`: authenticated user receives their accessible documents (non-empty for a user with space access) in `apps/api/tests/contract/test_documents.py`
- [X] T005 [P] [US1] Write failing integration test for the full accessible-docs flow: user with groups → `list_for_user()` returns correct spaces → `list_by_space_ids()` returns documents from those spaces in `apps/api/tests/integration/test_accessible_docs.py`

### Implementation for User Story 1

- [X] T006 [P] [US1] Implement `SqlDocumentRepository.list_by_space_ids()` using `DocumentModel.space_id.in_(space_ids)` (add `if not space_ids: return []` early-return guard) in `apps/api/tessera_api/adapters/repo.py`
- [X] T007 [P] [US1] Fix `SqlSpaceRepository.list_for_user()`: replace the `list_all()` stub with a single SQL JOIN (`spaces JOIN role_permissions ON rp.space_id = s.id WHERE rp.idp_group = ANY(:user_groups)`); admin path calls `list_all()` in `apps/api/tessera_api/adapters/repo.py`
- [X] T008 [US1] Fix `GET /v1/documents` no-`space_id` branch: resolve `user.groups` via `SqlUserRepository.get_by_subject(user_info["sub"])`, call `space_repo.list_for_user(user)` then `doc_repo.list_by_space_ids(space_ids, state)` in `apps/api/tessera_api/routers/documents.py`
- [X] T009 [US1] Refactor `DocumentsPage`: extract `fetchDocuments(spaceId: string | null)` helper, remove `if (!selectedSpaceId) return` guard, call `fetchDocuments(null)` on mount via `useEffect([], [])` in `apps/web/app/documents/page.tsx`

**Checkpoint**: Run `uv run pytest packages/core/tests/ apps/api/tests/contract/test_documents.py apps/api/tests/integration/test_accessible_docs.py -v` — all US1 tests must pass. Navigate to `/documents` in the browser and confirm auto-load.

---

## Phase 4: User Story 2 — Space-Scoped Filtering Remains Available (Priority: P2)

**Goal**: The space selector still narrows the list to a chosen space; clearing it returns to the cross-space view. Backend is unchanged (existing `?space_id` path still works). Frontend must wire the clear action to call `fetchDocuments(null)` and provide context-aware empty-state messages.

**Independent Test**: Select a space → only that space's documents appear. Clear the selector → all accessible documents return.

### Tests for User Story 2 ⚠️ Write these FIRST — confirm they FAIL before implementing

- [X] T010 [P] [US2] Write failing frontend test: selecting a space calls `fetchDocuments(spaceId)` and the list updates to show only that space's documents in `apps/web/app/documents/page.test.tsx`
- [X] T011 [P] [US2] Write failing frontend test: clearing the space selector calls `fetchDocuments(null)` and restores the cross-space document list in `apps/web/app/documents/page.test.tsx`

### Implementation for User Story 2

- [X] T012 [US2] Wire space-selector clear handler: ensure `setSelectedSpaceId(null)` triggers `useEffect([selectedSpaceId])` which calls `fetchDocuments(null)` in `apps/web/app/documents/page.tsx`
- [X] T013 [US2] Update empty-state messages: show "No documents found across your accessible spaces." when `selectedSpaceId` is `null` and "No documents in this space." when a space is selected but has no documents in `apps/web/app/documents/page.tsx`

**Checkpoint**: Run frontend tests (`cd apps/web && npm test`). Manually verify: select a space → filtered; clear selector → all accessible docs restored.

---

## Phase 5: User Story 3 — Access Boundary Enforcement (Priority: P3)

**Goal**: Documents from spaces the user has no access to must never appear, regardless of system state. Backend access logic from US1 already enforces this via the SQL JOIN, but explicit tests and the empty-groups edge case must be covered.

**Independent Test**: Log in as a user with access only to Space A; confirm Space B documents are absent from `GET /v1/documents`.

### Tests for User Story 3 ⚠️ Write these FIRST — confirm they FAIL before implementing

- [X] T014 [P] [US3] Write failing integration test: user with access only to Space A receives no documents from Space B in `apps/api/tests/integration/test_access_boundary.py`
- [X] T015 [P] [US3] Write failing integration test: admin user (`is_admin=True`) receives documents from all spaces in `apps/api/tests/integration/test_access_boundary.py`

### Implementation for User Story 3

- [X] T016 [US3] Add empty-groups guard in `SqlSpaceRepository.list_for_user()`: when `user.groups` is an empty list (and not admin), return `[]` immediately without executing a DB query in `apps/api/tessera_api/adapters/repo.py`

**Checkpoint**: Run `uv run pytest apps/api/tests/integration/test_access_boundary.py -v` — both boundary tests pass. Verify SC-002: zero unauthorized document exposure.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates and end-to-end validation across all user stories.

- [X] T017 [P] Run Ruff and Black over all modified Python files (`packages/core/tessera_core/ports/repositories.py`, `apps/api/tessera_api/adapters/repo.py`, `apps/api/tessera_api/routers/documents.py`) and fix any violations before committing
- [X] T018 [P] Run the full test suite (`uv run pytest packages/core/tests/ apps/api/tests/ -v`) and confirm all new and existing tests pass with no regressions
- [X] T019 Execute all five quickstart.md manual validation scenarios (auto-load, space-filter, access boundary, admin view, no-access empty state) against the running stack

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories.
- **US1 (Phase 3)**: Depends on Foundational — blocks US2 frontend work (needs the `fetchDocuments` helper).
- **US2 (Phase 4)**: Depends on US1 frontend task T009 (`fetchDocuments` helper must exist).
- **US3 (Phase 5)**: Depends on US1 backend (T006, T007 must be complete for the access boundary to be implemented).
- **Polish (Phase 6)**: Depends on all user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational (Phase 2). No dependencies on US2 or US3.
- **US2 (P2)**: Backend is already correct after US1. Frontend depends on T009. Can overlap with US3.
- **US3 (P3)**: Depends on T006 + T007 (US1 backend) — boundary logic lives there.

### Within Each User Story

1. **Write tests first → confirm they FAIL**
2. Implement: port method → adapter → router → frontend
3. **Confirm tests now PASS**
4. Commit (Ruff + Black must be clean — V. Quality Gates)

### Parallel Opportunities

- T003, T004, T005 (US1 tests) can be written in parallel — different files.
- T006, T007 (adapter implementations) touch different classes in the same file; write them sequentially to avoid merge conflicts or split into two commits.
- T010, T011 (US2 frontend tests) can be written in parallel — same test file but disjoint test functions.
- T014, T015 (US3 integration tests) can be written in parallel — same file, disjoint test functions.
- T017, T018 (Polish) can run in parallel — Ruff/Black and pytest are independent.

---

## Parallel Example: User Story 1

```bash
# Write all US1 failing tests together (before any implementation):
# T003: packages/core/tests/test_ports.py
# T004: apps/api/tests/contract/test_documents.py
# T005: apps/api/tests/integration/test_accessible_docs.py

# Then implement adapter tasks (same file — do sequentially):
# T006: SqlDocumentRepository.list_by_space_ids()
# T007: SqlSpaceRepository.list_for_user()

# Then fix router and frontend (different files — can be parallel):
# T008: apps/api/tessera_api/routers/documents.py
# T009: apps/web/app/documents/page.tsx
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (baseline green)
2. Complete Phase 2: Foundational (port method)
3. Write US1 tests (T003–T005) and confirm they fail
4. Implement US1 (T006–T009)
5. **STOP and VALIDATE**: All US1 tests pass; browser confirms auto-load
6. Deploy / demo if ready

### Incremental Delivery

1. Setup + Foundational → port contract ready
2. US1 → auto-load works → **demo-able MVP**
3. US2 → space filter + clear → **full selector behavior**
4. US3 → boundary tests → **security sign-off**
5. Polish → Quality Gates pass → **ready for review**

---

## Notes

- [P] tasks = different files or disjoint code paths; no dependency on an incomplete sibling task
- [Story] label maps task to a user story for traceability
- Tests must be written and confirmed **failing** before implementation (Constitution §IV)
- Ruff + Black must pass before any commit (Constitution §V)
- `list_by_space_ids([])` → `[]` early-return is a hard requirement (data-model.md validation rule)
- Admin bypass (`is_admin=True` → `list_all()`) must be implemented in T007, not deferred
- No new DB migrations required — all schema is already in place
