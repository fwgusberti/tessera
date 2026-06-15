# Tasks: Frontend Login

**Input**: Design documents from `/specs/005-frontend-login/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Companion tests are included for all new modules (`lib/auth.tsx`, `lib/auth-guard.tsx`, `app/login/page.tsx`). Tests are written alongside implementation per plan.md §IV guidance. Existing tests (home, documents, admin) need a mock for AuthContext after the AuthProvider is introduced.

**Organization**: Tasks grouped by user story. No new npm dependencies are added.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no cross-task dependency)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

All paths are under `apps/web/` (the Next.js web application).

---

## Phase 1: Setup (Shared Types)

**Purpose**: Add auth type definitions that all subsequent phases depend on.

- [x] T001 Add `AuthUser`, `AuthState`, `AuthStatus`, `LoginCredentials`, `LoginResponse`, `RefreshResponse` to `apps/web/lib/types.ts` (see contracts/auth-context.ts and contracts/api-client.ts for exact shapes)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core auth infrastructure that MUST be complete before any user story can be implemented or tested.

**⚠️ CRITICAL**: All user story work depends on this phase.

- [x] T002 Create `apps/web/lib/auth.tsx` — `"use client"` module with: `AuthContext` (React Context with `AuthContextValue` interface from contracts/auth-context.ts), `AuthProvider` component that (a) hydrates `AuthUser`/tokens from `localStorage` on mount using keys `tessera_access_token`, `tessera_refresh_token`, `tessera_expires_at`, (b) sets `status: "loading"` while hydrating then transitions to `"authenticated"` or `"unauthenticated"`, (c) listens for `window` `storage` events on `tessera_access_token` to sync logout across tabs, (d) implements `login(credentials)`: calls `POST /v1/auth/login`, persists tokens to `localStorage`, updates state; throws user-readable message on 401, (e) implements `logout()`: calls `POST /v1/auth/logout` (best-effort), removes all `tessera_*` keys from `localStorage`, transitions to `"unauthenticated"`, (f) implements `refreshIfNeeded()`: if `tessera_expires_at` is within 60 seconds of now, calls `POST /v1/auth/refresh`, rotates tokens in `localStorage` and state; serialises concurrent calls with a `refreshLock` promise so only one refresh is in flight; throws (triggering logout) if refresh fails. Export `useAuth()` hook that throws when used outside `AuthProvider`.

- [x] T003 Update `apps/web/lib/api.ts` — add `configureApi(config: ApiConfig)` function (called by AuthProvider after mount) that stores `getAccessToken`, `refreshIfNeeded`, `onUnauthorized` callbacks; update the internal `request()` function to: (a) call `await config.refreshIfNeeded()` before each request to get a fresh token, (b) inject `Authorization: Bearer <token>` header on every call, (c) on `401` response: call `config.refreshIfNeeded()` once to force a refresh (bypassing the expiry check), then retry the original request exactly once; if the retry is also `401`, call `config.onUnauthorized()` and throw; (d) add unauthenticated raw variants `authLogin`, `authRefresh`, `authLogout` that call the `/v1/auth/*` endpoints without injecting a Bearer header (used by AuthContext only). NOTE: `configureApi` must be called from AuthProvider before any API calls are made.

- [x] T004 Create `apps/web/lib/auth-guard.tsx` — `"use client"` component `AuthGuard({ children })` that: (a) calls `useAuth()` to get `status`, (b) while `status === "loading"` renders `null` (blank; avoids flash of protected content), (c) when `status === "unauthenticated"` calls `router.replace("/login?redirect=" + encodeURIComponent(pathname))` via `useRouter` + `usePathname` from `next/navigation` and returns `null`, (d) when `status === "authenticated"` renders `children`. The `redirect` query param MUST be validated in the login page to be a relative path before use (to prevent open-redirect).

- [x] T005 Update `apps/web/app/layout.tsx` — extract the `<nav>` into a separate `"use client"` `NavBar` component in `apps/web/components/NavBar.tsx` that calls `useAuth()` to render a "Sign out" button when `status === "authenticated"` (clicking it calls `logout()` then navigates to `/login`); wrap `{children}` inside `layout.tsx` with `<AuthProvider>` (import from `@/lib/auth`); call `configureApi` inside `AuthProvider`'s `useEffect` once tokens are ready.

**Checkpoint**: AuthContext, api.ts, AuthGuard, and AuthProvider/NavBar are complete. User story implementation can now begin.

---

## Phase 3: User Story 1 — Authenticate to Access the Application (Priority: P1) 🎯 MVP

**Goal**: An unauthenticated user is redirected to `/login`, can submit credentials, and lands on the originally requested page. Invalid credentials show a clear error. Empty fields are caught client-side. Already-authenticated users bypass the login page.

**Independent Test**: Open an incognito window → navigate to `/` → confirm redirect to `/login?redirect=/` → submit valid credentials → confirm landing on `/` with dashboard loaded. See quickstart.md Scenarios 1–4.

### Companion Tests for User Story 1

- [x] T006 [P] [US1] Write `apps/web/tests/auth.test.tsx` — describe "AuthContext / login": (a) successful login stores tokens in localStorage and transitions status to `"authenticated"`, (b) failed login (401) throws with a user-readable message and does not store tokens, (c) already-authenticated user on login page is redirected — mock `authLogin` (the raw fetch variant); use `renderHook` with `AuthProvider` wrapper; assert localStorage key values after login.

- [x] T007 [P] [US1] Write `apps/web/tests/login.test.tsx` — describe "LoginPage": (a) renders email and password inputs and a submit button, (b) submitting with empty password shows validation message before any fetch call, (c) submitting with empty email shows validation message before any fetch call, (d) successful login calls `useAuth().login()` and triggers router push to `?redirect` destination or `/`, (e) failed login shows inline error message and keeps the form on screen, (f) when `status === "authenticated"` on mount, page redirects to `/`. Mock `useAuth` via `vi.mock("@/lib/auth", ...)`.

- [x] T008 [P] [US1] Write `apps/web/tests/auth-guard.test.tsx` — describe "AuthGuard": (a) renders `null` and redirects to `/login?redirect=/protected` when `status === "unauthenticated"`, (b) renders children when `status === "authenticated"`, (c) renders `null` without redirecting when `status === "loading"`. Mock `useAuth` and `next/navigation` (`useRouter`, `usePathname`).

### Implementation for User Story 1

- [x] T009 [US1] Create `apps/web/app/login/page.tsx` — `"use client"` login page with: (a) controlled `email` and `password` inputs, (b) client-side validation before submit: both fields required; show `<p role="alert">` messages next to each empty field without making a network call (FR-003), (c) on submit: call `useAuth().login({ email, password })`; catch thrown message and display below the form as a non-technical error (FR-004), (d) on success: read `?redirect` search param via `useSearchParams()`; validate it starts with `/` and does not start with `//` (open-redirect guard); call `router.push(redirect ?? "/")` (FR-005), (e) on mount: if `status === "authenticated"`, call `router.replace("/")` (FR-007). Wrap the page body in `<Suspense>` as required by Next.js for `useSearchParams()`.

- [x] T010 [US1] Wrap `apps/web/app/page.tsx` — import `AuthGuard` from `@/lib/auth-guard` and render `<AuthGuard>{/* existing page content */}</AuthGuard>` around the page body (FR-006). The existing `"use client"` directive and all current component code remain unchanged.

- [x] T011 [P] [US1] Wrap `apps/web/app/search/page.tsx` with `<AuthGuard>` following the same pattern as T010 (FR-006).

- [x] T012 [P] [US1] Wrap `apps/web/app/documents/page.tsx` with `<AuthGuard>` (FR-006).

- [x] T013 [P] [US1] Wrap `apps/web/app/documents/[id]/page.tsx` with `<AuthGuard>` (FR-006).

- [x] T014 [P] [US1] Wrap `apps/web/app/metrics/page.tsx` with `<AuthGuard>` (FR-006).

- [x] T015 [P] [US1] Wrap `apps/web/app/proposals/page.tsx` with `<AuthGuard>` (FR-006).

- [x] T016 [P] [US1] Wrap `apps/web/app/admin/page.tsx` with `<AuthGuard>` (FR-006).

**Checkpoint**: Login page, all protected routes, and AuthGuard are complete. Run Vitest + quickstart.md Scenarios 1–4.

---

## Phase 4: User Story 2 — Stay Logged In Across Page Refreshes and Navigation (Priority: P2)

**Goal**: After login, refreshing the browser or navigating between pages keeps the user authenticated. Expired access tokens are silently renewed. If renewal fails, the user is redirected to login with the current path preserved.

**Independent Test**: Log in → refresh the page → confirm still authenticated (no login redirect). See quickstart.md Scenarios 5–6.

**Note**: The core implementation (localStorage hydration on mount, `refreshIfNeeded`, 401 retry in api.ts) was built in Phase 2. This phase adds companion tests and verifies the wiring.

### Companion Tests for User Story 2

- [x] T017 [P] [US2] Extend `apps/web/tests/auth.test.tsx` — describe "AuthContext / session persistence": (a) on mount with valid tokens in localStorage, status transitions from `"loading"` to `"authenticated"` without calling the refresh endpoint, (b) `refreshIfNeeded()` with an `expires_at` more than 60 s in the future returns the current access token without calling the refresh endpoint, (c) `refreshIfNeeded()` with an `expires_at` within 60 s calls `POST /v1/auth/refresh`, rotates tokens in localStorage, and returns the new access token, (d) concurrent calls to `refreshIfNeeded()` when a refresh is in flight all resolve to the same promise (no double-refresh — verify fetch called exactly once), (e) failed refresh (network error or 401 from refresh endpoint) clears localStorage and transitions status to `"unauthenticated"`. Mock the `authRefresh` raw function via `vi.mock`.

- [x] T018 [P] [US2] Write `apps/web/tests/api.test.tsx` — describe "api / auth injection": (a) request injects `Authorization: Bearer <token>` header when a token is configured, (b) request with expired token calls `refreshIfNeeded()` before the fetch, (c) on 401 response, the client calls `refreshIfNeeded()` once and retries the original request, (d) on second consecutive 401 (retry also fails), `onUnauthorized()` is called and an error is thrown. Mock `fetch` with `vi.fn()`.

**Checkpoint**: Session persistence, proactive refresh, and reactive 401 handling are fully tested. Run quickstart.md Scenarios 5–6.

---

## Phase 5: User Story 3 — Log Out Securely (Priority: P3)

**Goal**: An authenticated user clicks the logout button in the nav (visible on all protected pages), their session ends, and they are redirected to `/login`. Subsequent navigation to protected pages redirects back to login.

**Independent Test**: Log in → click logout in navbar → confirm redirect to `/login` → press browser back → confirm redirect to `/login` again. See quickstart.md Scenarios 7–8.

**Note**: The `logout()` method and `NavBar` logout button were implemented in Phase 2 (T002 and T005). This phase adds companion tests and verifies cross-tab behaviour.

### Companion Tests for User Story 3

- [x] T019 [P] [US3] Extend `apps/web/tests/auth.test.tsx` — describe "AuthContext / logout": (a) `logout()` calls `authLogout` with the current access and refresh tokens, (b) `logout()` removes all `tessera_*` keys from localStorage and transitions status to `"unauthenticated"` regardless of whether the server call succeeds or fails (best-effort server revocation), (c) a `storage` event setting `tessera_access_token` to `null` (from another tab's logout) causes the current context to transition to `"unauthenticated"`.

- [x] T020 [P] [US3] Extend `apps/web/tests/auth-guard.test.tsx` — describe "AuthGuard / post-logout": (a) after `status` transitions from `"authenticated"` to `"unauthenticated"` (simulated logout), AuthGuard triggers `router.replace("/login?redirect=<current path>")` on the next render.

- [x] T021 [P] [US3] Write `apps/web/tests/navbar.test.tsx` — describe "NavBar": (a) logout button is visible when `status === "authenticated"`, (b) clicking the logout button calls `useAuth().logout()` and navigates to `/login`, (c) logout button is not rendered when `status === "unauthenticated"`. Mock `useAuth` and `next/navigation`.

**Checkpoint**: All three user stories are independently complete and tested. Run quickstart.md Scenarios 7–8 including the cross-tab scenario.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Update existing tests broken by the new AuthProvider wrapper, and validate the full feature end-to-end.

- [x] T022 [P] Update `apps/web/tests/home.test.tsx` — add a `vi.mock("@/lib/auth", () => ({ useAuth: () => ({ status: "authenticated", user: { id: "u1", email: "test@test.com", isAdmin: false }, accessToken: "tok" }), AuthProvider: ({ children }: { children: React.ReactNode }) => children, AuthGuard: ({ children }: { children: React.ReactNode }) => children }))` at the top so the AuthProvider/AuthGuard wrappers added to the home page do not break the existing test suite. Verify all existing home tests still pass.

- [x] T023 [P] Update `apps/web/tests/documents.test.tsx` — apply the same `vi.mock("@/lib/auth", ...)` pattern as T022.

- [x] T024 [P] Update `apps/web/tests/admin.test.tsx` — apply the same `vi.mock("@/lib/auth", ...)` pattern as T022.

- [x] T025 Handle service-unavailable error case in `apps/web/app/login/page.tsx` — ensure network errors (non-401 failures from `authLogin`) display a generic "Something went wrong, please try again" message (distinct from the invalid-credentials message) and do not leave partial state in localStorage. Add a test case for this in `apps/web/tests/login.test.tsx`.

- [x] T026 Run full Vitest suite (`cd apps/web && npm test`) and confirm all tests pass with no console errors related to missing AuthContext. Run quickstart.md validation Scenarios 1–8 manually in a browser.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on T001; BLOCKS all user story work
- **Phase 3 (US1)**: Depends on Phase 2 completion; T006–T008 (tests) can run in parallel with each other; T009 can run in parallel with T006–T008; T010–T016 can all run in parallel after T004 (AuthGuard) is done
- **Phase 4 (US2)**: Depends on Phase 2 completion; T017 and T018 can run in parallel
- **Phase 5 (US3)**: Depends on Phase 2 completion; T019–T021 can run in parallel
- **Phase 6 (Polish)**: Depends on all prior phases; T022–T025 can run in parallel; T026 runs last

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 2 only — no dependency on US2 or US3
- **US2 (P2)**: Depends on Phase 2 only — implementation is already in Phase 2; Phase 4 adds tests only
- **US3 (P3)**: Depends on Phase 2 only — logout and NavBar already in Phase 2; Phase 5 adds tests only

### Within Phase 2 (sequential order)

1. T001 (types) → T002 (AuthContext) → T003 (api.ts update, needs AuthContext interface) → T004 (AuthGuard, needs useAuth) → T005 (layout, needs AuthProvider + AuthGuard)

---

## Parallel Opportunities

### Phase 2

All tasks are sequential (each depends on the previous).

### Phase 3: User Story 1

```text
# Step A — All can run in parallel:
T006  Write auth.test.tsx (login describe block)
T007  Write login.test.tsx
T008  Write auth-guard.test.tsx
T009  Create app/login/page.tsx

