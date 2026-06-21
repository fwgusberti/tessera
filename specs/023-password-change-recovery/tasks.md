# Tasks: Password Change and Recovery Flow

**Input**: Design documents from `/specs/023-password-change-recovery/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Tests**: Included — the Tessera Constitution (IV) mandates TDD as NON-NEGOTIABLE for all core business domain work.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in all descriptions

---

## Phase 1: Setup

**Purpose**: Create the database migration that all user stories require before any schema-dependent code can run.

- [X] T001 Create Alembic migration 0005 for `password_reset_tokens` table (id UUID PK, user_id FK→users CASCADE, token_hash VARCHAR(64) UNIQUE, created_at TIMESTAMPTZ DEFAULT now(), expires_at TIMESTAMPTZ NOT NULL, consumed_at TIMESTAMPTZ) with partial index `ix_prt_user_active` WHERE consumed_at IS NULL, in `db/migrations/versions/0005_password_reset_tokens.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain entities, port ABCs, ORM models, repository implementations, and shared utilities that all three user stories depend on. Must be complete before Phase 3.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Add `PasswordResetToken` Pydantic entity (fields: id, user_id, token_hash, created_at, expires_at, consumed_at) to `packages/core/tessera_core/domain/entities.py`
- [X] T003 [P] Extend `packages/core/tessera_core/ports/repositories.py`: add `PasswordResetTokenRepository` ABC (methods: `create`, `get_by_hash`, `consume_all_for_user`); add `revoke_all_except(user_id, except_hash)` to `RefreshTokenRepository` ABC
- [X] T004 [P] Add abstract method `send_password_reset(*, to, reset_url, expires_in_minutes)` to `EmailPort` in `packages/core/tessera_core/ports/providers.py`
- [X] T005 Add `PasswordResetTokenModel` SQLAlchemy ORM class (mapped to `password_reset_tokens` table) to `apps/api/tessera_api/adapters/models.py` — depends on T002
- [X] T006 Write failing unit tests for `validate_password_strength()` covering: too-short password, blocklist match, all-same-chars, and valid passwords in `apps/api/tests/unit/test_password_strength.py` (TDD: must fail before T007)
- [X] T007 Implement `validate_password_strength(password: str) -> None` (raises `ValueError` on weak password; blocklist of ~20 common passwords; len ≥ 8; not all identical chars) in `apps/api/tessera_api/auth/password_strength.py` — depends on T006
- [X] T008 [P] Write failing unit tests for `PasswordResetService.create_token()` (returns valid entity + raw token) and `is_valid()` (expired, consumed, valid cases) in `packages/core/tests/test_password_reset.py` (TDD: must fail before T009)
- [X] T009 Implement `PasswordResetService` with `create_token(user_id, expires_in_minutes=60) -> tuple[PasswordResetToken, str]` and `is_valid(token) -> bool` in `packages/core/tessera_core/services/password_reset.py` — depends on T002, T008
- [X] T010 [P] Implement `check_rate_limit(redis_client, key: str, max_count: int, window_seconds: int) -> bool` (INCR + EXPIRE pattern) in `apps/api/tessera_api/auth/rate_limit.py`
- [X] T011 Implement `SqlPasswordResetTokenRepository` (create, get_by_hash, consume_all_for_user) and add `revoke_all_except(user_id, except_hash)` to `SqlRefreshTokenRepository` in `apps/api/tessera_api/adapters/repo.py` — depends on T003, T005; edit same file sequentially
- [X] T012 Implement `send_password_reset()` in `FastMailEmailAdapter` in `apps/api/tessera_api/adapters/email.py` — depends on T004

**Checkpoint**: Domain entities, all ports, ORM models, repository implementations, password-strength validator, rate limiter, and email adapter are all complete. User story implementation can now begin.

---

## Phase 3: User Story 1 — Change Password While Logged In (Priority: P1) 🎯 MVP

**Goal**: An authenticated user can change their password; all other sessions are revoked; the current session is maintained via token rotation; the event is audit-logged.

**Independent Test**: Log in as a registered user → `POST /v1/auth/change-password` with valid credentials → verify HTTP 200 and new token pair → verify login with old password returns 401 → verify second session's refresh token is rejected.

### Tests for User Story 1 (TDD — write before implementation)

- [X] T013 [US1] Write failing contract tests for `POST /v1/auth/change-password`: success (200 + token pair), wrong current password (401), password mismatch (400), weak new password (400), missing auth (401) in `apps/api/tests/contract/test_change_password.py`
- [X] T014 [P] [US1] Write failing integration tests for change-password: session invalidation (other tokens revoked, current rotated), audit record written in `apps/api/tests/integration/test_password_change.py`

### Implementation for User Story 1

