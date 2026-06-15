# Tasks: JWT Authentication

**Input**: Design documents from `specs/004-jwt-auth/`

**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/auth-api.md ✅ quickstart.md ✅

**Tests**: Included — Constitution Principle IV mandates TDD (NON-NEGOTIABLE). Tests are written first and must fail before implementation begins.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on each other)
- **[Story]**: User story label (US1–US4)
- File paths follow the monorepo layout from plan.md

---

## Phase 1: Setup

**Purpose**: Add the single new dependency and new configuration fields needed by all subsequent phases.

- [X] T001 Add `passlib[bcrypt]>=1.7` to dependencies in `apps/api/pyproject.toml`
- [X] T002 Add `jwt_access_token_expire_minutes`, `jwt_refresh_token_expire_days`, `jwt_algorithm` fields to `Settings` in `apps/api/tessera_api/config.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain entities, database schema, JWT helpers, and repository needed by ALL user stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Add `password_hash: str | None = None` to `User` domain entity in `packages/core/tessera_core/domain/entities.py`
- [X] T004 Add `RefreshToken` domain entity (id, user_id, token_hash, issued_at, expires_at, is_revoked) to `packages/core/tessera_core/domain/entities.py`
- [X] T005 [P] Add `password_hash: Mapped[str | None]` column to `UserModel` in `apps/api/tessera_api/adapters/models.py`
- [X] T006 [P] Add `RefreshTokenModel` (all fields from data-model.md, index on user_id+is_revoked) to `apps/api/tessera_api/adapters/models.py`
- [X] T007 Create Alembic migration `ALTER TABLE users ADD COLUMN password_hash TEXT` + `CREATE TABLE refresh_tokens` in `apps/api/alembic/versions/` (depends on T005, T006)
- [X] T008 Create `apps/api/tessera_api/auth/jwt_auth.py` with `create_access_token`, `verify_access_token`, `create_refresh_token`, `hash_refresh_token` using `joserfc` and `bcrypt`
- [X] T009 Add `SqlRefreshTokenRepository` (create, get_by_hash, revoke, delete_by_user) to `apps/api/tessera_api/adapters/repo.py`
- [X] T010 Create `apps/api/tessera_api/routers/auth.py` with empty router and register it in `apps/api/tessera_api/main.py` under `/v1`

**Checkpoint**: Foundation ready — user story phases can now proceed.

---

## Phase 3: User Story 1 — Authenticate and Receive Token (Priority: P1) 🎯 MVP

**Goal**: Users can register with email/password and log in to receive a JWT access token and refresh token.

**Independent Test**: `POST /v1/auth/register` creates a user; `POST /v1/auth/login` with correct credentials returns `access_token` + `refresh_token`; wrong password returns 401 with `invalid_credentials` (same message as wrong email).

### Tests — User Story 1 (write first, confirm they FAIL before implementing)

- [X] T011 [P] [US1] Write unit tests for `create_access_token`, `verify_access_token`, `hash_refresh_token` in `apps/api/tests/auth/test_jwt_helpers.py`
- [X] T012 [P] [US1] Write integration tests for `POST /v1/auth/register` (success, duplicate email, weak password) in `apps/api/tests/auth/test_auth_register.py`
- [X] T013 [P] [US1] Write integration tests for `POST /v1/auth/login` (success, wrong password, unknown email, inactive account) in `apps/api/tests/auth/test_auth_login.py`

### Implementation — User Story 1

- [X] T014 [US1] Implement `POST /v1/auth/register` in `apps/api/tessera_api/routers/auth.py`: hash password with bcrypt, create `User` record, emit `auth.register` audit event, return 201 (depends on T011–T013)
- [X] T015 [US1] Implement `POST /v1/auth/login` in `apps/api/tessera_api/routers/auth.py`: verify bcrypt hash, call `create_access_token` + `create_refresh_token`, persist refresh token via `SqlRefreshTokenRepository`, emit `auth.login.success` / `auth.login.failure` audit events, return tokens (depends on T014)

**Checkpoint**: User Story 1 fully functional — register + login end-to-end working.

---

## Phase 4: User Story 2 — Access Protected Resources with Token (Priority: P1)

**Goal**: A valid JWT bearer token grants access to all protected endpoints; missing/invalid/expired tokens are rejected.

**Independent Test**: Call `GET /v1/spaces` with valid JWT → 200; call without any credentials → 401; call with a tampered token → 401.

### Tests — User Story 2 (write first, confirm they FAIL before implementing)

- [X] T016 [P] [US2] Write integration tests for JWT-bearer access on a representative protected endpoint (`GET /v1/spaces`): valid token → 200, missing → 401, expired → 401 `token_expired`, tampered → 401 `invalid_token` in `apps/api/tests/auth/test_jwt_protection.py`

### Implementation — User Story 2

- [X] T017 [US2] Update `require_user` in `apps/api/tessera_api/auth/oidc.py` to check `Authorization: Bearer` header first via `verify_access_token`; fall back to session cookie for backward compatibility (depends on T016)

**Checkpoint**: User Story 2 functional — all existing protected endpoints now accept JWT bearer tokens.

---

## Phase 5: User Story 3 — Refresh Expired Access Token (Priority: P2)

**Goal**: A valid refresh token exchanges for a new access token and a new refresh token; the old refresh token is immediately invalidated.

**Independent Test**: Use a refresh token returned from login → `POST /v1/auth/refresh` → receive new tokens; attempt to reuse the old refresh token → 401.

### Tests — User Story 3 (write first, confirm they FAIL before implementing)

- [X] T018 [P] [US3] Write integration tests for `POST /v1/auth/refresh`: valid token → new tokens issued + old token invalidated, replay of old token → 401, expired token → 401 in `apps/api/tests/auth/test_auth_refresh.py`

### Implementation — User Story 3

- [X] T019 [US3] Implement `POST /v1/auth/refresh` in `apps/api/tessera_api/routers/auth.py`: look up refresh token by hash, verify not revoked + not expired, revoke old token, issue new access + refresh tokens, persist new refresh token, emit `auth.token.refresh` audit event (depends on T018)

**Checkpoint**: User Story 3 functional — token refresh with rotation working.

---

## Phase 6: User Story 4 — Log Out and Invalidate Tokens (Priority: P2)

**Goal**: Explicit logout deletes the refresh token so it can no longer be used to issue new access tokens.

**Independent Test**: Log out with a valid access token + refresh token → 204; attempt to use that refresh token afterward → 401.

### Tests — User Story 4 (write first, confirm they FAIL before implementing)

- [X] T020 [P] [US4] Write integration tests for `POST /v1/auth/logout`: authenticated logout → 204 + refresh token rejected afterward; unauthenticated logout → 401 in `apps/api/tests/auth/test_auth_logout.py`

### Implementation — User Story 4

- [X] T021 [US4] Implement `POST /v1/auth/logout` in `apps/api/tessera_api/routers/auth.py`: require valid JWT bearer via updated `require_user`, delete the provided refresh token from `refresh_tokens` table via `SqlRefreshTokenRepository`, emit `auth.logout` audit event, return 204 (depends on T020)

**Checkpoint**: All four user stories functional — full auth lifecycle working.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T022 [P] Run `pytest --cov=tessera_api --cov-report=term-missing` and confirm coverage ≥ 85% on all new modules in `apps/api/`
- [ ] T023 [P] Run all quickstart.md validation scenarios (Scenarios 1–10) against a local stack and confirm all pass
- [X] T024 Run `ruff check` and `black --check` on all new/modified files; fix any violations

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — blocks all user stories
- **Phases 3–6 (User Stories)**: All depend on Phase 2 completion; P1 stories first, then P2 stories
- **Phase 7 (Polish)**: Depends on all desired stories being complete

### User Story Dependencies

- **US1 (P1)**: Depends only on Phase 2 — no story-to-story dependency
- **US2 (P1)**: Depends on Phase 2; US1 must be complete (needs tokens to test access)
- **US3 (P2)**: Depends on Phase 2 + US1 (needs login to get a refresh token)
- **US4 (P2)**: Depends on Phase 2 + US1 + US3 (needs refresh tokens to test revocation)

### Within Each Phase

- Tests MUST be written first and confirmed FAILING before implementation begins (TDD)
- Models/entities before services
- Services before endpoints
- Commit after each task or logical group

### Parallel Opportunities

- T003 + T004 can run sequentially (same file)
- T005 + T006 can run in parallel (different sections of same file, but careful of conflicts — do T005 then T006 or merge)
- T011 + T012 + T013 can run in parallel (different test files)
- T016 runs alone in US2 (single file)
- T018 runs alone in US3 (single file)
- T020 runs alone in US4 (single file)
- T022 + T023 can run in parallel in Phase 7

---

## Parallel Example: Phase 2 Foundational

```bash
# These can run in parallel (different files):
Task T003+T004: "Add User.password_hash + RefreshToken entity to packages/core/tessera_core/domain/entities.py"
Task T008: "Create apps/api/tessera_api/auth/jwt_auth.py"
Task T009: "Add SqlRefreshTokenRepository to apps/api/tessera_api/adapters/repo.py"

