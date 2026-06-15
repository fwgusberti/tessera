# Tasks: New User Registration

**Input**: Design documents from `specs/006-user-registration/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/register-api.md ✅ | quickstart.md ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared state)
- **[Story]**: User story this task belongs to ([US1], [US2], [US3])
- Exact file paths included in every task description

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the types and API function that all phases depend on. No user story work can begin before this phase.

- [x] T001 Add `RegisterCredentials` interface and `PasswordStrength` type to `apps/web/lib/types.ts`
- [x] T002 Add `authRegister(displayName, email, password)` function to `apps/web/lib/api.ts` (raw POST to `/v1/auth/register`, returns `void` — response body intentionally discarded per contracts/register-api.md)

**Checkpoint**: Types exported and `authRegister` callable — remaining phases may begin

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: Scaffold the register route so Next.js resolves `/register`. Required before any US1–US3 implementation.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Create `apps/web/app/register/page.tsx` with empty `RegisterPage` and `RegisterForm` component shells (use "use client" directive, Suspense wrapper matching `apps/web/app/login/page.tsx` layout)

**Checkpoint**: `/register` route exists and renders an empty page — user story implementation can now begin

---

## Phase 3: User Story 1 — Complete Registration Flow (Priority: P1) 🎯 MVP

**Goal**: A new visitor can fill in display name, email, and password, submit the form, be auto-authenticated, and be redirected to their intended destination.

**Independent Test**: Visit `/register`, submit valid credentials → redirected to `/` (or `?redirect=` target) as an authenticated user without a second login step.

### Implementation for User Story 1

- [x] T004 [US1] Implement form UI in `apps/web/app/register/page.tsx`: three labeled inputs (Display name, Email, Password) with `id`, `autoComplete`, `disabled={submitting}` attributes matching login page conventions
- [x] T005 [US1] Add client-side validation in `apps/web/app/register/page.tsx`: display name non-empty after trim and ≤ 100 chars; email contains "@" and a dot after "@"; password ≥ 8 chars; show inline `role="alert"` field errors (see data-model.md Validation Rules)
- [x] T006 [P] [US1] Add password strength indicator in `apps/web/app/register/page.tsx`: inline `passwordStrength(value: string): PasswordStrength` function using heuristic from research.md (weak/medium/strong label rendered below password field, non-blocking)
- [x] T007 [US1] Implement form submission in `apps/web/app/register/page.tsx`: call `authRegister()`, then on success call `login({email, password})` from `useAuth()`, then redirect using `?redirect=` safety predicate (identical to `apps/web/app/login/page.tsx:49`); disable button during flight
- [x] T008 [US1] Add authenticated-user guard in `apps/web/app/register/page.tsx`: `useEffect` watching `status === "authenticated"` → `router.replace("/")`, render null while loading or already authenticated (mirrors login page pattern)

### Tests for User Story 1

- [x] T009 [P] [US1] Write Vitest tests for US1 in `apps/web/tests/register.test.tsx`: render form fields; submit with valid data → calls `authRegister` then `login` then redirects to `/`; submit with `?redirect=/documents` → redirects to `/documents`; client-side validation blocks empty fields; password < 8 chars blocked; display name > 100 chars blocked; authenticated status → `router.replace("/")` called

**Checkpoint**: User Story 1 is fully functional. `/register` accepts valid submissions, auto-logs the user in, and redirects correctly.

---

## Phase 4: User Story 2 — Duplicate Email Handling (Priority: P2)

**Goal**: When a visitor tries to register with an already-registered email, they see a clear error and a link to sign in.

**Independent Test**: Submit the form with a known-registered email → error "This email is already registered" and a sign-in link appear; page does not redirect.

### Implementation for User Story 2

- [x] T010 [US2] Handle 409 conflict in `apps/web/app/register/page.tsx`: when `authRegister` throws with message `"Email already registered"`, display a `role="alert"` form-level error containing the message and an `<a href="/login">` sign-in link (mirrors FR-007)

### Tests for User Story 2

- [x] T011 [P] [US2] Add Vitest tests for US2 in `apps/web/tests/register.test.tsx`: mock `authRegister` to throw `"Email already registered"` → error message visible, sign-in link present, no redirect; generic server error → generic message shown

**Checkpoint**: Duplicate-email path is handled. User Story 2 is complete and independently verifiable.

---

## Phase 5: User Story 3 — Navigation Links (Priority: P3)

**Goal**: A visitor on the login page can discover and reach `/register` via a visible link, and vice versa.

**Independent Test**: Visit `/login` → "Create account" link exists and points to `/register`. Visit `/register` → sign-in link exists and points to `/login`.

### Implementation for User Story 3

- [x] T012 [US3] Add "Create account" link to `apps/web/app/login/page.tsx`: render below the submit button, pointing to `/register` (or `/register?redirect=<current redirect>` if one is present)
- [x] T013 [US3] Add "Already have an account? Sign in" link to `apps/web/app/register/page.tsx`: render below the submit button, pointing to `/login`

### Tests for User Story 3

- [x] T014 [P] [US3] Add Vitest tests for US3 in `apps/web/tests/register.test.tsx` and update `apps/web/tests/login.test.tsx`: login page renders "Create account" link to `/register`; register page renders sign-in link to `/login`

**Checkpoint**: All three user stories complete. Full registration flow, duplicate-email handling, and navigation links are all independently testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T015 [P] Run full test suite `cd apps/web && npm test` and confirm zero regressions in `login.test.tsx`, `auth.test.tsx`, and new `register.test.tsx`
- [x] T016 Run quickstart.md manual validation scenarios 1–6 against the running dev stack to confirm end-to-end behaviour

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — no dependency on US2 or US3
- **US2 (Phase 4)**: Depends on Phase 2 — independent of US1/US3 (same file, different code path)
- **US3 (Phase 5)**: Depends on Phase 2 — independent of US1/US2 for login-link task; register-link task may be done alongside US1
- **Polish (Phase 6)**: Depends on all desired stories complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependency on US2/US3
- **US2 (P2)**: Can start after Phase 2 — no dependency on US1/US3 (adds a new error branch)
- **US3 (P3)**: Can start after Phase 2 — T012 (login page link) is independent; T013 (register page link) can be done alongside T004

### Within Each Phase

- T004 → T005 → T007 (UI built before validation wired, validation before submission)
- T006 (strength indicator) is parallel to T005 (different concern in same file)
- T008 can be implemented any time after T003

---

## Parallel Opportunities

```bash
# Phase 1 — can run in parallel:
Task T001: types.ts additions
Task T002: api.ts additions