- [X] T015 [US1] Add `POST /v1/auth/change-password` endpoint to `apps/api/tessera_api/routers/auth.py`: validate Bearer token → verify current_password with bcrypt → check password_mismatch + strength → update password_hash → revoke_all_except current refresh_token → rotate current refresh_token → write audit `auth.password.change` → return new token pair — depends on T013, T014
- [X] T016 [P] [US1] Add `changePassword()` API client function (calls POST /v1/auth/change-password, returns new token pair) to `apps/web/lib/auth.ts`
- [X] T017 [P] [US1] Create account settings page with Security section containing current-password, new-password, confirm-password inputs; on 200 update auth store with new tokens; inline error states per contracts/frontend.md in `apps/web/app/account/page.tsx` — depends on T016
- [X] T018 [US1] Add "Forgot password?" link below the password field in `apps/web/app/login/page.tsx` (styled identically to existing "Create account" link; href="/forgot-password")

**Checkpoint**: User Story 1 is fully functional and independently testable.

---

## Phase 4: User Story 2 — Request a Password Reset by Email (Priority: P2)

**Goal**: An unauthenticated user submits their email; the system always returns the same neutral response (no enumeration); a time-limited single-use reset link is emailed when the email is registered; rate limiting silently absorbs excess requests.

**Independent Test**: Submit `POST /v1/auth/forgot-password` with a registered email → confirm email received in ≤ 60 s → submit again immediately → confirm only one email received → submit with an unregistered email → confirm identical response body and comparable timing.

### Tests for User Story 2 (TDD — write before implementation)

- [X] T019 [US2] Write failing contract tests for `POST /v1/auth/forgot-password`: registered email (200 + fixed body), unregistered email (200 + same body), rate-limit exceeded (200 + same body, no email) in `apps/api/tests/contract/test_forgot_password.py`
- [X] T020 [P] [US2] Write failing integration tests for forgot-password: token created and expires in 60 min, prior tokens consumed on re-issue (FR-008), audit record written, no-op when email missing in `apps/api/tests/integration/test_forgot_password.py`

### Implementation for User Story 2

- [X] T021 [US2] Add `POST /v1/auth/forgot-password` endpoint to `apps/api/tessera_api/routers/auth.py`: check_rate_limit by IP (5/15 min, Redis key = `tessera:rate:reset:{sha256(ip)}`); if over limit return 200 early; lookup user by email; if not found perform dummy bcrypt + write audit (nil UUID, found=false) + return 200; else consume_all_for_user + create new PasswordResetToken via PasswordResetService + persist + send_password_reset email + write audit `auth.password.reset_requested` + return 200 — depends on T019, T020
- [X] T022 [P] [US2] Add `forgotPassword(email)` API client function to `apps/web/lib/auth.ts`
- [X] T023 [P] [US2] Create `/forgot-password` page: email input, "Send reset link" button, always shows success message after submission (no error state for 200), "Back to sign in" link, slate/indigo design system in `apps/web/app/forgot-password/page.tsx` — depends on T022

**Checkpoint**: User Story 2 is fully functional and independently testable.

---

## Phase 5: User Story 3 — Use Reset Link to Set a New Password (Priority: P3)

**Goal**: A user clicks the reset link, sets a new password; the token is consumed; all sessions are revoked; the user is redirected to `/login`; the event is audit-logged. Expired or already-consumed tokens show a clear actionable error.

**Independent Test**: Obtain a valid reset token → `POST /v1/auth/reset-password` with valid new password → verify 204 → verify login with new password → verify the same token returns 400 on a second attempt → load `/reset-password?token=<expired>` in browser → verify expired-link page with "Request a new link" button.

### Tests for User Story 3 (TDD — write before implementation)

- [X] T024 [US3] Write failing contract tests for `POST /v1/auth/reset-password`: valid token + new password (204), consumed token (400 `invalid_or_expired_token`), expired token (400), mismatch (400), weak password (400) in `apps/api/tests/contract/test_reset_password.py`
- [X] T025 [P] [US3] Write failing integration tests for reset-password: all refresh tokens revoked on success, audit record written, second use of same token rejected in `apps/api/tests/integration/test_reset_password.py`

### Implementation for User Story 3

- [X] T026 [US3] Add `POST /v1/auth/reset-password` endpoint to `apps/api/tessera_api/routers/auth.py`: check mismatch + strength first; hash token (sha256); lookup PasswordResetToken by hash; if not found/consumed/expired raise 400 `invalid_or_expired_token`; else mark consumed_at=now, update user password_hash, revoke all refresh tokens for user, write audit `auth.password.reset_completed`, return 204 — depends on T024, T025
- [X] T027 [P] [US3] Add `resetPassword({token, newPassword, confirmNewPassword})` API client function to `apps/web/lib/auth.ts`
- [X] T028 [P] [US3] Create `/reset-password` page: reads `?token=` from URL (shows expired-link state immediately if absent); new-password + confirm inputs with inline strength feedback; on 204 navigate to `/login?reset=success`; on 400 `invalid_or_expired_token` show full-page expired message with link to `/forgot-password` in `apps/web/app/reset-password/page.tsx` — depends on T027
- [X] T029 [US3] Add `?reset=success` banner to `/login` page: dismissible `slate-100/slate-700` info banner "Your password has been reset. Please sign in with your new password." rendered above the form when `reset=success` is in query params in `apps/web/app/login/page.tsx`