# After T003+T004 complete:
Task T005+T006: "Add UserModel.password_hash + RefreshTokenModel to apps/api/tessera_api/adapters/models.py"

# After T005+T006:
Task T007: "Create Alembic migration"
```

## Parallel Example: User Story 1 Tests

```bash
# All three test files can be written in parallel:
Task T011: "apps/api/tests/auth/test_jwt_helpers.py"
Task T012: "apps/api/tests/auth/test_auth_register.py"
Task T013: "apps/api/tests/auth/test_auth_login.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 (register + login)
4. Complete Phase 4: US2 (JWT protection on existing endpoints)
5. **STOP and VALIDATE**: Run quickstart.md Scenarios 1–5 and 9
6. Ship — the core auth lifecycle is working

### Incremental Delivery

1. Setup + Foundational → skeleton ready
2. US1 → users can register and log in (MVP)
3. US2 → protected endpoints secured (MVP complete)
4. US3 → token refresh (UX improvement)
5. US4 → logout (security closure)
6. Polish → coverage + linting gate

---

## Notes

- [P] tasks = different files or truly independent, safe to run in parallel
- TDD is NON-NEGOTIABLE per constitution — every test task MUST precede its paired implementation task
- `require_user` update (T017) is additive: session cookie path must remain functional for backward compat
- Signing key is `settings.secret_key` — no new secret needed
- `RefreshTokenModel.token_hash` stores SHA-256 of the raw token; raw token is never persisted
