---
description: "Task list for User Badge feature implementation"
---

# Tasks: User Badge

**Input**: Design documents from `/specs/057-user-badge/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: INCLUDED — the constitution mandates Test-Driven Development
(Principle IV, NON-NEGOTIABLE). Test tasks are written first and must fail
before implementation.

**Organization**: Tasks are grouped by user story. US1 (P1) is the MVP.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 / US2 (Setup, Foundational, Polish carry no story label)

## Path Conventions

- Backend (FastAPI): `apps/api/tessera_api/`, tests `apps/api/tests/`
- Frontend (Next.js): `apps/web/` (`components/`, `lib/`, `tests/`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Client-side plumbing to talk to the new endpoint. No new
dependencies and no schema changes are required for this feature.

- [ ] T001 [P] Add `MeResponse` interface (`id`, `email`, `display_name: string | null`, `is_admin`) to `apps/web/lib/types.ts` per contracts/auth-me.md
- [ ] T002 [P] Add `getMe(): Promise<MeResponse>` calling `GET /v1/auth/me` to `apps/web/lib/api.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The self-identity endpoint supplies the display name consumed by
BOTH user stories. Must exist before either story delivers its full value.

**⚠️ CRITICAL**: No user story work depending on the display name can complete
until this phase is done.

- [ ] T003 Write failing integration tests for `GET /v1/auth/me` in `apps/api/tests/integration/test_auth_me.py`: (a) happy path returns caller `id`/`email`/`display_name`; (b) user with no name → `display_name: null`; (c) no bearer token → 401; (d) tenant isolation — users A (company 1) and B (company 2) each get only their own identity (SC-004); (e) returned `email` equals token subject, never substituted
- [ ] T004 Implement `GET /v1/auth/me` handler in `apps/api/tessera_api/routers/auth.py` using the `CurrentUser` dependency and `SqlUserRepository.get_by_id(UUID(user_info["sub"]))`; return `MeResponse` shape; 404 if the subject row is missing (make T003 pass)
- [ ] T005 Run Ruff + Black on `apps/api` and confirm the new endpoint's statements meet the 85% coverage gate (Constitution V/IV)

**Checkpoint**: `/auth/me` returns the caller's own identity and passes isolation tests.

---

## Phase 3: User Story 1 - See who I am signed in as (Priority: P1) 🎯 MVP

**Goal**: A persistent navigation badge shows the signed-in account's email (and
display name when available) on every authenticated page; it is hidden when no
one is signed in and disappears on sign-out.

**Independent Test**: Sign in as a known account → badge shows that account's
email (plus name) on Chat/Documents/Spaces; sign out → badge disappears.

### Tests for User Story 1 (write first, must fail) ⚠️

- [ ] T006 [P] [US1] Write failing Vitest tests in `apps/web/tests/UserBadge.test.tsx`: (a) `status: "unauthenticated"` → renders nothing (FR-004); (b) authenticated → email from `useAuth()` shown immediately before `/auth/me` resolves; (c) after `getMe()` resolves with a `display_name` → name shown alongside email (FR-002); (d) `display_name: null` → email only; (e) long email → element carries full value in `title` (FR-008)

### Implementation for User Story 1

- [ ] T007 [US1] Create `apps/web/components/UserBadge.tsx`: gate on `useAuth().status === "authenticated"` (else render null), show `user.email` immediately, fetch `getMe()` on mount / when auth user id changes and enrich with `display_name`; truncate label with `truncate`/`max-w-*` and expose full value via `title`; style with `slate-*`/`indigo-*` per constitution (make T006 pass)
- [ ] T008 [US1] Mount `<UserBadge />` in `apps/web/components/NavBar.tsx` in both the desktop bar (near Account/Sign out) and the mobile menu, so it is present on every authenticated page (FR-003) and legible on mobile (FR-009)

**Checkpoint**: MVP — badge shows the active account's email + name across pages and hides on sign-out.

---

## Phase 4: User Story 2 - Distinguish accounts at a glance (Priority: P2)

