---
description: "Task list for Company User Management Page (053)"
---

# Tasks: Company User Management Page

**Input**: Design documents from `/specs/053-user-management/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/company-members.openapi.yaml ✅

**Tests**: INCLUDED — the plan's Constitution Check (Principle IV, Test-Driven Development) requires failing tests written first for the repository method, the endpoint contract (admin 200 / member 403 / unauth 401), and the cross-tenant isolation case.

**Organization**: Tasks are grouped by user story. All three stories are P1 and are served by the single new `GET /v1/companies/members` endpoint, so User Story 1 (the roster) is the MVP that ships the working, gated, and scoped endpoint; User Story 2 (access restriction) and User Story 3 (tenant scoping) primarily add the proving tests and story-specific UX/hardening for security properties that reuse existing structural mechanisms (`CompanyAdminContext`, the `WHERE company_id` predicate). See Dependencies for the coupling notes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task belongs to (US1, US2, US3)

> Implementation status: all tasks complete (T001–T022). Tests: core `test_company_member_listing.py`, API `tests/unit/test_company_members_router.py` (admin 200 / member 403 / unauth 401) and `tests/test_tenant_isolation.py::TestCompanyMembersIsolation`, frontend `tests/user-management.test.tsx` — all green. Note: web app uses **vitest** (not jest); backend test tree lives under `apps/api/tests/` (not `apps/api/tessera_api/tests/`).

## Path Conventions

Three-package layout (unchanged): `packages/core/tessera_core` (domain/ports), `apps/api/tessera_api` (FastAPI adapters/routers), `apps/web` (Next.js App Router).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the working surface; no new dependencies, languages, or migrations are introduced by this feature.

- [X] T001 Confirm on branch `053-user-management` and verify no schema migration or new dependency is required (feature reads existing `company_memberships` ⋈ `users`); create empty new files with import stubs so later tasks compile: `packages/core/tessera_core/domain/company_member_listing.py`, `apps/api/tessera_api/tests/unit/test_company_members_router.py`, `apps/web/components/company/CompanyRoleBadge.tsx`, `apps/web/app/users/page.tsx`, `apps/web/tests/user-management.test.tsx`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Framework-free domain type and port contract that every story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Create `CompanyMemberListing` value object (fields: `user_id: UUID`, `display_name: str`, `email: str`, `role: CompanyRole`) in `packages/core/tessera_core/domain/company_member_listing.py`, mirroring the existing `CompanyMemberMatch` in `packages/core/tessera_core/domain/company_member_match.py`
- [X] T003 Re-export `CompanyMemberListing` from `packages/core/tessera_core/domain/entities.py` (add to imports and `__all__` alongside the other domain types)
- [X] T004 Add abstract method `list_members(self, company_id: UUID) -> list[CompanyMemberListing]` to `CompanyRepository` in `packages/core/tessera_core/ports/repositories/company.py` (express in domain terms only, no Postgres detail; import the new value object)

**Checkpoint**: Domain type and port contract exist — user story implementation can begin.

---

## Phase 3: User Story 1 - Admin views the company's users and their roles (Priority: P1) 🎯 MVP

**Goal**: A company admin opens `/users` and sees every member of their active company, each with an identifying name/email and a company-role badge ("administrator" / "member").

**Independent Test**: Sign in as a Company A admin (Company A active), open `/users`, and confirm the page lists exactly Company A's members, each with name + email and a role badge; the endpoint returns 200 with the roster.

### Tests for User Story 1 (write first, ensure they FAIL) ⚠️

- [X] T005 [P] [US1] Core repository test: `list_members(company_id)` returns one `CompanyMemberListing` per company membership joined to its user, ordered by `display_name`, carrying the correct `role` — in `packages/core/tests/test_company_member_listing.py` (or the nearest existing core repo test module)
- [X] T006 [P] [US1] Router contract test: admin of the active company `GET /v1/companies/members` → 200 with a `members` array matching the roster (mixed roles), each item having `user_id`/`display_name`/`email`/`role` — in `apps/api/tessera_api/tests/unit/test_company_members_router.py`, following the `TestSearchMembersContract` structure in `apps/api/tessera_api/tests/unit/test_members_router.py`
- [X] T007 [P] [US1] Frontend test: the `/users` page renders a row per member with name, email, and a role badge; a member with empty `display_name` falls back to email — in `apps/web/tests/user-management.test.tsx` (mock `getCompanyMembers`)

### Implementation for User Story 1

- [X] T008 [US1] Implement `SqlCompanyRepository.list_members(company_id)` in `apps/api/tessera_api/adapters/repositories/company.py` — single `SELECT u.id, u.display_name, u.email, cm.role FROM company_memberships cm JOIN users u ON u.id = cm.user_id WHERE cm.company_id = :company_id ORDER BY u.display_name`, mapping each row to `CompanyMemberListing` (reuse the join shape from `search_members_for_space`, minus search/exclusion, plus the `role` column)
- [X] T009 [US1] Add endpoint `GET /companies/members` to `apps/api/tessera_api/routers/companies.py`, gated by the existing `CompanyAdminContext` dependency (`tessera_api.auth.oidc.require_company_admin`); derive `company_id` from the authenticated context (never from client input), call `company_repo.list_members(company_id)`, and return `{"members": [...]}` shaped per `contracts/company-members.openapi.yaml`
- [X] T010 [P] [US1] Add `CompanyMember` type and `getCompanyMembers(): Promise<CompanyMember[]>` (calling `GET /v1/companies/members`) to `apps/web/lib/companies.ts`
- [X] T011 [P] [US1] Create `CompanyRoleBadge` component (admin=indigo, member=slate; renders labels "administrator"/"member") in `apps/web/components/company/CompanyRoleBadge.tsx`, mirroring the styling conventions of `apps/web/components/members/RoleBadge.tsx`
- [X] T012 [US1] Create the User Management page in `apps/web/app/users/page.tsx` — `AuthGuard`-wrapped, fetches `getCompanyMembers()`, renders a table (name + email per row, `CompanyRoleBadge` for role) mirroring the `SpaceMembersPanel` layout; `display_name` falls back to `email` when blank (depends on T010, T011)
- [X] T013 [US1] Add a "Users" link (desktop + mobile) to `apps/web/components/NavBar.tsx` pointing at `/users`

**Checkpoint**: MVP — an admin can open `/users` and see their active company's roster with roles; the endpoint is already admin-gated and company-scoped (proven by US2/US3).

---

## Phase 4: User Story 2 - Access is restricted to company administrators (Priority: P1)

**Goal**: Only administrators of the active company can view the roster; non-admin members and unauthenticated visitors are refused with no data leaked.

**Independent Test**: Call `GET /v1/companies/members` as a non-admin member → 403 with no roster; call it unauthenticated → 401; navigating to `/users` as a non-admin shows a clean access-denied state.

### Tests for User Story 2 (write first, ensure they FAIL) ⚠️

- [X] T014 [P] [US2] Router contract test: a non-admin **member** of the active company `GET /v1/companies/members` → 403 and no roster in the body — add to `apps/api/tessera_api/tests/unit/test_company_members_router.py`
- [X] T015 [P] [US2] Router contract test: an unauthenticated caller `GET /v1/companies/members` → 401 and no roster in the body — add to `apps/api/tessera_api/tests/unit/test_company_members_router.py`

### Implementation for User Story 2

- [X] T016 [US2] Verify/complete the `CompanyAdminContext` gate on the `GET /companies/members` endpoint in `apps/api/tessera_api/routers/companies.py` so that non-admins (403) and unauthenticated callers (401) are rejected before any roster is selected (the dependency is reused from US1's T009 — confirm it short-circuits ahead of the repository call)
- [X] T017 [US2] Add a clean access-denied state to `apps/web/app/users/page.tsx` — when `getCompanyMembers()` returns 403/401, render an access-denied message and never render the roster (depends on T012)

**Checkpoint**: Roster is fully protected — 403 for non-admin members, 401 for unauthenticated, no partial reveal.

---

## Phase 5: User Story 3 - The list is scoped to the admin's own company (Priority: P1)

**Goal**: An admin only ever sees the members of their active company; members belonging solely to another company never appear, even if the admin belongs to multiple companies.

**Independent Test**: As an admin of Company A whose account also exists in Company B, with Company A active, `GET /v1/companies/members` returns exactly Company A's members and no B-only member.

### Tests for User Story 3 (write first, ensure they FAIL) ⚠️

- [X] T018 [US3] Cross-tenant isolation test: an admin authenticated for Company A `GET /v1/companies/members` receives exactly Company A's members; a user who is a member only of Company B never appears, even though that user's `users` record exists — add a `company_members` case to `apps/api/tessera_api/tests/test_tenant_isolation.py` (using the existing harness)

### Implementation for User Story 3

- [X] T019 [US3] Verify the mandatory `WHERE cm.company_id = :company_id` predicate in `SqlCompanyRepository.list_members` (from US1's T008) restricts the join to the active company only, and that `company_id` flows solely from the authenticated `CompanyAdminContext` in the endpoint (T009) — no path/query/body source; make the isolation test in T018 pass

**Checkpoint**: All three stories independently functional; tenant scoping proven by the isolation test.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates and end-to-end validation across the stories.

- [X] T020 [P] Run Ruff + Black on `packages/core` and `apps/api` and fix any findings (Constitution Principle V)
- [X] T021 [P] Run the full backend suite for this feature — `pytest apps/api/tests/unit/test_company_members_router.py`, `pytest apps/api/tests/test_tenant_isolation.py -k company_members`, `pytest packages/core/tests -k company_member` — and the frontend suite `cd apps/web && npx jest user-management`; validate against the known test-env baseline (do not treat the pre-existing API 85% coverage gate or known-failing baseline tests as regressions)
- [X] T022 Execute the manual validation scenarios in `specs/053-user-management/quickstart.md` (Scenarios 1–4) to confirm SC-001…SC-005

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories (provides `CompanyMemberListing` and the `list_members` port method).
- **User Story 1 (Phase 3)**: Depends on Foundational. Ships the working, gated, scoped endpoint + UI (MVP).
- **User Story 2 (Phase 4)**: Depends on Foundational; its implementation confirms/completes the gate wired on US1's endpoint (T009) and adds the frontend denial state on US1's page (T012). Its **tests** (T014/T015) can be written right after Foundational.
- **User Story 3 (Phase 5)**: Depends on Foundational; its verification targets the `WHERE company_id` predicate in US1's repository method (T008). Its **test** (T018) can be written right after Foundational.
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### Story Independence Notes

Because a single read endpoint serves all three P1 stories, US1 necessarily ships the endpoint *with* its admin gate and tenant-scope predicate (shipping an ungated or unscoped roster as an MVP would violate Principle VI). US2 and US3 are therefore each **independently testable** — their contract/isolation tests exercise distinct properties (403/401 access control; cross-tenant scoping) — while their implementation is largely proving and hardening the structural mechanisms US1 puts in place. Any of the three test sets can fail/pass independently.

### Within Each User Story

- Tests written first and FAIL before implementation.
- Domain type / port (Foundational) before repository.
- Repository before endpoint.
- Endpoint before frontend page; badge/type helpers can be parallel with the page scaffolding.

### Parallel Opportunities

- Foundational T002 → T003 → T004 are sequential (same/importing files).
- US1 tests T005, T006, T007 are all `[P]` (different files, different packages).
- US1 helpers T010 (lib) and T011 (badge) are `[P]`; both precede the page T012.
- US2 tests T014, T015 are `[P]`.
- Polish T020, T021 are `[P]`.
- Once Foundational is done, all three stories' test tasks can be authored in parallel.

---

## Parallel Example: User Story 1

```bash
# Author all US1 tests together (different files, expect them to FAIL first):
Task: "Core repo test for list_members in packages/core/tests/test_company_member_listing.py"
Task: "Router contract test (admin 200) in apps/api/tessera_api/tests/unit/test_company_members_router.py"
Task: "Frontend render test in apps/web/tests/user-management.test.tsx"

# Then build US1 frontend helpers in parallel before the page:
Task: "getCompanyMembers + CompanyMember type in apps/web/lib/companies.ts"
Task: "CompanyRoleBadge in apps/web/components/company/CompanyRoleBadge.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. Complete Phase 3 (User Story 1) — the gated, scoped endpoint + `/users` page.
3. **STOP and VALIDATE**: Sign in as an admin and confirm the roster renders with roles.
4. Deploy/demo — this is the complete requested capability.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 → working roster (MVP) → validate → demo.
3. US2 → prove/complete access control (403/401 + denial UX) → validate.
4. US3 → prove tenant scoping (cross-company isolation test) → validate.
5. Polish → lint, full suite against baseline, quickstart scenarios.

---

## Notes

- `[P]` = different files, no dependency on an incomplete task.
- `[Story]` label maps each task to its user story for traceability.
- Verify each test FAILS before implementing (Principle IV).
- `company_id` MUST originate only from the authenticated `CompanyAdminContext` — never from path, query, or body (Principle VI).
- Commit after each task or logical group.
