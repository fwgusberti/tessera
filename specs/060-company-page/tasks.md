# Tasks: Company Page

**Input**: Design documents from `/specs/060-company-page/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/company-profile.md, quickstart.md

**Tests**: Included — TDD is non-negotiable per Constitution IV. Within each story, test tasks are written first and MUST fail before implementation begins.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Monorepo (per plan.md): backend in `apps/api/` + `packages/core/`, frontend in `apps/web/`. No new packages, no migrations.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Extract the shared option lists both the onboarding form and the new company page will consume. No project initialization needed — the monorepo, tooling, and routes already exist.

- [X] T001 Create `apps/web/lib/companyOptions.ts` exporting `INDUSTRIES` and `TEAM_SIZES`, moved verbatim from the module-local constants in `apps/web/components/onboarding/CompanyForm.tsx`
- [X] T002 Update `apps/web/components/onboarding/CompanyForm.tsx` to import `INDUSTRIES` and `TEAM_SIZES` from `@/lib/companyOptions` and delete the local copies; run the existing onboarding tests to confirm no regression (depends on T001)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

**No foundational tasks required.** Everything the stories need already exists: `CompanyMemberContext`/`CompanyAdminContext` auth dependencies, the companies router, `SqlCompanyRepository`, `write_audit`, `CompanyProvider` with `reloadCompanies()`, and the routed `/settings/company` placeholder. The `companies` table already has every column (no migrations).

**Checkpoint**: Setup complete — user story implementation can begin.

---

## Phase 3: User Story 1 - View company information (Priority: P1) 🎯 MVP

**Goal**: Any signed-in member can open the company page and see the active company's name, industry, team size, and creation date — with explicit "Not provided" for empty optional fields, and never another company's data.

**Independent Test**: Sign in as a plain member, open the company dropdown → "Company", and confirm the profile fields render accurately (nulls show "Not provided"); confirm the API rejects unauthenticated and non-member access.

### Tests for User Story 1 (write first — MUST fail before implementation) ⚠️

- [X] T003 [P] [US1] Write failing unit tests for `GET /v1/companies/current` in `apps/api/tests/unit/test_company_profile_router.py` (new file): 200 with full profile (id, name, industry, team_size, created_at) and `role: "admin"` for an admin caller; 200 with `role: "member"` for a plain member; `industry`/`team_size` returned as `null` when unset. Use the `@pytest.mark.anyio` marker and module-level-import patching per repo convention.
- [X] T004 [P] [US1] Write failing integration tests (view slice) in `apps/api/tests/integration/test_company_profile.py` (new file, sync `fastapi.testclient.TestClient`): member GET returns only the token's company (isolation test 1); revoked-membership token → 403 `not_a_member` (isolation test 2); unauthenticated → 401 (FR-011); company-unscoped (select-kind) token → 403 `credential_not_scoped`.
- [X] T005 [P] [US1] Write failing Vitest view-mode tests in `apps/web/tests/company-page.test.tsx` (new file): page renders name, industry, team size, and formatted creation date from `getCurrentCompany()`; `null` industry/team_size render the literal text "Not provided" (FR-003); creation date is display-only.
- [X] T006 [P] [US1] Extend `apps/web/tests/company-menu.test.tsx` with a failing test: the "Company" link to `/settings/company` is visible to non-admin members (FR-001).

### Implementation for User Story 1

- [X] T007 [US1] Add `CompanyProfileResponse` (id, name, industry, team_size, created_at, role) and `GET /v1/companies/current` guarded by `CompanyMemberContext` to `apps/api/tessera_api/routers/companies.py`; company id comes only from the auth context, `role` is the caller's membership role (contract: contracts/company-profile.md). Makes T003/T004 pass.
- [X] T008 [P] [US1] Add `CompanyProfile` interface and `getCurrentCompany(): Promise<CompanyProfile>` to `apps/web/lib/companies.ts` (types per data-model.md).
- [X] T009 [US1] Rewrite `apps/web/app/settings/company/page.tsx` replacing the placeholder: client component behind `AuthGuard`, fetches `getCurrentCompany()` once, renders a definition-list profile card (name, industry, team size, formatted creation date) with "Not provided" in muted slate for null optionals; slate/indigo styling per the Users-page pattern. Makes T005 pass. (depends on T008)
- [X] T010 [P] [US1] In `apps/web/components/company/CompanyMenu.tsx`, remove the admin gate on the `/settings/company` link and relabel it "Company" so every member sees it. Makes T006 pass.
- [X] T011 [US1] Verify US1: `cd apps/api && uv run pytest tests/unit/test_company_profile_router.py tests/integration/test_company_profile.py --no-cov` and `cd apps/web && npx vitest run tests/company-page.test.tsx tests/company-menu.test.tsx` — all green.

**Checkpoint**: User Story 1 fully functional — every member can view the company profile. Deployable MVP.

---

## Phase 4: User Story 2 - Edit company information (Priority: P2)

**Goal**: A company admin can edit name/industry/team size in place, save with validation, see the change everywhere immediately (including the nav company menu), and every successful change is audited.

**Independent Test**: Sign in as an admin, edit the company name on `/settings/company`, save; confirm the page and the company menu show the new name, a fresh GET returns it, and an audit record `company.updated` exists with the changed fields.

### Tests for User Story 2 (write first — MUST fail before implementation) ⚠️

- [X] T012 [P] [US2] Extend `apps/api/tests/unit/test_company_repo.py` with failing tests for `update_details`: persists all three fields, bumps `updated_at`, returns `None` for a nonexistent company id, and leaves a second seeded company untouched (isolation test 4).
- [X] T013 [P] [US2] Add failing PATCH unit tests to `apps/api/tests/unit/test_company_profile_router.py`: happy path returns the saved profile and calls `write_audit` with action `company.updated`, entity `company`, and a changed-fields map containing only actually-changed fields (FR-010); 422 `invalid_name` for empty, whitespace-only, and >255-char names (FR-005); 422 `invalid_team_size` for a value outside `VALID_TEAM_SIZES`; `null` industry/team_size clear the stored values; 404 when the repository returns `None`.
- [X] T014 [P] [US2] Add failing integration tests (edit slice) to `apps/api/tests/integration/test_company_profile.py`: admin PATCH persists across a fresh GET (US2 scenario 1); an audit row is written with actor id, company id, and changed fields (SC-004); with two companies seeded, an update by A's admin leaves B's row untouched.
- [X] T015 [P] [US2] Add failing Vitest edit-mode tests to `apps/web/tests/company-page.test.tsx`: Edit button shown when `role === "admin"`; form prefilled with current values using the shared INDUSTRIES/TEAM_SIZES selects; successful save returns to view mode with response values and calls `reloadCompanies()` (FR-007); Cancel discards changes and restores original values (FR-006); empty name blocked client-side with a message (FR-005); failed save (rejected promise / 422) stays in edit mode with entered values intact and shows an error banner (edge case).

### Implementation for User Story 2

- [X] T016 [US2] Add abstract method `update_details(company_id: UUID, *, name: str, industry: str | None, team_size: str | None) -> Company | None` to the `CompanyRepository` port in `packages/core/tessera_core/ports/repositories/company.py`.
- [X] T017 [US2] Implement `SqlCompanyRepository.update_details` in `apps/api/tessera_api/adapters/repositories/company.py`: load `WHERE id = :company_id`, apply all three fields, flush, return the mapped domain `Company`; return `None` when no row matches. Makes T012 pass. (depends on T016)
- [X] T018 [US2] Add `UpdateCompanyRequest` (name required 1–255 non-blank after trim; industry ≤100 or null; team_size ∈ `VALID_TEAM_SIZES` or null — same codes as `POST /v1/companies`) and `PATCH /v1/companies/current` guarded by `CompanyAdminContext` to `apps/api/tessera_api/routers/companies.py`: call `update_details`, write a `company.updated` audit record via `write_audit` with metadata `{"company_id": ..., "changed": {field: {"from": old, "to": new}}}` for changed fields only, return the saved profile as `CompanyProfileResponse` with `role: "admin"`. Makes T013/T014 pass. (depends on T017)
- [X] T019 [P] [US2] Add `UpdateCompanyData` interface and `updateCurrentCompany(data: UpdateCompanyData): Promise<CompanyProfile>` to `apps/web/lib/companies.ts`.
- [X] T020 [US2] Add edit mode to `apps/web/app/settings/company/page.tsx`: Edit button rendered only when the fetched profile's `role === "admin"`; form prefilled with current values using `INDUSTRIES`/`TEAM_SIZES` from `@/lib/companyOptions`; client-side trim + empty-name validation; Save → `updateCurrentCompany()` → swap in the response atomically, return to view mode, call `reloadCompanies()`; Cancel discards form state; on failure stay in edit mode with entered values and an error banner rendering server 422 messages. Makes T015 pass. (depends on T009, T019, T001)
- [X] T021 [US2] Verify US2: `cd apps/api && uv run pytest tests/unit/test_company_profile_router.py tests/unit/test_company_repo.py tests/integration/test_company_profile.py --no-cov` and `cd apps/web && npx vitest run tests/company-page.test.tsx` — all green.

**Checkpoint**: User Stories 1 AND 2 work — members view, admins edit with audit and immediate propagation.

---

## Phase 5: User Story 3 - Non-administrators cannot edit (Priority: P3)

**Goal**: Non-admin members get a strictly read-only page, and any forged change submission is refused server-side with data unchanged.

**Independent Test**: Sign in as a plain member: the page shows no edit controls; a direct `PATCH /v1/companies/current` with the member's token returns 403 `forbidden` and a follow-up GET proves the stored values are unchanged.

### Tests for User Story 3 (write first — MUST fail before implementation) ⚠️

> Note: the refusal tests target the PATCH endpoint, so this story's tests require US2's endpoint to exist (see Dependencies). The read-only-UI test depends only on US1's page.

- [X] T022 [P] [US3] Add a unit test to `apps/api/tests/unit/test_company_profile_router.py`: PATCH by a non-admin member → 403 `forbidden` and the repository update method is never called (FR-008).
- [X] T023 [P] [US3] Add an integration test to `apps/api/tests/integration/test_company_profile.py`: member-token PATCH → 403 `forbidden`, then a follow-up GET proves stored values are unchanged (isolation test 3, SC-003).
- [X] T024 [P] [US3] Add a Vitest test to `apps/web/tests/company-page.test.tsx`: when the profile's `role === "member"`, no Edit button or form controls are rendered — page is read-only (US3 scenario 1).

### Implementation for User Story 3

- [X] T025 [US3] Confirm and close any gaps the US3 tests reveal: server enforcement is the `CompanyAdminContext` dependency on PATCH in `apps/api/tessera_api/routers/companies.py` (no handler-level role check needed); client gating is the `role === "admin"` conditional in `apps/web/app/settings/company/page.tsx`. Fix either side if a T022–T024 test fails.
- [X] T026 [US3] Verify US3: `cd apps/api && uv run pytest tests/unit/test_company_profile_router.py tests/integration/test_company_profile.py --no-cov` and `cd apps/web && npx vitest run tests/company-page.test.tsx` — all green.

**Checkpoint**: All user stories independently functional; SC-003 enforcement proven at both layers.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates, regression safety, and end-to-end validation per quickstart.md.

- [X] T027 [P] Run quality gates on touched Python: `cd apps/api && uv run ruff check . && uv run black --check .` (and `packages/core` if its tooling applies); fix any findings.
- [X] T028 [P] Full scoped test run per quickstart.md: all three API suites with `--no-cov` plus both web suites; then a full `make test` to confirm no regressions beyond the documented pre-existing baseline (test_ports, migration_0002, tessera_mcp, repo-wide coverage gate).
- [X] T029 Execute the manual scenarios in `specs/060-company-page/quickstart.md`: US1 member view (incl. "Not provided"), US2 admin edit + nav-name propagation + audit row via psql, US3 forged PATCH refusal, multi-company tenant isolation, signed-out 401/redirect.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately. Only blocks T020 (edit form uses the shared options).
- **Foundational (Phase 2)**: Empty — nothing blocks the stories.
- **User Story 1 (Phase 3)**: Can start immediately. No dependency on other stories.
- **User Story 2 (Phase 4)**: Builds on US1's GET endpoint (T007), page (T009), and Setup (T001). Backend tasks T012–T014, T016–T018 can start any time; T020 needs T009 + T001.
- **User Story 3 (Phase 5)**: Refusal tests (T022, T023) need US2's PATCH endpoint (T018); the read-only UI test (T024) needs only US1's page (T009).
- **Polish (Phase 6)**: After all desired stories complete.

### Within Each User Story

- Tests MUST be written and observed failing before implementation tasks begin (Constitution IV)
- Port before adapter before router (T016 → T017 → T018)
- API client functions before page changes (T008 → T009; T019 → T020)
- Verification task closes each story

### Parallel Opportunities

- **US1 tests**: T003, T004, T005, T006 — four different files, all parallel
- **US1 implementation**: T008 and T010 parallel with T007; T009 after T008
- **US2 tests**: T012, T013, T014, T015 — all parallel (T013/T014 extend files created in US1, which is complete by then)
- **US2 implementation**: T019 parallel with the T016→T017→T018 chain
- **US3 tests**: T022, T023, T024 — all parallel
- **Polish**: T027 and T028 parallel

## Parallel Example: User Story 1

```bash
# Launch all US1 test-writing tasks together:
Task: "T003 unit tests for GET /v1/companies/current in apps/api/tests/unit/test_company_profile_router.py"
Task: "T004 integration view tests in apps/api/tests/integration/test_company_profile.py"
Task: "T005 Vitest view-mode tests in apps/web/tests/company-page.test.tsx"
Task: "T006 company-menu link test in apps/web/tests/company-menu.test.tsx"

# Then implementation (T007 backend, T008 web lib, T010 menu in parallel; T009 after T008)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Skip Phase 2 (empty)
3. Complete Phase 3: US1 tests → implementation → T011 verification
4. **STOP and VALIDATE**: run quickstart US1 manual scenario — every member can view the company profile
5. Deploy/demo if ready

### Incremental Delivery

1. Setup → US1 (view page live — MVP)
2. US2 (admin editing + audit + propagation) → validate → deploy
3. US3 (non-admin refusal proven at both layers) → validate → deploy
4. Polish: quality gates, full regression check, manual quickstart pass

### Notes

- No migrations, no new dependencies, no new routes — the page slot and link already exist
- Tenant isolation is structural: neither endpoint accepts a company id from the client
- Known pre-existing test failures (test_ports, migration_0002, tessera_mcp) and the repo-wide coverage gate are NOT this feature's signal — use the scoped commands in quickstart.md
