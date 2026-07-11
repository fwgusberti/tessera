# Tasks: Company Selection at Sign-In

**Input**: Design documents from `/specs/059-fix-tenant-selection/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/company-selection.md, quickstart.md

**Tests**: INCLUDED — Constitution Principle IV (TDD, non-negotiable) requires all new behavior written test-first in Vitest. Within each phase, test tasks MUST be written and observed failing before the corresponding implementation tasks.

**Organization**: Tasks are grouped by user story. Web-only feature — every path is under `apps/web/`; there are no backend, core, or migration tasks.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task belongs to (US1, US2, US3)

## Path Conventions

Monorepo web app: source in `apps/web/app/` (routes) and `apps/web/lib/` (auth/api modules), tests in `apps/web/tests/` (Vitest + Testing Library, jsdom). Run tests with `cd apps/web && npx vitest run`.

---

## Phase 1: Setup

**Purpose**: Confirm the working baseline so later failures are attributable to this feature. No new dependencies, scaffolding, or config are needed (plan.md: no new packages).

- [X] T001 Confirm the existing web suite baseline is green: `cd apps/web && npm install && npx vitest run`; record any pre-existing failures before making changes — baseline: 308 passed, 1 pre-existing failure (`tests/document-detail-modernized.test.tsx` breadcrumb assertion, unrelated)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Token-kind awareness in the shared types and JWT decoding — every user story reads `tokenKind`/`companyId` from the auth context, so this MUST land first.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Extend shared types in `apps/web/lib/types.ts`: add `export type TokenKind = "full" | "select" | "onboarding"`; add optional `tenant_selection_required?: boolean` to `LoginResponse`; add `tokenKind: TokenKind` and `companyId: string | null` to `AuthUser` (per data-model.md)
- [X] T003 Add failing tests to `apps/web/tests/auth.test.tsx`: `decodeJwtUser` surfaces `tokenKind` from the `token_kind` claim and `companyId` from `company_id`; `tokenKind` defaults to `"full"` when the claim is absent (legacy tokens); `companyId` is `null` on non-full tokens
- [X] T004 Implement token-kind decoding in `apps/web/lib/auth.tsx`: extend `decodeJwtUser` to parse `token_kind` and `company_id` into `AuthUser.tokenKind`/`AuthUser.companyId` (default `"full"` / `null`); verify T003 tests pass

**Checkpoint**: Auth context exposes `tokenKind`/`companyId` on every state update (login, refresh, restore) — user stories can now begin.

---

## Phase 3: User Story 1 - Multi-company user completes sign-in by choosing a company (Priority: P1) 🎯 MVP

**Goal**: A multi-company login lands on a `/select-company` picker listing companies (name + role); picking one exchanges the select token for a full-scoped pair via `POST /v1/auth/select-tenant` and enters the app. Single-company and zero-company logins are unchanged.

**Independent Test**: Sign in as a user with two memberships → picker lists both companies with role badges → pick one → main screens load that company's data. Sign in as a one-company user → no picker (quickstart scenarios 1–2).

### Tests for User Story 1 (write first, observe failing) ⚠️

- [X] T005 [P] [US1] Add failing tests to `apps/web/tests/auth.test.tsx`: `selectTenant(companyId)` POSTs `{ company_id }` to `/v1/auth/select-tenant` with the current access token via raw fetch (no auth-injection retry), persists the returned pair through the existing `writeStorage`/`updateState` path, and leaves stored tokens/state untouched when the call fails; `login()` resolves to `{ tenantSelectionRequired: true }` when the response carries `tenant_selection_required` and `false` otherwise (contract B2)
- [X] T006 [P] [US1] Add failing tests to `apps/web/tests/login.test.tsx`: multi-company login (`tenantSelectionRequired: true`) routes to `/select-company?redirect=<sanitized dest>` preserving the `redirect` query param; single-company login still routes straight to the destination (FR-003 / SC-004)
- [X] T007 [P] [US1] Create `apps/web/tests/select-company.test.tsx` with failing tests for the picker happy path per contract B1: renders one action per company showing name + role badge from `GET /v1/companies/me`; picking a company calls `selectTenant` and navigates to the sanitized `redirect` (default `/`); unauthenticated session redirects to `/login`; `tokenKind === "full"` redirects to `redirect`/`/`; `tokenKind === "onboarding"` redirects to `/onboarding`; `redirect` sanitization matches `/login` (must start with `/`, not `//`)

### Implementation for User Story 1