# Step B — All can run in parallel (after T004 AuthGuard exists):
T010  Wrap app/page.tsx
T011  Wrap app/search/page.tsx
T012  Wrap app/documents/page.tsx
T013  Wrap app/documents/[id]/page.tsx
T014  Wrap app/metrics/page.tsx
T015  Wrap app/proposals/page.tsx
T016  Wrap app/admin/page.tsx
```

### Phases 4 + 5 (can run in parallel with each other after Phase 2)

```text
# Both can run in parallel:
T017  auth.test.tsx (persistence describe block)
T018  api.test.tsx

T019  auth.test.tsx (logout describe block)
T020  auth-guard.test.tsx (post-logout describe block)
T021  navbar.test.tsx
```

### Phase 6

```text
# All can run in parallel:
T022  Update home.test.tsx
T023  Update documents.test.tsx
T024  Update admin.test.tsx
T025  Service-unavailable error case + test

# Runs last:
T026  Full test suite run + quickstart validation
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: T001
2. Complete Phase 2: T002 → T003 → T004 → T005
3. Complete Phase 3: T006–T016
4. **STOP and VALIDATE**: Run Vitest + quickstart.md Scenarios 1–4
5. Deploy/demo: users can now log in and access all protected pages

### Incremental Delivery

1. Phase 1 + Phase 2 → auth infrastructure ready
2. Phase 3 (US1) → login flow + protected routes → **MVP!**
3. Phase 4 (US2) → session persistence tests → confidence in refresh flow
4. Phase 5 (US3) → logout tests → logout fully verified
5. Phase 6 → existing tests fixed + full end-to-end validation

### Notes

- T002 is the most complex task — it implements all of AuthContext's login, logout, refresh, localStorage, and cross-tab logic in a single `"use client"` module
- T003 modifies an existing shared file — be careful not to break the existing `api.get`/`api.post` surface
- T005 splits the `<nav>` out of `layout.tsx` — existing nav links must remain unchanged; only the logout button and AuthProvider wrap are new
- Wrap tasks T010–T016 are all identical in pattern: add `import { AuthGuard } from "@/lib/auth-guard"` and wrap existing return content with `<AuthGuard>…</AuthGuard>` — each takes <5 minutes
- `configureApi()` must be called inside `AuthProvider`'s `useEffect` (after token hydration) to avoid calling it during SSR
