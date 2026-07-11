# Tasks: Space Access Management for Company Members

**Input**: Design documents from `/specs/058-member-space-access/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/member-space-access.md, quickstart.md

**Tests**: INCLUDED — Constitution IV (TDD, non-negotiable). Within each story, tests are written first and must fail before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in every description

## Conventions (from research.md R7 + memory)

- `packages/core` tests: `@pytest.mark.asyncio` (pytest-asyncio)
- `apps/api` tests: `@pytest.mark.anyio`; unit tests patch **module-level** router imports; integration tests use `fastapi.testclient.TestClient` (sync)
- Ignore pre-existing failures: `test_ports`, `migration_0002`, `tessera_mcp`, and the unreachable 85% API coverage gate (~73% baseline) — run targeted suites with `--no-cov`
- No migrations, no new dependencies in this feature

---

## Phase 1: Setup

**Purpose**: Confirm a clean starting point; this feature adds no dependencies, migrations, or scaffolding.

- [X] T001 Record the pre-change test baseline: run `cd apps/api && python -m pytest tests/test_tenant_isolation.py tests/integration -q --no-cov` and `cd packages/core && python -m pytest -q`, noting any failures beyond the known-unrelated set (research.md R7) so feature validation isn't confused by pre-existing breakage

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

**No foundational tasks.** The feature builds entirely on existing infrastructure: `SpaceRepository.list_by_company`, `list_accessible_by_user`, `SpaceMembershipRepository.list_by_user`, `MembershipService` writes/audit, `CompanyAdminContext`/`CompanyMemberContext`, and the implicit company-admin rule (`effective_space_role(..., is_company_admin=True)`, feature 036). No schema changes.

**Checkpoint**: User story implementation can begin immediately after T001.

---

## Phase 3: User Story 1 - Admin grants a member access to spaces from user management (Priority: P1) 🎯 MVP

**Goal**: From the Users page, a company admin opens a member's space access, sees every company space with the member's direct/effective role, and grants / changes / revokes access via the existing per-space member endpoints. Backed by new core `MemberAccessService` + admin-gated `GET /v1/companies/members/{user_id}/space-access`.

**Independent Test**: As a company admin, add a fresh user to the company, open their space access from `/users`, grant access to an existing space, then as that user confirm the space and its documents are visible (quickstart.md scenarios 1–2).

### Tests for User Story 1 (write first — must fail before implementation) ⚠️

- [X] T002 [P] [US1] Core service tests in `packages/core/tests/test_member_access_service.py` (pytest-asyncio): every company space appears exactly once; `direct_role`/`effective_role`/`is_direct` derivation for direct, inherited-only (`direct_role=None`, `effective_role` set, `is_direct=False`), and no-access rows; spaces of another company never appear; invariant `is_direct == (direct_role is not None)`
- [X] T003 [P] [US1] Router unit tests in `apps/api/tests/unit/test_member_space_access_router.py` (anyio, patching module-level imports in `companies.py`): 200 response shape per contract (`member` + `spaces[]` with `direct_role`/`effective_role`/`is_direct`); 403 for non-admin caller; generic 404 for a `user_id` not in the active company
- [X] T004 [P] [US1] Integration tests in `apps/api/tests/integration/test_member_space_access.py` (TestClient): admin fetches a fresh member's access (all spaces `effective_role=null`) → grants via existing `POST /v1/spaces/{id}/members` → re-fetch shows the role and inherited access on child spaces → member's `GET /v1/spaces` now lists the space; role change via `PUT` and revoke via `DELETE` reflected on re-fetch (FR-001, FR-002, FR-003, FR-008, FR-011); duplicate grant returns 400 with existing access intact (edge case)
- [X] T005 [P] [US1] Tenant-isolation cases in `apps/api/tests/test_tenant_isolation.py`: (a) Company A admin requests space-access of a Company B member → 404, no data, `cross_tenant_denied` audit record; (b) non-admin Company A member calls the endpoint → 403 (plan.md isolation tests 1 and 4)
- [X] T006 [P] [US1] Panel component tests in `apps/web/tests/member-space-access-panel.test.tsx` (Vitest): renders all spaces with access states; no-access row offers grant with role select defaulting to `viewer`; `is_direct` row offers change-role and revoke; inherited-only row is informational (no revoke); grant/change/revoke call the space-member endpoints and update rows in place

### Implementation for User Story 1

- [X] T007 [P] [US1] Create `MemberSpaceAccess` read model (frozen dataclass: `space`, `direct_role`, `effective_role`, `is_direct`) in `packages/core/tessera_core/domain/member_space_access.py` per data-model.md
- [X] T008 [US1] Implement `MemberAccessService.space_access_for_member(member_id, company_id)` in `packages/core/tessera_core/services/member_access.py`: left-join `list_by_company(company_id)` with `list_accessible_by_user(member_id, company_id)` (effective role + is_direct) and `list_by_user(member_id)` filtered to company spaces (direct role); make T002 pass (depends on T007)
- [X] T009 [US1] Add `GET /v1/companies/members/{user_id}/space-access` to `apps/api/tessera_api/routers/companies.py`: `CompanyAdminContext` gate; validate target holds a `company_memberships` row for the active company else generic 404 (+ `cross_tenant_denied` audit on cross-company hit, 053/054 convention); assemble response via `MemberAccessService`; module-level imports for patchability; make T003, T004, T005 pass
- [X] T010 [P] [US1] Create web API client `apps/web/lib/members.ts`: `getMemberSpaceAccess(userId)` for the new endpoint plus typed wrappers for `POST /v1/spaces/{id}/members`, `PUT /v1/spaces/{id}/members/{userId}`, `DELETE /v1/spaces/{id}/members/{userId}`
- [X] T011 [US1] Create `apps/web/components/members/MemberSpaceAccessPanel.tsx` (client component, follows `SpaceMembersPanel`/`AddUserPanel` patterns): lists `spaces[]` per contract UI rules; grant (role select, default viewer), change role, revoke with optimistic in-place updates; slate neutrals / indigo-600 actions / red revoke; make T006 pass (depends on T010)
- [X] T012 [US1] Wire per-row "Spaces" action into `apps/web/app/users/page.tsx` opening `MemberSpaceAccessPanel` for that member — visible to company admins only (FR-004) (depends on T011)
- [X] T013 [US1] Verify story: `cd packages/core && python -m pytest tests/test_member_access_service.py -q`; `cd apps/api && python -m pytest tests/unit/test_member_space_access_router.py tests/integration/test_member_space_access.py tests/test_tenant_isolation.py -q --no-cov`; `cd apps/web && npx vitest run tests/member-space-access-panel.test.tsx` — all green

**Checkpoint**: User Story 1 fully functional — an admin can take a new member from "no access" to "sees the space" without leaving `/users` (SC-001).

---

## Phase 4: User Story 2 - Company admin can administer every space in the company (Priority: P2)

**Goal**: `GET /v1/spaces`, `GET /v1/spaces/{id}`, and `GET /v1/spaces/{id}/ancestors` gain a company-admin branch: admins see every company space (non-member spaces returned with `effective_role: "admin"`, `is_direct: false`); non-admin behavior unchanged. Implemented in core `SpaceHierarchyService`.

**Independent Test**: One user creates a space without adding the company admin as a member; the admin still sees it on the Spaces page, can open it, and can grant another member access to it (quickstart.md scenario 4).

### Tests for User Story 2 (write first — must fail before implementation) ⚠️

- [X] T014 [P] [US2] Core service tests in `packages/core/tests/test_space_hierarchy_admin.py` (pytest-asyncio): for a company admin, accessible set = membership-derived accesses (values unchanged) ∪ remaining company spaces as `SpaceAccess(effective_role=ADMIN, is_direct=False)`; non-admin set unchanged; single-space and ancestor access checks honor the same branch; spaces of another company never included
- [X] T015 [P] [US2] Integration tests in `apps/api/tests/integration/test_admin_space_visibility.py` (TestClient): company admin's `GET /v1/spaces` includes a space they don't belong to with `effective_role: "admin"`, `is_direct: false`; `GET /v1/spaces/{id}` and `/ancestors` succeed for that space; non-admin member still sees only membership-derived spaces (FR-005); response shape unchanged per contract
- [X] T016 [P] [US2] Tenant-isolation case in `apps/api/tests/test_tenant_isolation.py`: Company A admin's admin-wide space listing never contains Company B spaces; cross-company `GET /v1/spaces/{id}` still returns generic 404 with `cross_tenant_denied` audit (plan.md isolation tests 2 and 3)

### Implementation for User Story 2

- [X] T017 [US2] Add the company-admin listing/access branch to `packages/core/tessera_core/services/space_hierarchy.py`: when `is_company_admin`, union membership-derived accesses with all remaining `list_by_company(company_id)` spaces as implicit `SpaceAccess(effective_role=ADMIN, is_direct=False)`; apply the same rule to single-space and ancestors access checks; make T014 pass
- [X] T018 [US2] Update `apps/api/tessera_api/routers/spaces.py`: switch `list_spaces` from `CompanyContext` to `CompanyMemberContext` and pass `is_company_admin` (derived from the caller's session-bound membership row, never input) into `SpaceHierarchyService`; apply the same branch to `get_space` and `get_ancestors`; keep module-level imports; make T015, T016 pass (depends on T017)
- [X] T019 [US2] Verify story + ripple check (research.md R3): `cd packages/core && python -m pytest tests/test_space_hierarchy_admin.py -q`; `cd apps/api && python -m pytest tests/integration/test_admin_space_visibility.py tests/test_tenant_isolation.py tests/integration/test_spaces*.py -q --no-cov`; confirm existing consumers of `GET /v1/spaces` (Spaces page, document add/move space pickers, NavBar role probe) still pass their suites

**Checkpoint**: User Stories 1 AND 2 work independently — every company space is reachable for administration (SC-003), and the US1 panel can grant access to spaces the admin doesn't belong to.

---

## Phase 5: User Story 3 - A member with no space access understands their situation (Priority: P3)

**Goal**: The Spaces page empty state branches on company role: non-admin with zero accesses sees "No spaces have been shared with you yet. A company administrator can grant you access."; a company admin with an empty list keeps the existing "no spaces" copy + Add Space (the company truly has none, given US2).

**Independent Test**: Log in as a company member with no space access and confirm the spaces area explains access must be granted by an administrator, not that no spaces exist (quickstart.md scenario 3).

### Tests for User Story 3 (write first — must fail before implementation) ⚠️

- [X] T020 [P] [US3] Empty-state tests in `apps/web/tests/spaces-empty-state.test.tsx` (Vitest): non-admin member with zero spaces sees the "not shared with you yet / administrator can grant access" message and never "No spaces available in your company"; company admin with zero spaces sees the existing copy with Add Space; once a space is listed, no empty-state message renders (FR-007, SC-005)

### Implementation for User Story 3

- [X] T021 [US3] Update the empty state in `apps/web/app/spaces/page.tsx` (currently "No spaces available in your company." at ~line 71): branch on the caller's company role — non-admin + 0 accesses → new explanatory copy; admin + 0 spaces → existing copy; make T020 pass

**Checkpoint**: All of US1–US3 independently functional — the stranded-member experience is fully closed.

---

## Phase 6: User Story 4 - Every path into the company produces a manageable member (Priority: P3)

**Goal**: Prove (and fix if needed) that members from all four join paths — company creation, invitation acceptance, direct add, email-domain matching — appear in the roster and member search, and can be granted space access end-to-end. Research R5 expects no code change; this story encodes parity as tests.

**Independent Test**: Create one member through each join path, then as company admin confirm each appears in user management and member search, and that granting each access works end-to-end (quickstart.md scenario 5).

### Tests for User Story 4 (parity sweep — these ARE the deliverable) ⚠️

- [X] T022 [US4] Join-path parity integration tests in `apps/api/tests/integration/test_join_path_parity.py` (TestClient): create one member per path (onboarding company creation, invitation acceptance per 054, direct add via `POST /v1/companies/members`, domain match at sign-up per 055); for each: appears in `GET /v1/companies/members` roster, appears in `GET /v1/spaces/{id}/members/search`, appears in the US1 space-access endpoint, `POST /v1/spaces/{id}/members` grant succeeds, and the member's `GET /v1/spaces` then lists the space (FR-006, SC-002)

### Implementation for User Story 4

- [X] T023 [US4] Fix any parity gap T022 exposes in the relevant module (`apps/api/tessera_api/routers/companies.py`, `onboarding.py`, or member search in the spaces members router); if no gap (expected per research.md R5), mark N/A with the passing test run as evidence

**Checkpoint**: All user stories complete — every join path yields a grantable, manageable member.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Whole-feature validation and quality gates.

- [X] T024 Run the full quickstart automated validation (quickstart.md): core, API (`--no-cov`), and web suites for all feature files plus `tests/test_tenant_isolation.py` — all green, ignoring only the known-unrelated failures from T001
- [X] T025 [P] Quality gates: `ruff check apps/api packages/core && black --check apps/api packages/core`; run the web app's existing lint over changed files in `apps/web`
- [ ] T026 Manual quickstart walkthrough (quickstart.md scenarios 1–6) against the dev stack, verifying the reported account case: grant `felipe+1@gusba.dev` access from `/users` and confirm the account sees and can use the space (spec Assumptions — primary verification case)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Empty — no blockers beyond T001
- **User Stories (Phases 3–6)**: All can start after T001; no story depends on another to function
  - US1 (P1) → US2 (P2) → US3 (P3) → US4 (P3) is the recommended priority order
  - US4's T022 references the US1 endpoint for one assertion — if run before US1, drop that assertion or schedule US4 last (recommended)
- **Polish (Phase 7)**: After all desired stories complete

### Story-level notes

- **US1** is self-contained: `MemberAccessService` calls `list_by_company` directly, so it does NOT depend on US2's router changes
- **US2** touches only `space_hierarchy.py` + `spaces.py` — no overlap with US1 files
- **US3** is web-only (one page + one test) — independent of everything except the existing spaces API
- **US4** is test-only unless a gap is found

### Within Each User Story

- Tests first, confirmed failing, then implementation (Constitution IV)
- Domain model → service → router → web client → component → page wiring
- Story verification task last

### Parallel Opportunities

- All test-writing tasks within a story are [P] with each other (different files): T002–T006; T014–T016
- T007 (domain model) ∥ T010 (web client) — different packages
- After T001, US1/US2/US3 phases can proceed in parallel across developers (disjoint files); the only shared file is `apps/api/tests/test_tenant_isolation.py` (T005 vs T016 — coordinate or serialize)

---

## Parallel Example: User Story 1

```bash
# Launch all US1 test-writing tasks together:
Task: "T002 core service tests in packages/core/tests/test_member_access_service.py"
Task: "T003 router unit tests in apps/api/tests/unit/test_member_space_access_router.py"
Task: "T004 integration tests in apps/api/tests/integration/test_member_space_access.py"
Task: "T005 tenant-isolation cases in apps/api/tests/test_tenant_isolation.py"
Task: "T006 panel tests in apps/web/tests/member-space-access-panel.test.tsx"

# Then start implementation in parallel where files are disjoint:
Task: "T007 MemberSpaceAccess read model in packages/core/tessera_core/domain/member_space_access.py"
Task: "T010 web API client in apps/web/lib/members.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001 (baseline)
2. Phase 3 complete (T002–T013)
3. **STOP and VALIDATE**: quickstart scenarios 1–2 — admin grants from `/users`, member sees the space
4. Ship: the reported gap (felipe+1@gusba.dev stranded) is fixed for spaces the admin can see

### Incremental Delivery

1. US1 → MVP: member-centric grant surface works
2. US2 → no space is orphaned from administration (admin-wide visibility)
3. US3 → honest empty state for members awaiting access
4. US4 → parity proof across all join paths
5. Polish → full validation + quality gates + manual walkthrough

Each story is independently testable and adds value without breaking previous stories.
