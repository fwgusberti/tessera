---

description: "Task list for User Roles (024) feature implementation"
---

# Tasks: User Roles

**Input**: Design documents from `/specs/024-user-roles/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Included — Constitution Principle IV (TDD) is NON-NEGOTIABLE. Unit, contract, and integration tests must be written first and confirmed failing before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Database Foundation)

**Purpose**: Create the database schema that all subsequent phases depend on.

- [X] T001 Create Alembic migration 0006_space_memberships with `space_memberships` table, `uq_space_membership` unique constraint, and `ix_space_memberships_space` / `ix_space_memberships_user` indexes in `db/migrations/versions/0006_space_memberships.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain entities, port interfaces, ORM adapter, and SQL repository that MUST be complete before any user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Add `SpaceRole` enum (`VIEWER | EDITOR | ADMIN`) and `SpaceMembership` Pydantic entity (id, space_id, user_id, role, invited_by_user_id, created_at, updated_at) to `packages/core/tessera_core/domain/entities.py`
- [X] T003 [P] Add `SpaceMembershipRepository` abstract class with `add`, `get`, `list_by_space`, `list_by_user`, `update_role`, `remove`, and `count_admins` abstract methods to `packages/core/tessera_core/ports/repositories.py`
- [X] T004 [P] Add `SpaceMembershipModel` SQLAlchemy ORM class with `UniqueConstraint("space_id", "user_id")` and two indexes to `apps/api/tessera_api/adapters/models.py`
- [X] T005 Add permission functions `get_space_membership_role`, `effective_space_role`, `can_write_document`, `can_manage_members`, and `can_read_space_document` operating on `list[SpaceMembership]` to `packages/core/tessera_core/permissions/access.py`
- [X] T006 Implement `SqlSpaceMembershipRepository` with async `AsyncSession` CRUD methods and `count_admins` using `SELECT COUNT(*) WHERE role='admin'` in `apps/api/tessera_api/adapters/repo.py`

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 — Administrators Manage Space Membership and Roles (Priority: P1) 🎯 MVP

**Goal**: A space Admin can invite registered users, assign roles, change roles, and remove members. Non-admin members cannot perform these actions. The last-admin guard prevents a space from losing all admins.

**Independent Test**: Invite a user to a space as Editor, confirm they appear in the member list with the correct role, then verify that an Editor cannot change another member's role (should get 403).

### Tests for User Story 1 ⚠️ WRITE FIRST — CONFIRM FAILING BEFORE IMPLEMENTING

- [X] T007 [P] [US1] Write failing unit tests for all five `access.py` permission functions and all three `MembershipService` methods (invite, change_role, remove) including last-admin guard in `packages/core/tests/test_membership.py`
- [X] T008 [P] [US1] Write failing HTTP contract tests for all 5 member endpoints (`POST /spaces/{id}/members`, `GET /spaces/{id}/members`, `GET /spaces/{id}/members/me`, `PUT /spaces/{id}/members/{user_id}`, `DELETE /spaces/{id}/members/{user_id}`) in `apps/api/tests/contract/test_members.py`
- [X] T009 [P] [US1] Write failing integration tests for invite, change-role, and remove-member flows including permission checks (403 for non-admin) and last-admin 409 guard in `apps/api/tests/integration/test_members.py`
- [X] T010 [P] [US1] Write failing component tests for `SpaceMembersPanel` (list rendering, admin-only controls), `InviteMemberForm` (submit flow), and `RoleBadge` (correct styles per role) in `apps/web/tests/members.test.tsx`

### Implementation for User Story 1