**Checkpoint**: All three user stories are fully functional and independently testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Coverage verification, NavBar link, and end-to-end validation.

- [X] T030 Add "Account" link to `apps/web/components/NavBar.tsx` (authenticated-only, links to `/account`, styled with existing nav-item pattern)
- [X] T031 [P] Run `pytest apps/api --cov=tessera_api --cov-report=term-missing` and fix any modules below 85% coverage threshold — target files: `auth/password_strength.py`, `auth/rate_limit.py`, `routers/auth.py` (new endpoints), `adapters/repo.py` (new repository methods)
- [X] T032 [P] Run `pytest packages/core --cov=tessera_core --cov-report=term-missing` and fix any coverage gaps in `services/password_reset.py`
- [X] T033 Run `cd apps/web && npx vitest run` and confirm all existing and new tests pass; add Vitest tests for `forgotPassword`, `changePassword`, `resetPassword` client functions in `apps/web/tests/password.test.ts` if not already covered
- [X] T034 Execute quickstart.md validation scenarios end-to-end against local dev stack and confirm all acceptance criteria pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion (migration must exist before ORM models reference the table) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 completion — can start immediately after
- **US2 (Phase 4)**: Depends on Phase 2 completion — can run in parallel with US1 once Phase 2 is done
- **US3 (Phase 5)**: Depends on Phase 2 completion AND US2 (requires PasswordResetToken to exist in DB from US2)
- **Polish (Phase 6)**: Depends on all desired stories being complete

### User Story Dependencies

- **US1 (P1)**: Depends only on Foundational — no dependencies on other stories
- **US2 (P2)**: Depends only on Foundational — independently implementable alongside US1
- **US3 (P3)**: Depends on Foundational AND US2 (consumes tokens created by US2 flow)

### Within Each User Story

- Tests (TDD) → written and confirmed failing before implementation
- Repository/adapters implemented before endpoints
- API client implemented before frontend page
- Endpoint before frontend (frontend calls the endpoint)

### Parallel Opportunities Within Phase 2

```
T002 (entity) → T005 (ORM model) → T011 (SQL repos)
T003 (port ABCs)              ↗
T004 (EmailPort)              → T012 (email adapter)
T006 (strength tests) → T007 (strength impl)          ← can run concurrently with T008→T009
T008 (service tests)  → T009 (service impl)
T010 (rate limiter)                                    ← fully independent
```

---

## Parallel Example: User Story 1

```bash
# After T013 (contract tests) is written:
# T014 and T016 can be written in parallel:
Task: "Write integration tests in apps/api/tests/integration/test_password_change.py"
Task: "Add changePassword() client to apps/web/lib/auth.ts"

# After T015 (endpoint) is done:
# T017 (frontend page) can proceed:
Task: "Create apps/web/app/account/page.tsx"
```

## Parallel Example: User Story 2

```bash
# After T019 (contract tests) is written:
# T020 (integration tests) and T022 (API client) can be written in parallel:
Task: "Write integration tests in apps/api/tests/integration/test_forgot_password.py"
Task: "Add forgotPassword() to apps/web/lib/auth.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (migration)
2. Complete Phase 2: Foundational (entities, ports, adapters, utilities)
3. Complete Phase 3: User Story 1 (change-password endpoint + account page)
4. **STOP and VALIDATE**: `pytest apps/api`, run quickstart.md Scenario 1
5. Deploy or demo — users can change passwords from account settings

### Incremental Delivery

1. Phase 1 + Phase 2 → Foundation ready
2. Phase 3 (US1) → Password change working → validate → ship as MVP
3. Phase 4 (US2) → Reset request working → validate → ship
4. Phase 5 (US3) → Full recovery flow → validate → ship
5. Phase 6 → Polish + coverage → final ship

### Parallel Team Strategy

With two developers:
- Dev A: Phase 2 foundational tasks T002→T005→T011, T003, T006→T007
- Dev B: Phase 2 utility tasks T004, T008→T009, T010, T012
- Once Phase 2 complete: Dev A takes US1 (Phase 3), Dev B takes US2 (Phase 4)
- US3 (Phase 5) follows after US2

---

## Notes

- [P] tasks = different files, no same-file conflicts, can be executed concurrently
- [Story] label maps each task to its user story for traceability
- Each user story has independently verifiable acceptance criteria from spec.md
- TDD: all test tasks (T006, T008, T013, T014, T019, T020, T024, T025) MUST be written before their corresponding implementation tasks and MUST fail initially
- Commit after each completed task or logical group; run Ruff + Black before each commit (Constitution V)
- The `revoke_all_except()` method in `SqlRefreshTokenRepository` (T011) and `SqlPasswordResetTokenRepository` (T011) are in the same file — implement sequentially, not in parallel