- [X] T008 [US1] Add `authSelectTenant(accessToken, companyId)` raw-fetch helper in `apps/web/lib/api.ts` calling `POST /v1/auth/select-tenant`, typed to return the token-pair shape (`RefreshResponse`), surfacing the error `code` on failure like the other auth endpoints
- [X] T009 [US1] Extend `AuthProvider` in `apps/web/lib/auth.tsx`: add `selectTenant(companyId)` to `AuthContextValue` (calls T008 helper, atomically swaps the stored token pair + context refs, no state change on failure); change `login()` to return `{ tenantSelectionRequired: boolean }` derived from the response flag / decoded token kind; verify T005 tests pass
- [X] T010 [US1] Create `apps/web/app/select-company/page.tsx`: client page that fetches `GET /v1/companies/me` via the existing `getMyCompanies()` (`apps/web/lib/companies.ts`), renders the company list with name + role badge, calls `selectTenant` on pick, then navigates to the sanitized `redirect` param or `/`; implements the unauthenticated→`/login`, `full`→app, `onboarding`→`/onboarding` redirects (contract B1); verify T007 happy-path tests pass
- [X] T011 [US1] Update `apps/web/app/login/page.tsx`: when `login()` returns `tenantSelectionRequired: true`, route to `/select-company?redirect=<encoded dest>` instead of the destination; verify T006 tests pass

**Checkpoint**: Multi-company sign-in works end-to-end through the picker; single-/zero-company flows unchanged. MVP deliverable — quickstart scenarios 1–2 pass manually.

---

## Phase 4: User Story 2 - Unscoped session is redirected to selection instead of erroring (Priority: P2)

**Goal**: Any authenticated `select`-kind session reaching a protected page (restore, bookmark, navigation) is redirected to `/select-company?redirect=<path>`; any 403 `credential_not_scoped` API response triggers the same redirect centrally, and the raw backend message is never rendered (FR-004, FR-005, SC-002).

**Independent Test**: With a stored unscoped session, open `http://localhost:3000/spaces` directly → redirected to `/select-company?redirect=%2Fspaces`; completing selection lands on `/spaces` (quickstart scenarios 3–4).

### Tests for User Story 2 (write first, observe failing) ⚠️

- [X] T012 [P] [US2] Create `apps/web/tests/tenant-guard.test.tsx` with failing tests per contract B4: authenticated `select`-kind session on a protected path → `router.replace("/select-company?redirect=" + encodeURIComponent(pathname))` and renders nothing; exempt paths (`/login`, `/register`, `/select-company`, `/forgot-password`, `/reset-password`) pass through; `full` and `onboarding` token kinds pass through; unauthenticated status passes through
- [X] T013 [P] [US2] Add failing tests to `apps/web/tests/api.test.tsx`: a 403 response with error code `credential_not_scoped` invokes the `onTenantSelectionRequired` config callback and throws an `ApiError` with friendly copy (e.g. "Please choose a company to continue."); assert the literal string "Credential is not scoped to a tenant" never appears in the thrown error message (SC-002); other 403 codes behave as before

### Implementation for User Story 2

- [X] T014 [US2] Add `onTenantSelectionRequired?(): void` to `ApiConfig` in `apps/web/lib/api.ts` and make `request()` intercept any 403 whose error `code` is `credential_not_scoped`: invoke the callback, then throw a friendly `ApiError` that never carries the server's raw message (contract B3); verify T013 tests pass
- [X] T015 [US2] Add `TenantGuard` client component to `apps/web/lib/auth-guard.tsx` per contract B4 (redirect `select`-kind sessions off non-exempt paths, render nothing while redirecting), and exempt `/select-company` in the existing `OnboardingGuard`; verify T012 tests pass
- [X] T016 [US2] Wire it up: mount `TenantGuard` inside `AuthProvider` in `apps/web/app/layout.tsx` (next to `OnboardingGuard`), and have `AuthProvider` in `apps/web/lib/auth.tsx` pass an `onTenantSelectionRequired` callback that navigates to `/select-company` when configuring the API client

**Checkpoint**: Unscoped sessions can never reach broken pages, and `credential_not_scoped` is intercepted globally — US1 and US2 both work independently.

---

## Phase 5: User Story 3 - Selection failures are handled gracefully (Priority: P3)

**Goal**: Suspended-company and revoked-membership selection failures show mapped, human-readable messages, keep the remaining companies selectable (with a re-fetched list), and the picker offers sign-out that fully clears the session (FR-006, FR-008).

**Independent Test**: Suspend one of the user's two companies, sign in, pick the suspended company → clear "unavailable" message appears and the other company still works; Sign out from the picker returns to `/login` with storage cleared (quickstart scenarios 5–7).

### Tests for User Story 3 (write first, observe failing) ⚠️

- [X] T017 [P] [US3] Add failing failure-path tests to `apps/web/tests/select-company.test.tsx`: picking a company that fails with code `company_suspended` shows the "company unavailable" copy, keeps the picker interactive, and re-fetches `GET /v1/companies/me`; code `not_a_member` shows the "no longer have access" copy and the refreshed list drops the revoked company while others stay selectable; an unknown error code shows generic copy; a Sign out action calls `logout()` and routes to `/login`; assert the raw string "Credential is not scoped to a tenant" is never rendered by the page (SC-002)

### Implementation for User Story 3