- [X] T011 [US1] Implement `MembershipService` with `invite` (actor-must-be-admin guard, duplicate-member guard, audit `member_invited`), `change_role` (last-admin guard, audit `role_changed`), and `remove` (last-admin guard, audit `member_removed`) in `packages/core/tessera_core/services/membership.py`
- [X] T012 [US1] Implement members router with all 5 endpoints, mapping `PermissionError → 403`, `ValueError("not a member") → 404`, `ValueError("last admin") → 409` in `apps/api/tessera_api/routers/members.py`
- [X] T013 [US1] Register members router in `apps/api/tessera_api/main.py`
- [X] T014 [P] [US1] Create `RoleBadge` component with Tailwind styles (`bg-indigo-100 text-indigo-700` for ADMIN, `bg-slate-100 text-slate-700` for EDITOR, `bg-slate-50 text-slate-500` for VIEWER) in `apps/web/components/members/RoleBadge.tsx`
- [X] T015 [P] [US1] Create `InviteMemberForm` component with `user_id` input and role selector dropdown calling `POST /spaces/{id}/members` in `apps/web/components/members/InviteMemberForm.tsx`
- [X] T016 [US1] Create `SpaceMembersPanel` component rendering member list with `RoleBadge` per row; conditionally show `InviteMemberForm`, role-change dropdown, and remove button only when caller is ADMIN in `apps/web/components/members/SpaceMembersPanel.tsx`
- [X] T017 [US1] Create members management page that calls `GET /spaces/{id}/members/me` to determine viewer role then renders `SpaceMembersPanel` in `apps/web/app/spaces/[id]/members/page.tsx`
- [X] T018 [US1] Add current-user role badge to space navigation by calling `GET /spaces/{id}/members/me` on space page load in `apps/web/components/NavBar.tsx`

**Checkpoint**: User Story 1 is fully functional and independently testable. Space admins can manage membership end-to-end.

---

## Phase 4: User Story 2 — Editors Create and Modify Documents (Priority: P2)

**Goal**: Enforce write permissions on documents based on `SpaceMembership.role`. Editors can create/edit/delete; Viewers are blocked with a 403.

**Independent Test**: Create an Editor and a Viewer in the same space. Confirm Editor gets 201 on `POST /documents` and Viewer gets 403. Confirm Viewer gets 200 on `GET /documents/{id}`.

### Tests for User Story 2 ⚠️ WRITE FIRST — CONFIRM FAILING BEFORE IMPLEMENTING

- [X] T019 [P] [US2] Write failing integration tests verifying Editor gets 201 and Viewer gets 403 on document create, edit, and delete; also verify Viewer gets 200 on document read in `apps/api/tests/integration/test_document_permissions.py`

### Implementation for User Story 2

- [X] T020 [US2] Update document create, edit, and delete handlers to fetch `SpaceMembership` via `SqlSpaceMembershipRepository` and call `can_write_document(user, space_id, memberships)` (→ 403 if False) and `can_read_space_document` (→ 403 if False) in `apps/api/tessera_api/routers/documents.py`

**Checkpoint**: User Stories 1 and 2 both work independently. Role-based document access is enforced.

---

## Phase 5: User Story 3 — Global Admins Govern the Platform (Priority: P3)

**Goal**: A Global Admin (`User.is_admin=True`) can promote or demote any user's platform role via `PUT /users/{id}/platform-role` and can act as implicit space ADMIN in any space without explicit membership.

**Independent Test**: Log in as Global Admin (not a member of `other-space`), call `GET /spaces/{other_space_id}/members` and expect 200. Then call `PUT /users/{target}/platform-role` with `is_admin=true` and verify the target user gains global admin rights. A regular user calling the same endpoint must get 403.

### Tests for User Story 3 ⚠️ WRITE FIRST — CONFIRM FAILING BEFORE IMPLEMENTING

- [X] T021 [P] [US3] Write failing integration tests for `PUT /users/{id}/platform-role` (200 success, 403 for non-global-admin, audit record `platform_role_changed` written) and for global admin bypassing space membership check on member list endpoint in `apps/api/tests/integration/test_admin.py`

### Implementation for User Story 3

- [X] T022 [US3] Add `PUT /users/{user_id}/platform-role` endpoint requiring `user_info["is_admin"] == True`, updating `users.is_admin` via `UserRepository`, and emitting `AuditRecord(action="platform_role_changed", entity_type="user", metadata={user_id, previous_is_admin, new_is_admin})` in `apps/api/tessera_api/routers/admin.py`