**Goal**: The badge shows a short visual marker (initials) derived from identity,
and updates its label + marker when the active account switches.

**Independent Test**: Sign in as account A, note initials/label; sign out and
sign in as account B → badge's initials and label reflect B, not A.

### Tests for User Story 2 (write first, must fail) ⚠️

- [ ] T009 [P] [US2] Write failing Vitest tests for `initials(name, email)` in `apps/web/tests/identity.test.ts`: two-word name → first+last initial; single-word name → first two letters; no name → email local-part first two letters; whitespace trimmed; output uppercase and ≤2 chars (per contracts/user-badge.md)
- [ ] T010 [P] [US2] Add failing Vitest cases to `apps/web/tests/UserBadge.test.tsx`: initials chip renders (FR-007); when the authenticated user id changes, the badge re-derives to the new identity's label + initials (FR-005, SC-003)

### Implementation for User Story 2

- [ ] T011 [P] [US2] Implement pure `initials(name: string | null | undefined, email: string): string` in `apps/web/lib/identity.ts` (make T009 pass)
- [ ] T012 [US2] Render the initials avatar chip in `apps/web/components/UserBadge.tsx` using `initials(...)` (`bg-indigo-100 text-indigo-700`), and ensure re-derivation keys on the auth user id so an account switch updates the marker (make T010 pass)

**Checkpoint**: Both stories work — badge identifies the account and visibly changes across account switches.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Verification and final quality gates.

- [ ] T013 [P] Run Ruff + Black (`apps/api`) and the web lint config (`apps/web`); fix any violations (Constitution V)
- [ ] T014 [P] Confirm `apps/web` Vitest suite passes and `apps/api` coverage gate is met for the new code (Constitution IV)
- [ ] T015 Execute the manual validation steps in `specs/057-user-badge/quickstart.md` (Stories 1–2, edge cases, and the SC-004 isolation walkthrough)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup (uses `MeResponse`/`getMe`). BLOCKS full delivery of both stories.
- **User Story 1 (Phase 3)**: Depends on Foundational (needs `/auth/me` for the name).
- **User Story 2 (Phase 4)**: Depends on Foundational and on the `UserBadge` created in US1 (T007) — extends the same component.
- **Polish (Phase 5)**: Depends on all targeted stories being complete.

### Within Each User Story

- Tests are written first and must fail before implementation.
- US1: T006 (tests) → T007 (component) → T008 (mount in NavBar).
- US2: T009/T010 (tests) → T011 (helper) → T012 (chip + switch reactivity).

### Parallel Opportunities

- Setup: T001 and T002 in parallel.
- US1 tests (T006) can be authored while Foundational finishes, but pass only after T004.
- US2: T009 and T010 (different concerns) in parallel; T011 (`identity.ts`) is [P] vs the component file.
- Polish: T013 and T014 in parallel.

---

## Parallel Example: Setup

```bash
Task: "Add MeResponse interface to apps/web/lib/types.ts"
Task: "Add getMe() to apps/web/lib/api.ts"
```

## Parallel Example: User Story 2 tests

```bash
Task: "initials() unit tests in apps/web/tests/identity.test.ts"
Task: "UserBadge initials + account-switch tests in apps/web/tests/UserBadge.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1: Setup (T001–T002).
2. Phase 2: Foundational `/auth/me` (T003–T005) — CRITICAL.
3. Phase 3: User Story 1 (T006–T008).
4. **STOP and VALIDATE**: badge shows email + name across pages, hides on sign-out.
5. Deploy/demo the MVP.

### Incremental Delivery

1. Setup + Foundational → identity endpoint ready.
2. US1 → identity badge visible everywhere (MVP).
3. US2 → initials marker + account-switch reactivity.
4. Polish → lint, coverage, quickstart validation.

---

## Notes

- No new dependencies and no database migrations — this feature reads the
  caller's own existing `users.display_name`.
- [P] = different files, no dependencies.
- Tenant isolation is verified by T003(d)/(e) and T015 (SC-004): the badge and
  `/auth/me` only ever expose the current session's own identity.
- Commit after each task or logical group.
