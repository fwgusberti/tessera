# Tasks: Add Space Membership (Frontend)

**Input**: Design documents from `/specs/043-add-space-membership/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Required — Constitution Principle IV (TDD non-negotiable). API: pytest unit tests for the repository method and router endpoint. Web: Vitest tests for the new `AddMemberForm` component, plus updates to the existing `members.test.tsx` suite that currently covers `InviteMemberForm`.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete-task dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Exact file paths included in all task descriptions

## Path Conventions

- **Domain**: `packages/core/tessera_core/domain/`, `packages/core/tessera_core/ports/repositories/`
- **API**: `apps/api/tessera_api/adapters/repositories/`, `apps/api/tessera_api/routers/`
- **API tests**: `apps/api/tests/unit/`
- **Web components**: `apps/web/components/members/`
- **Web types**: `apps/web/lib/types.ts`
- **Web tests**: `apps/web/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the read-projection type used by both the API and the frontend before any story-specific code references it.

- [X] T001 [P] Add `CompanyMemberMatch` domain class (`user_id`, `display_name`, `email`) in `packages/core/tessera_core/domain/company_member_match.py`
- [X] T002 [P] Add `CompanyMemberMatch` TypeScript interface (`user_id`, `display_name`, `email`) to `apps/web/lib/types.ts`

---

## Phase 2: User Story 1 - Add an Existing Company Member to a Space (Priority: P1) 🎯 MVP

**Goal**: A space admin can search company members by name/email from the Space Members page and add a matched, not-yet-a-member person with a chosen role, without knowing their internal user ID.

**Independent Test**: As a space admin, open a space's Members page, open "Add Member", search for a colleague not yet in the space by name or email fragment, select them, choose a role, submit, and confirm they appear in the member list with that role.

### Tests for User Story 1 ⚠️ Write FIRST — confirm they FAIL before implementing

- [X] T003 [P] [US1] Write failing pytest tests for `SqlCompanyRepository.search_members_for_space` covering: company-scoped match on email/display_name via case-insensitive partial match, excludes user IDs already present in `space_memberships` for the target space, orders results by `display_name`, respects the result limit, in `apps/api/tests/unit/test_company_repo.py` (extend existing file)
- [X] T004 [P] [US1] Write failing pytest tests for `GET /v1/spaces/{space_id}/members/search` covering: 200 with matching company members, 200 with empty `members: []` for no matches, 403 when caller is not an admin of the target space (and not a company admin), 404 when `space_id` belongs to a different company than the caller's active company, in `apps/api/tests/unit/test_members_router.py` (new file)
- [X] T005 [P] [US1] Write failing Vitest tests for `AddMemberForm` covering: no search fires below 2 characters, debounced search calls `GET /v1/spaces/{spaceId}/members/search?q=...`, matching results render with name/email, empty-results message renders distinctly from the not-yet-searched state, selecting a result + choosing a role + submitting calls `POST /v1/spaces/{spaceId}/members` with `{ user_id, role }` and invokes `onSuccess`, in `apps/web/tests/add-member-form.test.tsx` (new file)

### Implementation for User Story 1

- [X] T006 [US1] Add abstract method `search_members_for_space(company_id, space_id, query, limit=20) -> list[CompanyMemberMatch]` to the `CompanyRepository` port in `packages/core/tessera_core/ports/repositories/company.py` (depends on T001)
- [X] T007 [US1] Implement `search_members_for_space` in `SqlCompanyRepository` (`apps/api/tessera_api/adapters/repositories/company.py`): join `company_memberships` to `users` filtered by `company_id`, `ILIKE` match on `email`/`display_name`, exclude `user_id`s found in `space_memberships` for `space_id`, order by `display_name`, apply `limit` (depends on T006; T003 must be failing first)
- [X] T008 [US1] Add `GET /v1/spaces/{space_id}/members/search` to `apps/api/tessera_api/routers/members.py`: validate the space belongs to the caller's active company (reuse `_require_space_in_company`), authorize via the same `can_manage_members` check used by `invite_member` (admin of this space or company admin — FR-002a), call `search_members_for_space`, return `{"members": [...]}` (depends on T007; T004 must be failing first)
- [X] T009 [P] [US1] Implement `AddMemberForm` in `apps/web/components/members/AddMemberForm.tsx`: input with 300ms debounce and 2-character minimum (FR-007), calls the search endpoint, renders matching results with a distinct empty-state message (FR-008), single-select of one result, role select (`viewer` default, `editor`, `admin`), submit calls `POST /v1/spaces/{spaceId}/members` and invokes an `onSuccess` callback on success (depends on T002; T005 must be failing first)
- [X] T010 [US1] Replace `InviteMemberForm` with `AddMemberForm` in `apps/web/components/members/SpaceMembersPanel.tsx`, preserving the existing admin-only visibility gating (FR-001, FR-009) (depends on T008, T009)
- [X] T011 [US1] Delete `apps/web/components/members/InviteMemberForm.tsx` now that `SpaceMembersPanel` no longer references it (depends on T010)
- [X] T012 [US1] Update `apps/web/tests/members.test.tsx`: remove the `InviteMemberForm` describe block and update the `SpaceMembersPanel` "shows/hides invite form" assertions to target `AddMemberForm`'s rendered control (depends on T010, T011)

