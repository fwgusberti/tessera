---

description: "Task list for Fix Missing User Identity in Session After Company Activation"
---

# Tasks: Fix Missing User Identity in Session After Company Activation

**Input**: Design documents from `/specs/033-fix-session-missing-sub/`

**Branch**: `033-fix-session-missing-sub` | **Date**: 2026-06-22

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Exact file paths are included in all task descriptions

---

## Phase 1: User Story 1 — Activate Company Without Crashing (Priority: P1) 🎯 MVP

**Goal**: Fix `activate_company` in `routers/companies.py` so that a JWT-only user (no prior session) gets a complete session user record (`sub`, `email`, `is_admin`, `active_company_id`) after calling the activate-company endpoint. Subsequent session-based requests no longer crash with `KeyError: 'sub'`.

**Independent Test**: Authenticate via JWT only → call `POST /v1/companies/{id}/activate` → make a request to a protected route through the onboarding guard → must return 200/403 (not 500).

### Tests for User Story 1 ⚠️ Write FIRST — verify they FAIL before implementing

- [X] T001 [P] [US1] Add `TestActivateCompanySession` class with `test_jwt_user_activate_stores_complete_identity` in `apps/api/tests/integration/test_companies.py` — asserts session `"user"` dict contains `sub`, `email`, `is_admin`, and `active_company_id` after a JWT-only user calls activate-company
- [X] T002 [P] [US1] Add `test_activate_company_preserves_existing_session_fields` to `TestActivateCompanySession` in `apps/api/tests/integration/test_companies.py` — asserts that an existing session with `sub` and extra fields is not overwritten; only `active_company_id` is updated

### Implementation for User Story 1

- [X] T003 [US1] Fix session user record creation in `apps/api/tessera_api/routers/companies.py` lines 711–713: replace the empty `{}` initializer with `{"sub": user_info["sub"], "email": user_info.get("email", ""), "is_admin": user_info.get("is_admin", False)}` inside the `if "user" not in request.session` guard

**Checkpoint**: `python -m pytest apps/api/tests/integration/test_companies.py::TestActivateCompanySession -v` — both T001 and T002 tests must pass. US1 is fully functional.

---

## Phase 2: User Story 2 — Onboarding Guard Handles Incomplete Sessions Gracefully (Priority: P2)

**Goal**: Add a defensive `if "sub" not in user_info` guard in `require_onboarding_complete` in `auth/bearer.py` so that any malformed or legacy session cookie (missing `sub`) returns HTTP 401 with `invalid_session` instead of raising an unhandled 500.

**Independent Test**: Inject a session cookie with `{"active_company_id": "..."}` but no `sub` → hit any route guarded by `require_onboarding_complete` → must return 401 with `{"error": {"code": "invalid_session", ...}}`, never a 500.

### Tests for User Story 2 ⚠️ Write FIRST — verify they FAIL before implementing

- [X] T004 [P] [US2] Add `TestOnboardingGateIncompleteSession` class with `test_incomplete_session_returns_401_not_500` in `apps/api/tests/integration/test_onboarding_gate.py` — injects session `{"user": {"active_company_id": "<uuid>"}}` (no `sub`) and asserts HTTP 401 with `invalid_session` error code
- [X] T005 [P] [US2] Add `test_complete_session_after_activate_passes_guard` to `TestOnboardingGateIncompleteSession` in `apps/api/tests/integration/test_onboarding_gate.py` — activates company as JWT user (session now has `sub`), hits a guarded route, asserts no 500 (SC-001 regression test)

### Implementation for User Story 2

- [X] T006 [US2] Add `if "sub" not in user_info` guard in `apps/api/tessera_api/auth/bearer.py` inside `require_onboarding_complete`, immediately after the `except HTTPException: return` block — raise `HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error": {"code": "invalid_session", "message": "Incomplete session — re-authenticate"}})` when `sub` is missing

**Checkpoint**: `python -m pytest apps/api/tests/integration/test_onboarding_gate.py::TestOnboardingGateIncompleteSession -v` — both T004 and T005 tests must pass. US2 is fully functional.

---

## Phase 3: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates and regression validation before merging

- [X] T007 [P] Run Ruff linter and Black formatter in `apps/api/` — both must exit 0 (`ruff check apps/api/tessera_api/routers/companies.py apps/api/tessera_api/auth/bearer.py && black --check apps/api/tessera_api/routers/companies.py apps/api/tessera_api/auth/bearer.py`)
- [X] T008 [P] Run full regression suite for affected modules: `python -m pytest apps/api/tests/integration/test_onboarding_gate.py apps/api/tests/integration/test_companies.py -v` — all pre-existing tests must continue to pass (no regressions in SC-003)
- [X] T009 Run quickstart.md validation: authenticate via JWT, activate company, hit protected route — confirm 200/403 response (not 500), per `specs/033-fix-session-missing-sub/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (US1)**: No dependencies — start immediately
- **Phase 2 (US2)**: Can start after Phase 1 completes; US2 is defense-in-depth for the same flow
- **Phase 3 (Polish)**: Depends on both Phase 1 and Phase 2 complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies — can start immediately
- **User Story 2 (P2)**: Logically independent (different file) but sequenced after US1 to ensure the root-cause fix is confirmed first

### Within Each User Story

- Tests (T001–T002, T004–T005) MUST be written and confirmed **failing** before their implementation tasks
- T003 depends on T001 and T002 being written
- T006 depends on T004 and T005 being written

### Parallel Opportunities

- T001 and T002 can be written in parallel (same class, different methods — coordinate to avoid conflicts)
- T004 and T005 can be written in parallel (same class, different methods)
- T007 and T008 run in parallel in Phase 3

---

## Parallel Example: User Story 1

```bash
# Write both failing tests for US1 in parallel (coordinate on same file):
Task T001: test_jwt_user_activate_stores_complete_identity
Task T002: test_activate_company_preserves_existing_session_fields

# Then implement (single file change):
Task T003: Fix companies.py lines 711–713
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Write T001 and T002 — confirm they fail
2. Implement T003 — fix the root cause in `companies.py`
3. **STOP and VALIDATE**: `pytest apps/api/tests/integration/test_companies.py::TestActivateCompanySession -v`
4. SC-001 and SC-002 are now met for the primary fix

### Incremental Delivery

1. Complete Phase 1 (US1) → root cause fixed, crash eliminated
2. Complete Phase 2 (US2) → defense-in-depth guard added, SC-004 met
3. Complete Phase 3 (Polish) → Ruff/Black pass, full regression clean

---

## Notes

- Total files changed: 2 (`routers/companies.py`, `auth/bearer.py`) — no migrations, no new dependencies
- No new imports required in either file (`status` already imported in `bearer.py`)
- Session priority order (session first, JWT second) must not be changed — verified by T002/T005
- `[P]` tasks touch different files or are parallelizable within the same file with coordination
