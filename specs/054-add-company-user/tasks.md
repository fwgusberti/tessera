# Tasks: Add User on the Company User Management Page

**Input**: Design documents from `/specs/054-add-company-user/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: INCLUDED — TDD is NON-NEGOTIABLE per the constitution (Principle IV) and the plan's Constitution Check. Every test task below is written to FAIL first, then made to pass.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

Three-package layout (unchanged): `packages/core/tessera_core` (domain + ports),
`apps/api/tessera_api` (FastAPI adapters/routers), `apps/web` (Next.js). Paths below
are repository-relative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the branch baseline before schema and code changes.

- [X] T001 Confirm current migration head is `0014` (so `0015` chains correctly) by running `uv run alembic -c db/alembic.ini heads` from repo root and verifying no local schema drift.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The one schema change this feature requires — `invitations.role` plus the pending-uniqueness index — and the domain/adapter plumbing that carries the role. Blocks US1 (invite) and US3 (role); US2 (direct add) does not read this but shares the same repositories.

**⚠️ CRITICAL**: No user story work should begin until this phase is complete.

- [X] T002 Write FAILING core test that an `Invitation` persists and round-trips `role` through the DB (create with `role=CompanyRole.ADMIN` → read back `admin`; default create → `member`) in `packages/core/tests/test_invitation_role.py` (pytest-asyncio, `@pytest.mark.asyncio`).
- [X] T003 Add `role: CompanyRole = CompanyRole.MEMBER` field to the `Invitation` domain model in `packages/core/tessera_core/domain/invitation.py`.
- [X] T004 Add `role` mapped column (`String(20)`, `NOT NULL`, server default `"member"`) to the invitation ORM model in `apps/api/tessera_api/adapters/models/invitation.py`.
- [X] T005 Create migration `db/migrations/versions/0015_invitation_role.py` (`down_revision = "0014"`): up = `ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'member'` on `invitations` + partial unique index `uq_invitation_pending_email` on `(company_id, lower(email)) WHERE status = 'pending'`; down = drop index then column.
- [X] T006 Persist and read `role` in `SqlInvitationRepository` — set it in `create` and `create_bulk`, and map it back in `_invitation_from_model` — in `apps/api/tessera_api/adapters/repositories/invitation.py`. Run T002 to green.

**Checkpoint**: Schema and invitation-role plumbing ready — user stories can begin.

---

## Phase 3: User Story 1 - Admin invites a new person by email (Priority: P1) 🎯 MVP

**Goal**: A company admin can invite a person by email; a pending invitation is created for the active company and the invite is sent, with unambiguous outcome feedback.

**Independent Test**: Sign in as a company admin, open `/users`, enter a fresh valid email, submit, and confirm an "invitation sent" confirmation; a malformed email is rejected with nothing sent; inviting a current member reports "already a member".

### Tests for User Story 1 ⚠️ (write first, ensure they FAIL)

- [X] T007 [P] [US1] Contract tests for `POST /v1/companies/invitations` in `apps/api/tests/unit/test_company_add_user_router.py`: 201 `{"status":"sent",...}` + `invitation.sent` audit on success; 409 `already_member` when email is a current member; 409 `already_invited` when a pending invitation exists (and on partial-index `IntegrityError`); 422 for malformed email (nothing sent); 502 `send_failed` when `send_invitation_email` raises (row created, failure surfaced). (pytest-anyio + `TestClient`)
- [X] T008 [P] [US1] Frontend test for the invite-by-email path in `apps/web/tests/user-management-add.test.tsx`: submitting a valid email calls `inviteCompanyMember` and renders the "invitation sent" confirmation; a malformed email shows a validation message and does not call the API. (Jest/RTL)

### Implementation for User Story 1

- [X] T009 [US1] Add `POST /v1/companies/invitations` to `apps/api/tessera_api/routers/companies.py`: gated by `CompanyAdminContext` (company_id from context only); Pydantic body `{email: EmailStr, role: CompanyRole = MEMBER}`; guard current-member via `get_by_email` + `get_membership`; guard existing pending via `get_pending_for_email`; create invitation, call `send_invitation_email` in try/except mapping failure to 502 `send_failed`; map partial-index `IntegrityError` to 409 `already_invited`; write `invitation.sent` audit. Run T007 to green.
- [X] T010 [P] [US1] Add `inviteCompanyMember(email, role)` + request/response types to `apps/web/lib/companies.ts` (POST `/v1/companies/invitations` via the `api` client).
- [X] T011 [US1] Create `apps/web/components/company/AddUserPanel.tsx` with the invite-by-email mode (email input, submit) and the outcome-message rendering (success / already-member / already-invited / invalid-email / send-failed). (Shared component; extended in US2/US3.)
- [X] T012 [US1] Wire an admin-only "Add user" affordance into `apps/web/app/users/page.tsx` that opens `AddUserPanel`, reusing `AuthGuard`; on invite success show the confirmation. Run T008 to green.

**Checkpoint**: US1 fully functional — an admin can invite by email with clear feedback.

---

## Phase 4: User Story 2 - Admin directly adds an already-registered user (Priority: P1)

**Goal**: A company admin can search the global user directory and directly add an existing user (not yet a member) to the active company immediately, seeing them in the roster with no acceptance step.

**Independent Test**: Sign in as admin, open `/users`, type a couple letters of an existing non-member's name/email, pick them, submit, and confirm they appear in the roster immediately; adding a current member reports "already a member"; a non-existent user reports "no such user".

### Tests for User Story 2 ⚠️ (write first, ensure they FAIL)

- [X] T013 [P] [US2] Adapter test for `search_addable_users(company_id, query, limit)` in `apps/api/tests/unit/test_company_repository_search.py`: matches on `display_name` and `email` (case-insensitive), excludes users already in `company_id`, respects `limit`, returns identity fields only.
- [X] T014 [P] [US2] Contract tests in `apps/api/tests/unit/test_company_add_user_router.py`: `GET /v1/companies/addable-users?q=` → 200 `{"users":[{user_id,display_name,email}]}` excluding current members; empty/short `q` (<2) → 422; `POST /v1/companies/members` → 201 `{"member":{...}}` + `company.member_added` audit; 404 `no_such_user` for an unknown `user_id`; 409 `already_member` when already a member (and on `uq_company_membership` `IntegrityError`); 422 for invalid role.
- [X] T015 [P] [US2] Frontend test for the direct-add path in `apps/web/tests/user-management-add.test.tsx`: typing in the existing-user search calls `searchAddableUsers` (debounced, min length) and renders results; selecting one and submitting calls `addCompanyMember` and appends the returned member to the roster.

### Implementation for User Story 2

- [X] T016 [P] [US2] Add abstract `search_addable_users(company_id: UUID, query: str, limit: int = 20) -> list[CompanyMemberMatch]` to the `CompanyRepository` port in `packages/core/tessera_core/ports/repositories/company.py`.
- [X] T017 [US2] Implement `search_addable_users` in `SqlCompanyRepository` (`apps/api/tessera_api/adapters/repositories/company.py`): `SELECT users … WHERE (email ILIKE :q OR display_name ILIKE :q) AND id NOT IN (SELECT user_id FROM company_memberships WHERE company_id = :company_id) ORDER BY display_name LIMIT :limit`, returning `CompanyMemberMatch`. Run T013 to green.
- [X] T018 [US2] Add `GET /v1/companies/addable-users` to `apps/api/tessera_api/routers/companies.py`: `CompanyAdminContext`-gated, `q` required min-length 2 (else 422), delegates to `search_addable_users(context.company_id, q)`.
- [X] T019 [US2] Add `POST /v1/companies/members` to `apps/api/tessera_api/routers/companies.py`: `CompanyAdminContext`-gated, body `{user_id: UUID, role: CompanyRole = MEMBER}`; 404 `no_such_user` if the user does not exist; `get_membership` guard + `add_membership` with duplicate `IntegrityError` mapped to 409 `already_member`; 201 returns the new member row; write `company.member_added` audit. Run T014 to green.
- [X] T020 [P] [US2] Add `searchAddableUsers(q)` and `addCompanyMember(userId, role)` + types to `apps/web/lib/companies.ts`.
- [X] T021 [US2] Extend `apps/web/components/company/AddUserPanel.tsx` with the add-existing-user mode: a debounced, min-length type-ahead over `searchAddableUsers`, result selection, submit via `addCompanyMember`, and outcome messaging (success / already-member / no-such-user).
- [X] T022 [US2] On direct-add success, append the returned member to the roster in place (no full reload) in `apps/web/app/users/page.tsx`. Run T015 to green.

**Checkpoint**: US1 and US2 both work — admin can invite by email or directly add an existing user.

---

## Phase 5: User Story 3 - Admin chooses the added user's company role (Priority: P2)

**Goal**: When adding by either method, the admin chooses `administrator` or `member` (default `member`); the resulting membership carries that role, including for invited users on acceptance.

**Independent Test**: Add a user (either path) with role `administrator` and confirm the roster shows them as admin; repeat with `member`; confirm the selector defaults to `member`; accept an admin-role invitation and confirm the new member is an administrator.

### Tests for User Story 3 ⚠️ (write first, ensure they FAIL)

- [X] T023 [P] [US3] Core test that invitation acceptance grants `invitation.role` in `apps/api/tests/unit/test_join_grants_invitation_role.py`: accepting an `admin`-role invitation yields a `company_memberships` row with `role="admin"` and response `"role":"admin"`; a `member`/legacy invitation yields `role="member"` (regression guard).
- [X] T024 [P] [US3] Extend contract tests in `apps/api/tests/unit/test_company_add_user_router.py`: `POST /companies/members` with `role="admin"` → member row `role="admin"`; `POST /companies/invitations` with `role="admin"` persists `role="admin"` on the invitation; omitting `role` defaults to `member` on both.
- [X] T025 [P] [US3] Extend `apps/web/tests/user-management-add.test.tsx`: the role selector defaults to `member` and its chosen value is passed to `addCompanyMember`/`inviteCompanyMember`.

### Implementation for User Story 3

- [X] T026 [US3] Change the `method="invitation"` branch of `POST /v1/companies/{company_id}/join` in `apps/api/tessera_api/routers/companies.py` to grant `invitation.role` instead of hard-coded `CompanyRole.MEMBER` (response `"role": invitation.role.value`); leave all other join guards unchanged. Run T023 to green.
- [X] T027 [US3] Add a role selector (Administrator | Member, default Member) to `apps/web/components/company/AddUserPanel.tsx`, feeding both submit paths. Run T024, T025 to green.

**Checkpoint**: All three add capabilities carry the admin-chosen role end-to-end.

---

## Phase 6: User Story 4 - Only admins can add users, scoped to their own company (Priority: P1)

**Goal**: All three endpoints are admin-only and derive `company_id` solely from the authenticated context; non-admins get 403, unauthenticated 401, and every write lands only in the active company.

**Independent Test**: As a non-admin member, confirm the Add-user affordance is absent and the endpoints return 403 with no write; as a multi-company admin, confirm an add lands only in the active company.

### Tests for User Story 4 ⚠️ (write first, ensure they FAIL)

- [X] T028 [P] [US4] Auth-gate contract tests in `apps/api/tests/unit/test_company_add_user_router.py`: non-admin member → 403 (no write) and unauthenticated → 401 for all three endpoints (`GET /companies/addable-users`, `POST /companies/members`, `POST /companies/invitations`).
- [X] T029 [P] [US4] Cross-tenant isolation cases in `apps/api/tests/test_tenant_isolation.py`: admin of Company A `POST /companies/members` creates the membership in A only (verify via `get_membership` on A and B); a user already in Company B can be direct-added to A and the write lands only in A; `GET /companies/addable-users` as A's admin returns identity fields only, excludes A's members, and cannot reveal B's roster.

### Implementation for User Story 4

- [X] T030 [US4] Verify (and correct if needed) that all three endpoints in `apps/api/tessera_api/routers/companies.py` depend on `CompanyAdminContext` and read `company_id` only from the resolved context — never from path or body. Run T028, T029 to green.
- [X] T031 [US4] Ensure the `AddUserPanel` affordance in `apps/web/app/users/page.tsx` renders only for admins of the active company (hidden for non-admin members).

**Checkpoint**: Add capability is admin-only and tenant-scoped across API and UI.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T032 [P] Run Ruff + Black over changed Python (`apps/api`, `packages/core`) and lint/format the changed web files; fix any findings (no exemptions).
- [X] T033 Run the quickstart backend + frontend validation from `specs/054-add-company-user/quickstart.md` and confirm the new tests pass against the known test-env baseline (not the absolute 85% API gate).
- [X] T034 Walk the manual end-to-end scenarios (#1–#7) in `quickstart.md` to confirm the outcome-message matrix (FR-012/SC-007) end-to-end.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup. Blocks US1 and US3 (invitation-role plumbing); US2 shares the repositories.
- **User Stories (Phase 3–6)**: Depend on Foundational.
  - US1 (P1), US2 (P1) are independent of each other. US2 does not need the invitation-role plumbing.
  - US3 (P2) depends on US1/US2 having created the endpoint request schemas and `AddUserPanel`, and on the invitation-role plumbing (T003–T006) for the acceptance change.
  - US4 (P1) verifies gating that US1/US2 endpoints already apply; best run once those endpoints exist.
- **Polish (Phase 7)**: Depends on all desired stories.

### Within Each User Story

- Tests are written first and MUST FAIL before implementation.
- Port method before adapter; adapter before endpoint; endpoint before frontend wiring.
- `lib/companies.ts` client functions before the `AddUserPanel` code that calls them.

### Parallel Opportunities

- US1 and US2 can proceed in parallel after Phase 2 (different endpoints; US2 touches `packages/core` port + company adapter, US1 does not).
- Within a story, all `[P]` test tasks can be written together; `[P]` client/port tasks in different files run in parallel.
- Shared files force serialization: `apps/api/tessera_api/routers/companies.py` (T009, T018, T019, T026, T030), `apps/web/components/company/AddUserPanel.tsx` (T011, T021, T027), and `apps/web/app/users/page.tsx` (T012, T022, T031) are edited by multiple tasks and are NOT `[P]` among themselves.

---

## Parallel Example: User Story 2

```bash
# Write US2 tests together (different files):
Task: "Adapter test for search_addable_users in apps/api/tests/unit/test_company_repository_search.py"
Task: "Endpoint contract tests in apps/api/tests/unit/test_company_add_user_router.py"
Task: "Frontend direct-add test in apps/web/tests/user-management-add.test.tsx"

# Parallel implementation (different files):
Task: "Add search_addable_users to the CompanyRepository port in packages/core/.../ports/repositories/company.py"
Task: "Add searchAddableUsers/addCompanyMember to apps/web/lib/companies.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 Setup → Phase 2 Foundational (migration + invitation-role plumbing).
2. Phase 3 US1 (invite by email).
3. **STOP and VALIDATE**: an admin can invite by email with clear feedback.
4. Deploy/demo if ready.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 → invite by email (MVP).
3. US2 → direct-add existing user.
4. US3 → role choice on both paths + role-on-acceptance.
5. US4 → confirm admin-only + tenant-scoped gating.
6. Polish → lint/format + quickstart validation.

---

## Notes

- [P] = different files, no dependencies. [Story] label maps each task to a user story for traceability.
- Every test task is written to FAIL first (TDD, Principle IV) and then made green by the referenced implementation task.
- New code is fully covered; validate the suite against the recorded test-env baseline, not the unreachable absolute API coverage gate (see plan Constitution Check IV).
- Commit after each task or logical group.