# Phase 3 — parallel within story:
Task T006: password strength indicator  ← parallel with T005
Task T009: US1 tests                    ← parallel with T006

# Phase 4 — parallel:
Task T011: US2 tests                    ← parallel with T010 (after T010 is spec'd)

# Phase 5 — parallel:
Task T012: login page link
Task T013: register page link  ← can also be done alongside T004 in Phase 3

# Phase 6 — parallel:
Task T015: automated tests
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003)
3. Complete Phase 3: User Story 1 (T004–T009)
4. **STOP and VALIDATE**: register a new user end-to-end per quickstart.md Scenario 1
5. Ship or continue to US2/US3

### Incremental Delivery

1. Setup + Foundational → route resolves
2. US1 complete → core registration works, user is authenticated automatically
3. US2 complete → duplicate email handled gracefully
4. US3 complete → navigation between login and register pages discoverable
5. Polish → full regression clean

---

## Notes

- All new code lives in `apps/web/` — no backend changes required
- `authRegister` return value is intentionally `void`; the auto-login via `login()` from `useAuth` is the session acquisition step
- Password strength indicator does NOT block submission; only `password.length >= 8` gates the submit
- `?redirect=` safety predicate must match exactly: `redirect.startsWith("/") && !redirect.startsWith("//")`
- Tests mock `@/lib/auth` and `next/navigation` exactly as `apps/web/tests/login.test.tsx` does
