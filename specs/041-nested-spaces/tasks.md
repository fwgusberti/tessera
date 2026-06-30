---

description: "Task list for Nested Spaces (041) implementation"
---

# Tasks: Nested Spaces

**Input**: Design documents from `/specs/041-nested-spaces/`

**Branch**: `041-nested-spaces` | **Date**: 2026-06-30

**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/spaces.md ✅ quickstart.md ✅

**TDD Note** (Constitution IV — NON-NEGOTIABLE): Domain service tests MUST be written and confirmed failing before implementation. API integration tests MUST be written before router handlers are updated. Mark each test task done only after confirming the test fails for the right reason.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1–US4)

---

## Phase 1: Setup

**Purpose**: Database foundation — required before any code can be run or tested against a live schema.

- [X] T001 Create Alembic migration `0012_space_parent` adding `parent_space_id UUID REFERENCES spaces(id) ON DELETE SET NULL` column and `ix_spaces_parent_space_id` index in `db/migrations/versions/0012_space_parent.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain model, value objects, repository port, and SQLAlchemy model changes — everything that US1–US4 build on top of.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Add `parent_space_id: uuid.UUID | None = None` field to the `Space` dataclass/Pydantic model in `packages/core/tessera_core/domain/space.py`
- [X] T003 [P] Create `SpaceAccess` value object (`space: Space`, `effective_role: SpaceRole`, `is_direct: bool`) in `packages/core/tessera_core/domain/space_access.py`
- [X] T004 Add four abstract methods to `SpaceRepository` port — `get_ancestor_chain(space_id) -> list[Space]`, `set_parent(space_id, parent_space_id) -> Space`, `remove_parent(space_id) -> Space`, `list_accessible_by_user(user_id, company_id) -> list[SpaceAccess]` — in `packages/core/tessera_core/ports/repositories/space.py` (depends on T002, T003)
- [X] T005 Add `parent_space_id` FK `mapped_column` and `parent` / `children` self-referential ORM relationships to `SpaceModel` in `apps/api/tessera_api/adapters/models/space.py` (depends on T002)

**Checkpoint**: Domain model, port, and ORM model are consistent — user story work can now begin.

---

## Phase 3: User Story 1 — Browse Inherited Child Spaces (Priority: P1) 🎯 MVP

**Goal**: A user who holds direct membership in any ancestor space automatically gains effective access to every descendant space, inheriting the same role.

**Independent Test**: A user with admin membership in "Engineering" can `GET /v1/spaces` and see both "Engineering" and its child "Frontend" (effective_role=admin, is_direct=false for Frontend), without any explicit Frontend membership.

### Tests for User Story 1 (TDD — write first, confirm failing)

- [X] T006 [P] [US1] Write failing unit tests for downward access inheritance (single-level, multi-level chain, no-access denial) in `packages/core/tests/test_space_hierarchy.py` using mock `SpaceRepository`
- [X] T007 [P] [US1] Write failing API integration tests for `GET /v1/spaces` returning only user-accessible spaces with `effective_role` and `is_direct` fields in `apps/api/tests/test_space_hierarchy.py`

### Implementation for User Story 1

- [X] T008 [US1] Implement `SpaceHierarchyService` class with constructor injection of `SpaceRepository` and `SpaceMembershipRepository`; implement no-op or pass-through methods as stubs to make T006 compile in `packages/core/tessera_core/services/space_hierarchy.py` (depends on T004, T006)
- [X] T009 [US1] Implement `list_accessible_by_user` in the SQLAlchemy space repository using the recursive CTE from research.md (base: direct memberships; recursive leg: children; GROUP BY with role-precedence MAX) in `apps/api/tessera_api/adapters/repositories/space.py` (depends on T004, T005)
- [X] T010 [US1] Update `GET /v1/spaces` router handler to call `list_accessible_by_user(user_id, company_id)` and return the new response shape (`parent_space_id`, `effective_role`, `is_direct` per space) in `apps/api/tessera_api/routers/spaces.py` (depends on T007, T009)
- [X] T011 [US1] Update `GET /v1/spaces/{space_id}` router handler to use effective membership check (404 if user has no direct or inherited access) in `apps/api/tessera_api/routers/spaces.py` (depends on T010)

**Checkpoint**: User Story 1 is independently functional. Run: `cd apps/api && uv run pytest tests/test_space_hierarchy.py -v -k "inheritance"`.

---

## Phase 4: User Story 2 — One-Way Permission Isolation (Priority: P1)

**Goal**: Child-space membership MUST NOT propagate upward. A user in "Frontend" cannot access "Engineering" (parent) or "Backend" (sibling).

**Independent Test**: A user with direct membership in "Frontend" only receives a 404 on `GET /v1/spaces/{engineering_id}` and sees only "Frontend" in `GET /v1/spaces`.

### Tests for User Story 2 (TDD — write first, confirm failing)

- [X] T012 [P] [US2] Write failing unit tests for upward-isolation invariant (child→parent denial, sibling denial, space list contains only accessible spaces) in `packages/core/tests/test_space_hierarchy.py` (depends on T008)
- [X] T013 [P] [US2] Write failing cross-tenant isolation integration tests (`test_set_parent_rejects_cross_company_parent`, `test_list_accessible_by_user_never_leaks_across_companies`, `test_inherited_access_stays_within_company`) in `apps/api/tests/test_space_hierarchy_isolation.py` (depends on T009)

### Implementation for User Story 2

- [X] T014 [US2] Run T012 unit tests against existing `SpaceHierarchyService`; if any pass for the wrong reason, tighten `list_accessible_by_user` effective-access derivation to enforce one-directional propagation in `packages/core/tessera_core/services/space_hierarchy.py` (depends on T008, T012)
- [X] T015 [US2] Update existing `test_space_visibility.py` integration tests that currently expect all company spaces on `GET /v1/spaces` — adjust fixtures and assertions to match the new user-filtered behaviour in `apps/api/tests/test_space_visibility.py` (depends on T010, T013)

**Checkpoint**: US1 and US2 both pass. Run: `cd apps/api && uv run pytest tests/test_space_hierarchy.py tests/test_space_hierarchy_isolation.py -v`.

---

## Phase 5: User Story 3 — Organize Spaces into a Hierarchy (Priority: P2)

**Goal**: A space admin can PATCH a parent onto a space (with cycle/depth/cross-company/self-parent guards) and DELETE the parent to promote a space to root. Audit records are emitted on each mutation.

**Independent Test**: An admin calls `PATCH /v1/spaces/{frontend_id}/parent` with `{ "parent_space_id": engineering_id }` and the response includes the updated space with `parent_space_id` set; a subsequent cycle attempt returns 400 with `invalid_parent`.

### Tests for User Story 3 (TDD — write first, confirm failing)

- [X] T016 [P] [US3] Write failing unit tests for `set_parent` validations: self-parent (`ValueError("self_parent")`), cycle (`ValueError("cycle")`), depth-limit (`ValueError("depth_limit")`), cross-company (`ValueError("cross_company")`), permission checks (`PermissionError`) in `packages/core/tests/test_space_hierarchy.py` (depends on T008)
- [X] T017 [P] [US3] Write failing API integration tests for `PATCH /v1/spaces/{id}/parent` (success, cycle rejection, self-parent rejection, 403 missing admin) and `DELETE /v1/spaces/{id}/parent` (success, 403) in `apps/api/tests/test_space_hierarchy.py` (depends on T010)

### Implementation for User Story 3

- [X] T018 [US3] Implement `SpaceHierarchyService.set_parent(actor, child_id, parent_id, company_id)`: verify actor admin in child AND parent, reject self-parent, call `repo.get_ancestor_chain` to detect cycles and check depth ≤ 10, call `repo.set_parent`, emit `AuditRecord` in `packages/core/tessera_core/services/space_hierarchy.py` (depends on T004, T016)
- [X] T019 [US3] Implement `SpaceHierarchyService.remove_parent(actor, child_id, company_id)`: verify actor admin in child, call `repo.remove_parent`, emit `AuditRecord` in `packages/core/tessera_core/services/space_hierarchy.py` (depends on T018)
- [X] T020 [US3] Implement `get_ancestor_chain` (recursive CTE walking `parent_space_id` upward, scoped by `company_id`), `set_parent` (UPDATE with return), and `remove_parent` (SET NULL with return) adapter methods in `apps/api/tessera_api/adapters/repositories/space.py` (depends on T004, T005, T009)
- [X] T021 [US3] Add `PATCH /v1/spaces/{space_id}/parent` router handler: validate request body (`parent_space_id: UUID`), call `SpaceHierarchyService.set_parent`, map `ValueError` → 400 `invalid_parent`, `PermissionError` → 403 in `apps/api/tessera_api/routers/spaces.py` (depends on T017, T018, T020)
- [X] T022 [US3] Add `DELETE /v1/spaces/{space_id}/parent` and `GET /v1/spaces/{space_id}/ancestors` router handlers; ancestors endpoint calls `repo.get_ancestor_chain` and returns `[{id, name, slug}]` ordered from immediate parent to root in `apps/api/tessera_api/routers/spaces.py` (depends on T021, T019, T020)

**Checkpoint**: US3 is independently functional. Run: `cd packages/core && uv run pytest tests/test_space_hierarchy.py -v` and `cd apps/api && uv run pytest tests/test_space_hierarchy.py -v -k "parent"`.

---

## Phase 6: User Story 4 — Navigate the Space Hierarchy (Priority: P3)

**Goal**: The web UI renders accessible spaces as a nested tree; orphaned child spaces (parent not in user's accessible set) display a breadcrumb; admins can assign/change/remove a parent through a modal.

**Independent Test**: A user with access to "Engineering" and its children "Frontend" and "Backend" sees a nested list; a user with access to "Frontend" only sees "Frontend" at root level with an "Engineering >" breadcrumb.

### Implementation for User Story 4

- [X] T023 [P] [US4] Add `parent_space_id: string | null` to `Space` interface and add `SpaceAccess` interface (`space: Space`, `effective_role: SpaceRole`, `is_direct: boolean`) in `apps/web/lib/types.ts`
- [X] T024 [P] [US4] Create `SpaceHierarchyView` component: accepts flat `SpaceAccess[]`, builds id-map, places items whose parent is in the accessible set as nested children, renders orphan roots at top level in `apps/web/components/spaces/SpaceHierarchyView.tsx` (depends on T023)
- [X] T025 [P] [US4] Create `SpaceBreadcrumb` component: fetches `GET /v1/spaces/{id}/ancestors`, renders ancestor name path (e.g. "Engineering >") for spaces whose parent is not visible in the user's list in `apps/web/components/spaces/SpaceBreadcrumb.tsx` (depends on T023)
- [X] T026 [P] [US4] Create `SetParentModal` component: admin UI with space-picker to call `PATCH /v1/spaces/{id}/parent`; includes a "Remove parent" action that calls `DELETE /v1/spaces/{id}/parent`; shows error message on 400 (`invalid_parent`) in `apps/web/components/spaces/SetParentModal.tsx` (depends on T023)
- [X] T027 [US4] Update `SpaceCard` to accept `depth` prop for indentation and render `SpaceBreadcrumb` when space has `parent_space_id` but parent is absent from visible set; show "Set parent" action button for admins in `apps/web/components/spaces/SpaceCard.tsx` (depends on T023, T025, T026)
- [X] T028 [US4] Update `apps/web/app/spaces/page.tsx` to call the `SpaceAccess[]`-returning `GET /v1/spaces`, pass result to `SpaceHierarchyView`, and wire the `SetParentModal` open/close state per space card (depends on T023, T024, T027)

**Checkpoint**: US4 is independently functional. Visit the spaces page as a user with mixed direct/inherited access and verify nested layout and breadcrumb.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates, coverage, and end-to-end validation.

- [X] T029 [P] Run `ruff check --fix` and `black .` on all new Python files (`space_access.py`, `space_hierarchy.py`, updated `space.py`, `space.py` adapter, router) and fix any remaining violations
- [X] T030 Run `cd apps/api && uv run pytest --cov=tessera_api --cov-report=term-missing` and confirm coverage is at or above the project baseline; fix any uncovered branches in the new service and adapter methods
- [X] T031 Execute all scenarios from `specs/041-nested-spaces/quickstart.md` against a running dev stack (`make dev` + `make db-migrate`) and confirm all acceptance checklist items pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (migration must exist for adapter tests to run)
- **US1 (Phase 3)**: Depends on Phase 2 — BLOCKS US2
- **US2 (Phase 4)**: Depends on US1 — shares same CTE implementation; tests verify isolation
- **US3 (Phase 5)**: Depends on Phase 2 (port/adapter) — can start in parallel with US1/US2 if staffed
- **US4 (Phase 6)**: Depends on US1 (GET /spaces returns SpaceAccess) and US3 (GET /ancestors endpoint)
- **Polish (Phase 7)**: Depends on all story phases being complete

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational — no story dependencies
- **US2 (P1)**: Shares US1 implementation; tests run after US1 endpoints exist
- **US3 (P2)**: Repository port is foundational; service + endpoints are independent of US1/US2
- **US4 (P3)**: Requires US1 (new GET /spaces shape) and US3 (ancestors endpoint)

### Within Each User Story

1. Write tests first (TDD) — confirm each test **fails** before implementing
2. Domain models / value objects before services
3. Services before adapter implementations
4. Adapter implementations before router handlers
5. Router handlers before frontend consumption

### Parallel Opportunities

- T002 ‖ T003 (different files, both foundational domain objects)
- T006 ‖ T007 (unit tests vs integration tests, different packages)
- T012 ‖ T013 (unit isolation tests vs API isolation tests)
- T016 ‖ T017 (unit tests vs integration tests for US3)
- T023 ‖ T024 ‖ T025 ‖ T026 (independent frontend files)
- T029 ‖ T030 (different tools)

---

## Parallel Example: User Story 3

```bash
# Write tests in parallel (different packages):
Task T016: unit tests for set_parent validations  →  packages/core/tests/test_space_hierarchy.py
Task T017: API integration tests for PATCH/DELETE  →  apps/api/tests/test_space_hierarchy.py

