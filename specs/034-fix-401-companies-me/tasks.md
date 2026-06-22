# Tasks: Fix 401 on Companies/Me After Login

**Input**: Design documents from `/specs/034-fix-401-companies-me/`

**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, contracts/companies-me.md ✓, quickstart.md ✓

**Tests**: Included — TDD required per constitution (new failing tests before fix).

**Organization**: Tasks are grouped by user story. This is a surgical two-file fix (<10 lines total); no setup or foundational phases needed.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Exact file paths are included in all descriptions

---

## Phase 1: User Story 1 — Returning User Can Access App After Login (Priority: P1) 🎯 MVP

**Goal**: Fix `require_user` in `oidc.py` so that a stale session cookie without `sub` falls through to JWT Bearer auth, eliminating the 401 loop for returning users.

**Independent Test**: Create a test client with a stale session cookie (contains only `active_company_id`, no `sub`) plus a valid JWT Bearer header and assert `GET /v1/companies/me` returns 200. Separately assert that stale session + no JWT returns 401 (no accidental open access).

### Tests for User Story 1 (TDD — write FIRST, ensure they FAIL before implementation)

- [X] T001 [US1] Write `TestGetMyCompaniesAuth` class with `test_stale_session_with_valid_jwt_returns_200` in `apps/api/tests/integration/test_companies.py` — encode a session cookie with only `{"active_company_id": "<uuid>"}` using `itsdangerous.TimestampSigner`, pass with a valid JWT Bearer, assert 200
- [X] T002 [P] [US1] Write `TestStaleSessionNoJwt` class with `test_stale_session_no_jwt_returns_401` in `apps/api/tests/integration/test_onboarding_gate.py` — encode same stale session cookie but no `Authorization` header, assert `GET /v1/companies/me` returns 401 (verifies fix does not open unauthenticated access)

### Implementation for User Story 1

- [X] T003 [US1] Fix `require_user` in `apps/api/tessera_api/auth/oidc.py` — change `if user:` to `if user and user.get("sub"):` on the session-return branch (line ~54), so incomplete sessions fall through to JWT Bearer auth

**Checkpoint**: Run `uv run pytest tests/integration/test_companies.py::TestGetMyCompaniesAuth::test_stale_session_with_valid_jwt_returns_200 tests/integration/test_onboarding_gate.py::TestStaleSessionNoJwt -v` — both must pass. Stale session + valid JWT → 200. Stale session + no JWT → 401.

---

## Phase 2: User Story 2 — Company List Loads During and After Onboarding (Priority: P2)

**Goal**: Add `GET /v1/companies/me` to the onboarding-gate exempt list in `bearer.py` so mid-onboarding users get an empty list (200) instead of 403.

**Independent Test**: Call `GET /v1/companies/me` with a valid JWT for a user who has not completed onboarding; assert 200 with `{"companies": []}`.

### Tests for User Story 2 (TDD — write FIRST, ensure they FAIL before implementation)

- [X] T004 [US2] Add `test_mid_onboarding_user_returns_empty_list` to the `TestGetMyCompaniesAuth` class in `apps/api/tests/integration/test_companies.py` — use a valid JWT for a user with no company memberships and no completed onboarding, assert 200 and `companies == []`

### Implementation for User Story 2

- [X] T005 [US2] Add `(r"^/v1/companies/me$", {"GET"}),` to `exempt_patterns` in `require_onboarding_complete` in `apps/api/tessera_api/auth/bearer.py` (after line ~67 in the existing exempt list)

**Checkpoint**: Run `uv run pytest tests/integration/test_companies.py::TestGetMyCompaniesAuth -v` — all tests in the class must pass, including the new mid-onboarding test.

---

## Phase 3: Polish & Regression Verification

**Purpose**: Confirm no regressions in the onboarding gate for endpoints that remain blocked.

- [X] T006 [P] Run full regression suite: `cd apps/api && uv run pytest tests/ -v --tb=short` — verify `TestOnboardingGateRegression::test_list_join_requests_blocked_mid_onboarding` still returns 403 and `TestOnboardingGateIncompleteSession::test_incomplete_session_returns_401_not_500` still returns 401
- [X] T007 [P] Run linting and formatting: `cd apps/api && uv run ruff check . && uv run black --check .` — must pass with no errors

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (US1)**: Can start immediately — no blocking prerequisites
- **Phase 2 (US2)**: Can start after Phase 1 is complete (T004 adds to the same test class as T001); OR can be implemented in parallel if T004 goes in its own class
- **Phase 3 (Polish)**: Depends on both Phase 1 and Phase 2 being complete

### Within Each User Story

- Tests MUST be written and confirmed failing before implementation
- T001 before T003 (stale-session test before oidc.py fix)
- T002 can run in parallel with T001 (different file)
- T004 before T005 (mid-onboarding test before bearer.py fix)

### Parallel Opportunities

- T001 and T002 can run in parallel (different test files)
- T003 and T004 can run in parallel (different files: oidc.py vs test_companies.py)
- T006 and T007 can run in parallel

---

## Parallel Example: Phase 1

```bash
# Write both failing tests simultaneously (different files):
Task T001: TestGetMyCompaniesAuth.test_stale_session_with_valid_jwt_returns_200 in test_companies.py
Task T002: TestStaleSessionNoJwt.test_stale_session_no_jwt_returns_401 in test_onboarding_gate.py

# Then apply the fix:
Task T003: Fix require_user in oidc.py
```

---

## Implementation Strategy

### MVP (Phase 1 Only — US1)

1. Write T001 + T002 (parallel) — tests fail
2. Apply T003 — fix `require_user`
3. Confirm T001 and T002 pass
4. **STOP and VALIDATE**: `GET /companies/me` with stale session + JWT → 200; without JWT → 401

### Full Fix (Both Stories)

1. MVP above
2. Write T004 — test fails (403 for mid-onboarding)
3. Apply T005 — add exempt pattern
4. Confirm all `TestGetMyCompaniesAuth` tests pass
5. Run T006 + T007 (parallel) — regression and lint

---

## Notes

- Session encoding for tests: use `itsdangerous.TimestampSigner` (see `TestOnboardingGateIncompleteSession` for pattern)
- Test marker: `@pytest.mark.anyio` (API pkg uses anyio, not pytest-asyncio)
- Use `fastapi.testclient.TestClient` (sync) for integration tests
- No migrations, no new dependencies, no new endpoints
- [P] tasks = different files, no shared state conflicts
