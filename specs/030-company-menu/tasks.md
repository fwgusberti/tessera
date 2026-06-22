---
description: "Task list for Company Menu feature implementation"
---

# Tasks: Company Menu

**Input**: Design documents from `/specs/030-company-menu/`

**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/api.md ✓, quickstart.md ✓

**Tests**: TDD required — backend unit + integration tests AND frontend component tests (per Constitution IV in plan.md).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new project infrastructure is required. All dependencies, DB tables, and repositories are already in place. This phase establishes the one new API response schema.

- [X] T001 Add `CompanyMeResponse` Pydantic schema (list of `{id, name, role}`) to `apps/api/tessera_api/routers/companies.py` (or a shared schemas module if one exists)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend endpoint and React context that ALL user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

> **TDD — write tests FIRST, verify they FAIL before implementing T004**

- [X] T002 [P] Write unit tests (expect failure) for GET /v1/companies/me (authenticated, unauthenticated, empty-membership, sorted-by-name cases) in `apps/api/tests/unit/test_company_router.py`
- [X] T003 [P] Write integration test (expect failure) for GET /v1/companies/me contract (status 200, shape `{companies:[{id,name,role}]}`, status 401) in `apps/api/tests/integration/test_companies.py`
- [X] T004 Implement GET /v1/companies/me endpoint in `apps/api/tessera_api/routers/companies.py` using `require_user`, `list_memberships_for_user`, `get_by_id`, sorted by name; verify T002 + T003 now pass
- [X] T005 [P] Add `getMyCompanies()` fetch helper (calls GET /v1/companies/me, returns `CompanyEntry[]`) in `apps/web/lib/companies.ts`
- [X] T006 [P] Implement `CompanyContext` + `CompanyProvider` in `apps/web/lib/company.tsx` — loads on `status === "authenticated"`, reads/writes `tessera_active_company_id` in `localStorage`, exposes `companies`, `activeCompany`, `setActiveCompany`, `createAndSetActive`, `reloadCompanies`
- [X] T007 Wrap `children` in `app/layout.tsx` with `CompanyProvider` (inside existing `AuthProvider`) in `apps/web/app/layout.tsx`

**Checkpoint**: Backend endpoint is live; CompanyContext is wired into the app tree — user story work can now begin.

---

## Phase 3: User Story 1 — View Current Company and Switch Companies (Priority: P1) 🎯 MVP

**Goal**: Authenticated users can see their active company in the NavBar and switch between companies via a dropdown (or see a static name when only one company exists).

**Independent Test**: Open NavBar as a single-company user → company name visible, no switcher. Open NavBar as a multi-company user → dropdown shows all companies; select one → active company updates and persists on page reload.

> **TDD — write tests FIRST, verify they FAIL before implementing T009**

### Tests for User Story 1

- [X] T008 [US1] Write component tests (expect failure) for CompanyMenu covering: 0-company (prompt shown), 1-company (static name, no dropdown), 2+-company (button opens dropdown, active item distinguished, Escape/outside-click closes) in `apps/web/tests/company-menu.test.tsx`

### Implementation for User Story 1

- [X] T009 [US1] Implement `CompanyMenu` component in `apps/web/components/company/CompanyMenu.tsx` — 0/1/multi-company display logic, `setActiveCompany` on selection, Escape + outside-click close; verify T008 passes
- [X] T010 [US1] Integrate `CompanyMenu` into `NavBar` desktop left-side (between logo and nav links) and inside the mobile menu in `apps/web/components/NavBar.tsx`
- [X] T011 [P] [US1] Extend NavBar tests with company menu presence cases (desktop + mobile) in `apps/web/tests/navbar.test.tsx`

**Checkpoint**: User Story 1 fully functional — company name visible, switching works, active company persists across reloads.

---

## Phase 4: User Story 2 — Create a New Company from the Menu (Priority: P2)

**Goal**: Authenticated users can open a modal directly from the company menu to create a new company; on success the new company becomes active.

**Independent Test**: Open company menu → select "Create new company" → modal appears → submit valid name → new company in list and active. Submit empty name → inline error → modal stays open.

> **TDD — write tests FIRST, verify they FAIL before implementing T013**

### Tests for User Story 2

- [X] T012 [US2] Add `CreateCompanyModal` component tests (expect failure) for: modal renders on trigger, valid submit calls `createAndSetActive` + closes, empty name shows inline error, stays open on failure in `apps/web/tests/company-menu.test.tsx`

### Implementation for User Story 2