# Implement in parallel after tests written:
Task T018+T019: SpaceHierarchyService methods  →  packages/core/
Task T020: adapter SQL implementations          →  apps/api/
```

---

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Complete Phase 1: Migration
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 (inherited access via CTE)
4. Complete Phase 4: US2 (isolation tests pass)
5. **STOP and VALIDATE**: `GET /v1/spaces` returns correct user-filtered list with inheritance
6. Deploy/demo with hierarchy access working; admin hierarchy management (US3) and UI navigation (US4) follow

### Incremental Delivery

1. Migration + Foundational → schema and domain ready
2. US1 → inherited access works end-to-end → demo
3. US2 → isolation verified → secure
4. US3 → admins can build hierarchies → structure manageable
5. US4 → frontend shows tree + breadcrumbs → full UX complete

---

## Notes

- All TDD phases: the test task is **done** only after the test file exists AND `pytest` reports the test as FAILED (for the right reason — not ImportError, not TypeError from missing class, but AssertionError or similar domain failure)
- The `list_accessible_by_user` CTE is the single most critical piece — it must include `WHERE s.company_id = :company_id` in BOTH the base leg AND the recursive leg (see constitution Principle VI)
- `GET /v1/spaces` is a **breaking change**: existing tests in `test_space_visibility.py` that expect all company spaces must be updated in T015
- The `parent_space_id` FK uses `ON DELETE SET NULL` — no application-layer parent-deletion handler is needed
- Frontend Tailwind: use `slate-*` neutrals and `indigo-600` accent per constitution UI Design System; do not introduce `gray-*` or `blue-*`