**Checkpoint**: A space admin can search and add an existing company member to a space end-to-end. User Story 1 is independently functional.

---

## Phase 3: User Story 2 - Prevent and Explain Failed Additions (Priority: P2)

**Goal**: When adding a member fails (duplicate, permission, ineligible person, network error), the admin sees a distinct, human-readable message and can retry without losing their search/selection/role choice.

**Independent Test**: Trigger each failure path (duplicate add, insufficient permission, ineligible/not-found person, simulated network failure) against the Add Member flow and confirm a distinct message is shown for each, and the form retains the admin's query, selection, and role choice.

### Tests for User Story 2 ⚠️ Write FIRST — confirm they FAIL before implementing

- [X] T013 [US2] Extend `apps/web/tests/add-member-form.test.tsx` with failing tests for each `POST /v1/spaces/{id}/members` failure response mapped per FR-006 (400 "already a member" → already-member message + member list refresh trigger; 403 → permission message; 404 → "no longer eligible" message; network/fetch rejection → retryable network message) and assert `query`, `selected`, and `role` are unchanged after each failure (FR-010)

### Implementation for User Story 2

- [X] T014 [US2] Add failure-mapping and retained-state handling to `AddMemberForm` (`apps/web/components/members/AddMemberForm.tsx`): catch submit errors, map response status/body to one of `already_member | forbidden | ineligible | network`, render the matching message, keep `query`/`selected`/`role` state intact on failure, and trigger a member-list refresh when the failure is "already a member" so the UI reflects reality (depends on T013, T009)

**Checkpoint**: User Stories 1 and 2 both work end-to-end; every documented failure path produces a distinct, retryable message.

---

## Phase 4: Polish & Cross-Cutting Concerns

- [X] T015 [P] Run `quickstart.md` scenarios 1–5 against a local dev stack and confirm actual responses/UI match the documented expectations
- [X] T016 [P] Run Ruff/Black on all touched Python files and the web project's lint/typecheck script on all touched TypeScript files; fix any violations (Constitution Principle V)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **User Story 1 (Phase 2)**: Depends on Setup (T001, T002) completion
- **User Story 2 (Phase 3)**: Depends on User Story 1 completion (`AddMemberForm` must exist — spec.md explicitly notes US2 builds on US1)
- **Polish (Phase 4)**: Depends on User Story 1 and User Story 2 completion

### Within Each User Story

- Tests MUST be written and confirmed FAILING before implementation tasks begin
- Domain/port changes before adapter implementation before router wiring (T006 → T007 → T008)
- Frontend component (T009) can be built in parallel with backend (T006–T008) since both sides only need the agreed contract (`contracts/members.md`)
- Wiring (`SpaceMembersPanel`) and cleanup (deleting `InviteMemberForm`, updating its tests) happen only after `AddMemberForm` itself is implemented

### Parallel Opportunities

- T001 and T002 (Setup) can run in parallel
- T003, T004, and T005 (US1 tests, three different files) can run in parallel
- T009 (frontend component) can run in parallel with T006–T008 (backend chain)
- T015 and T016 (Polish) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together (different files, all must fail first):
Task: "Failing repo tests for search_members_for_space in apps/api/tests/unit/test_company_repo.py"
Task: "Failing router tests for GET /v1/spaces/{space_id}/members/search in apps/api/tests/unit/test_members_router.py"
Task: "Failing AddMemberForm tests in apps/web/tests/add-member-form.test.tsx"

# Backend chain and frontend component can then proceed in parallel:
Task: "Implement search_members_for_space port + adapter (T006, T007)"
Task: "Implement AddMemberForm component (T009)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: User Story 1
3. **STOP and VALIDATE**: Run quickstart.md Scenarios 1–3 independently
4. Deploy/demo if ready — admins can already search and add members; failures just show generic messages until US2 lands

### Incremental Delivery

1. Setup → Foundation ready
2. Add User Story 1 → validate independently → deploy/demo (MVP)
3. Add User Story 2 → validate independently (quickstart Scenarios 4–5) → deploy/demo
4. Polish

---

## Notes

- [P] tasks = different files, no incomplete-task dependency
- [Story] label maps task to specific user story for traceability
- Verify each story's tests fail before implementing that story
- Commit after each task or logical group
- `InviteMemberForm.tsx` removal (T011) and its test updates (T012) are part of US1, not Polish — the spec's Assumptions section treats the replacement as part of the core deliverable, not cleanup