- [X] T018 [US3] Add failure handling to `apps/web/app/select-company/page.tsx`: map `ApiError.code` → copy (`company_suspended` → "This company's account is suspended…", `not_a_member` → "You no longer have access to this company…", other → generic message per data-model.md validation rules), keep the picker rendered, and re-fetch the company list after any failed selection; verify T017 error-path tests pass
- [X] T019 [US3] Add the Sign out action to `apps/web/app/select-company/page.tsx` reusing the auth context `logout()` (server revocation + storage clear) and routing to `/login` (FR-008); verify T017 sign-out test passes

**Checkpoint**: All three user stories independently functional; the picker has no dead ends.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Whole-feature verification and quality gates.

- [X] T020 Run the feature suites and the full web suite: `cd apps/web && npx vitest run tests/select-company.test.tsx tests/tenant-guard.test.tsx tests/auth.test.tsx tests/api.test.tsx tests/login.test.tsx && npx vitest run` — all green, no regressions vs the T001 baseline (SC-004) — feature suites 77/77 green; full suite 348 passed with only the pre-existing T001 baseline failure
- [X] T021 [P] Run web lint/type gates: `cd apps/web && npm run lint` and the project's TypeScript check pass with no new violations (Constitution V) — `npx tsc --noEmit` exits 0; no ESLint config or `lint` script exists in `apps/web`, so the TS check is the applicable gate
- [X] T022 Execute the manual validation walkthrough in `specs/059-fix-tenant-selection/quickstart.md` (scenarios 1–8) against the local stack, covering SC-001 through SC-004 including FR-007 persistence across reload and forced refresh — executed against the live local stack via API-driven walkthrough (fresh two-company user): scenarios 1, 2, 4, 6, 8 verified live (login flag + select token, single/zero-company kinds, raw 403 `credential_not_scoped` emitted then mapped, `not_a_member` 403, refresh preserves scope); scenarios 3, 5, 7 rest on client behavior covered by the Vitest suites (scenario 5 `company_suspended` could not be produced live — no suspend API and direct DB writes not permitted in this session)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories (every story reads `tokenKind` from the auth context)
- **User Story 1 (Phase 3)**: Depends on Phase 2 only
- **User Story 2 (Phase 4)**: Depends on Phase 2. Independent of US1's code paths except that its redirect *target* (`/select-company`, T010) must exist for end-to-end verification — the guard and interceptor themselves (T012–T016) can be built in parallel with US1
- **User Story 3 (Phase 5)**: Depends on US1 (extends the picker page created in T010)
- **Polish (Phase 6)**: Depends on all user stories

### Task-level Dependencies

- T002 → T003 → T004 (types → failing tests → implementation)
- T005/T006/T007 (tests) before T008–T011 (implementation); T008 → T009 → T010/T011
- T012/T013 (tests) before T014–T016; T016 depends on T014 + T015
- T017 (tests) before T018 → T019; both depend on T010
- T020–T022 last

### Parallel Opportunities

- **Within US1**: T005, T006, T007 in parallel (three different test files)
- **Within US2**: T012 and T013 in parallel; then T014 and T015 in parallel (different files)
- **Across stories**: after Phase 2, US1 (T005–T011) and US2 (T012–T016) can proceed in parallel — they touch `auth.tsx`/`api.ts` in different functions, but coordinate merges on those two shared files
- **Polish**: T021 parallel with T020

---

## Parallel Example: User Story 1

```bash
# Write all US1 tests together (must fail before implementation):
Task: "T005 selectTenant + login() return-shape tests in apps/web/tests/auth.test.tsx"
Task: "T006 multi-company login routing tests in apps/web/tests/login.test.tsx"
Task: "T007 picker happy-path tests in apps/web/tests/select-company.test.tsx"
```

## Parallel Example: User Story 2

```bash
# Tests in parallel:
Task: "T012 TenantGuard redirect tests in apps/web/tests/tenant-guard.test.tsx"
Task: "T013 credential_not_scoped interception tests in apps/web/tests/api.test.tsx"
# Then implementation in parallel:
Task: "T014 onTenantSelectionRequired interceptor in apps/web/lib/api.ts"
Task: "T015 TenantGuard component in apps/web/lib/auth-guard.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (baseline) + Phase 2 (token-kind foundation)
2. Phase 3: US1 — multi-company users can complete sign-in via the picker
3. **STOP and VALIDATE**: quickstart scenarios 1–2; the reported lockout (SC-001) is fixed for the sign-in path
4. Deliverable MVP — US2/US3 harden restore/bookmark and failure paths

### Incremental Delivery

1. Setup + Foundational → `tokenKind` visible in auth context
2. US1 → picker works from the login flow → validate → demo (MVP)
3. US2 → guard + global interceptor cover restored sessions and bookmarks → validate
4. US3 → failure copy, list re-fetch, sign-out → validate
5. Polish → full suites, lint, quickstart walkthrough

### Notes

- TDD is non-negotiable (Constitution IV): observe each test task fail before its implementation task
- `auth.tsx` and `api.ts` are touched by multiple phases — commit after each task or logical group to keep merges clean
- No Python changes anywhere; pre-existing API-side test baseline issues are out of scope (research.md R8)