- [X] T013 [US2] Implement `CreateCompanyModal` in `apps/web/components/company/CreateCompanyModal.tsx` — name (required), industry + team_size (optional select), calls `companyContext.createAndSetActive()`, inline error on failure, closes on success; verify T012 passes
- [X] T014 [US2] Add "Create new company" option to `CompanyMenu` that opens `CreateCompanyModal` in `apps/web/components/company/CompanyMenu.tsx`

**Checkpoint**: User Stories 1 + 2 both independently functional.

---

## Phase 5: User Story 3 — Access Company Settings (Priority: P3)

**Goal**: Admin users can navigate to company settings directly from the company menu; non-admins do not see the option.

**Independent Test**: Open company menu as admin → "Company settings" visible → click → navigates to `/settings/company`. Open as non-admin → option absent.

### Implementation for User Story 3

- [X] T015 [P] [US3] Create `/settings/company` stub page rendering heading "Company Settings" and a placeholder note in `apps/web/app/settings/company/page.tsx`
- [X] T016 [US3] Add admin-only "Company settings" `<Link href="/settings/company">` to `CompanyMenu` (visible only when `activeCompany?.role === "admin"`) in `apps/web/components/company/CompanyMenu.tsx`

**Checkpoint**: All three user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, accessibility, code quality, and final validation.

- [X] T017 Handle no-company state in `CompanyMenu` (FR-008) — when `companies` is empty after load, render "Create or join a company" prompt (link to `/register/company` or open `CreateCompanyModal`) in `apps/web/components/company/CompanyMenu.tsx`
- [X] T018 [P] Verify mobile responsive layout: confirm all `CompanyMenu` and `NavBar` tap targets are ≥ 44×44 px on viewport ≤ 768 px; adjust Tailwind classes as needed
- [X] T019 [P] Run Ruff + Black on all modified Python files (`apps/api/tessera_api/routers/companies.py`, test files) and fix any violations
- [X] T020 Run all quickstart.md validation scenarios (S1–S8) manually and confirm expected results

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **User Stories (Phases 3–5)**: All depend on Phase 2 completion
  - US1 (Phase 3): no story dependencies
  - US2 (Phase 4): depends on Phase 3 (CompanyMenu must exist to wire modal into it)
  - US3 (Phase 5): depends on Phase 3 (CompanyMenu must exist to add settings link)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### Within Each User Story

- Tests (TDD) MUST be written and confirmed FAILING before implementation
- Context/API helper before components
- Components before NavBar integration
- Core implementation before modal/settings integration

### Parallel Opportunities

- T002 and T003 (both test files, Phase 2) — write concurrently
- T005 and T006 (different files, Phase 2) — implement concurrently after T004
- T011 and T010 (different files, Phase 3) — extend tests concurrently with NavBar integration
- T015 and T016 (different files, Phase 5) — stub page independent of menu wiring
- T018, T019 (different concerns, Phase 6) — run concurrently

---

## Parallel Example: Phase 2 (Foundational)

```bash
# Parallel test writing (Phase 2 TDD setup):
Task T002: Write unit tests for GET /v1/companies/me in apps/api/tests/unit/test_company_router.py
Task T003: Write integration test for GET /v1/companies/me in apps/api/tests/integration/test_companies.py

# After T004 (endpoint done), parallel frontend foundation:
Task T005: Add getMyCompanies() in apps/web/lib/companies.ts
Task T006: Implement CompanyContext + CompanyProvider in apps/web/lib/company.tsx
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T007) — CRITICAL, blocks all stories
3. Complete Phase 3: User Story 1 (T008–T011)
4. **STOP and VALIDATE**: authenticated user sees company in NavBar, can switch (S1, S2 from quickstart.md)
5. Deploy/demo if ready

### Incremental Delivery

1. Phase 1 + 2 → Backend endpoint live, CompanyContext wired
2. Phase 3 (US1) → Company name visible, switching works → **MVP**
3. Phase 4 (US2) → In-menu company creation works
4. Phase 5 (US3) → Admin settings link works
5. Phase 6 → Edge cases, mobile polish, quality gates

---

## Notes

- [P] tasks = different files, no dependencies between them
- [Story] label maps task to specific user story for traceability
- TDD is required per Constitution IV: write and confirm FAILING tests before each implementation
- Use `@pytest.mark.anyio` (not `@pytest.mark.asyncio`) in the API package tests (see project memory)
- Use `fastapi.testclient.TestClient` (sync) for integration tests, not `httpx.ASGITransport`
- Module-level imports in routers (not deferred) for test patchability
- Tailwind: slate-* neutrals, indigo-600 primary — no blue-* or gray-*
- Commit after each completed task or logical group