**Checkpoint**: All three user stories are independently functional. Platform governance layer is in place.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates and end-to-end validation across all stories.

- [X] T023 [P] Run Ruff and Black linting checks on `packages/core`, `apps/api`, and `apps/web` and fix all violations to satisfy Constitution Principle V
- [X] T024 Execute all four quickstart.md validation scenarios (US1 invite flow, US2 editor/viewer write check, US3 global admin flow, last-admin guard) and confirm audit records in `audit_records` table per `data-model.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately with T001
- **Foundational (Phase 2)**: T002, T003, T004 can start in parallel after T001; T005 depends on T002; T006 depends on T003 + T004
- **US1 (Phase 3)**: All depend on Phase 2 completion; tests T007–T010 run in parallel; implementation T011–T018 run sequentially or as sub-groups
- **US2 (Phase 4)**: Depends on Phase 2 completion + US1 `SpaceMembership` being queryable
- **US3 (Phase 5)**: Depends on Phase 2 completion; largely independent of US1/US2
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2 — no dependency on US2 or US3
- **US2 (P2)**: Starts after Phase 2 — reads `SpaceMembership` data but does not call `MembershipService`; can be developed in parallel with US1
- **US3 (P3)**: Starts after Phase 2 — the `effective_space_role` global-admin bypass (T005) is the only shared function; can be developed in parallel with US1/US2

### Within US1

- T007–T010 (tests) must be written and confirmed failing before T011–T018
- T014 and T015 can run in parallel (different files, no dependencies)
- T016 depends on T014 + T015
- T017 depends on T016
- T018 can run in parallel with T016/T017

### Parallel Opportunities

- Phase 2: T002, T003, T004 in parallel
- Phase 3 tests: T007, T008, T009, T010 all in parallel
- Phase 3 impl: T014 + T015 in parallel; T018 in parallel with T016/T017 chain
- Phase 4 test T019 and Phase 5 test T021 can run in parallel once Phase 2 is done

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all US1 test-writing tasks together (TDD step 1):
Task: T007 — unit tests for access.py + MembershipService in packages/core/tests/test_membership.py
Task: T008 — contract tests for 5 endpoints in apps/api/tests/contract/test_members.py
Task: T009 — integration tests for member flows in apps/api/tests/integration/test_members.py
Task: T010 — component tests in apps/web/tests/members.test.tsx

# After tests confirmed failing, launch parallelizable components:
Task: T014 — RoleBadge.tsx
Task: T015 — InviteMemberForm.tsx
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T006) — CRITICAL, blocks all stories
3. Write US1 tests (T007–T010), confirm they fail
4. Complete Phase 3 implementation (T011–T018)
5. **STOP and VALIDATE**: Run T007–T010 test suites; demo invite/change/remove flows
6. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 complete → Test independently → Deploy/demo (MVP!)
3. US2 complete → Test independently → Deploy/demo (write-guard enforced)
4. US3 complete → Test independently → Deploy/demo (platform governance)
5. Each story adds value without breaking previous ones

### Parallel Team Strategy

With multiple developers, after Phase 2 completes:

- **Developer A**: US1 (T007–T018)
- **Developer B**: US2 (T019–T020)
- **Developer C**: US3 (T021–T022)

---

## Notes

- **TDD is non-negotiable** (Constitution IV): write each test group, confirm it fails, then implement
- `[P]` tasks operate on different files with no inter-task dependencies
- `[Story]` label maps tasks to user stories for traceability
- Each story is independently completable and testable before moving on
- Quality gates (Ruff + Black) must pass on every commit (Constitution V)
- `effective_space_role` returns ADMIN for `user.is_admin=True` regardless of space membership — this single function powers both US1 admin bypass and US3 global admin behavior
- Last-admin guard lives in `MembershipService`, not in the router or repository (Decision 5)
