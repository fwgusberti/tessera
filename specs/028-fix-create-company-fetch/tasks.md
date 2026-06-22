# Tasks: Fix Create Company Button Network Error

**Input**: Design documents from `/specs/028-fix-create-company-fetch/`

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

**Organization**: Tasks are grouped by user story. US1 is the MVP — the CORS fix
alone resolves the end-user-facing bug. US2 is polish that makes failure messages
actionable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Constitution Principle IV is non-negotiable: write the failing test, confirm it
  fails, then implement.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new project structure is required — this is a targeted bug fix.
The existing test infrastructure (pytest/anyio for API, Vitest for web) is in place.

*(No tasks — existing infrastructure is sufficient.)*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No new foundational layer is required. The `POST /v1/companies`
route and the `api.ts` client already exist correctly; only configuration and
error-handling are being fixed.

*(No tasks — proceed directly to user stories.)*

---

## Phase 3: User Story 1 — Create Company Successfully (Priority: P1) 🎯 MVP

**Goal**: The "Create Company" button reaches the backend and the company is
created. No "Failed to fetch" error appears under normal operating conditions.

**Independent Test**: Send an OPTIONS preflight to `POST /v1/companies` from
origin `http://localhost:3000`; confirm the response echoes the exact origin (not
`*`) and includes `Access-Control-Allow-Credentials: true`. Then POST a valid
payload; confirm a 201 response and a new company row in the database.

### Tests for US1 (TDD — write first, must fail before T002) ⚠️

- [X] T001 [US1] Add CORS preflight integration test to `apps/api/tests/integration/test_companies.py`: send OPTIONS to `/v1/companies` with `Origin: http://localhost:3000` header and assert `Access-Control-Allow-Origin == "http://localhost:3000"` and `Access-Control-Allow-Credentials == "true"` (confirm test fails before fix)

### Implementation for US1

- [X] T002 [US1] Fix CORS config in `apps/api/tessera_api/main.py`: replace `allow_origins=["*"] if settings.environment == "development" else []` with `allow_origins=[settings.frontend_url]` to use the explicit configured origin in all environments (confirm T001 now passes)

**Checkpoint**: `pytest apps/api/tests/integration/test_companies.py` passes; OPTIONS
preflight against the running stack returns an explicit origin, not `*`.

---

## Phase 4: User Story 2 — Clear Error Feedback on Real Failures (Priority: P2)

**Goal**: When a genuine network failure occurs (server down, offline), the user
sees a human-readable message such as "Could not reach the server. Please check
your connection and try again." instead of the raw browser `TypeError: Failed to fetch`.

**Independent Test**: In a unit test, stub `fetch` to throw a `TypeError`; call the
`api.post()` client method; assert the caught error message does NOT contain
"Failed to fetch" and does contain actionable guidance.

### Tests for US2 (TDD — write first, must fail before T004) ⚠️

- [X] T003 [US2] Create `apps/web/tests/api-network-error.test.ts`: mock global `fetch` to throw `new TypeError("Failed to fetch")`; call `api.post("/v1/companies", { name: "X" })` via the `request` helper; assert the rejected error message is the user-friendly string (confirm test fails before fix)

### Implementation for US2

- [X] T004 [US2] Wrap the `fetch()` call in `apps/web/lib/api.ts`'s `request()` function with a `try/catch` that catches `TypeError` and re-throws `new Error("Could not reach the server. Please check your connection and try again.")`, leaving all other error types to propagate unchanged (confirm T003 now passes)

**Checkpoint**: `npm test` in `apps/web` passes; all existing tests still green.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Regression validation and end-to-end verification against the running stack.

- [X] T005 [P] Run full API test suite `cd apps/api && pytest` and confirm 0 failures, coverage ≥ 85 %
- [X] T006 [P] Run full web test suite `cd apps/web && npm test` and confirm 0 failures
- [X] T007 Run quickstart scenarios from `specs/028-fix-create-company-fetch/quickstart.md` against the local stack: OPTIONS preflight curl, end-to-end form submission, and server-down friendly-error scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 3 (US1)**: No external dependencies — start immediately
  - T001 must precede T002 (TDD order)
- **Phase 4 (US2)**: No dependency on US1 — can start independently or in parallel
  - T003 must precede T004 (TDD order)
- **Phase 5 (Polish)**: Depends on T002 and T004 both complete

### User Story Dependencies

- **US1 (P1)**: Independent — CORS config touches only `main.py`
- **US2 (P2)**: Independent — error handling touches only `api.ts`
- US1 and US2 touch different files; their implementation tasks can run in parallel

### Within Each User Story

- Test task MUST be written and confirmed-failing before implementation task
- T001 → T002 (US1)
- T003 → T004 (US2)
- T005, T006, T007 after both stories complete

### Parallel Opportunities

- T001 and T003 can be written in parallel (different codebases, different files)
- T002 and T004 can be implemented in parallel after their respective tests are failing
- T005 and T006 can run in parallel

---

## Parallel Example: US1 + US2 together

```bash
# Parallel: write both failing tests simultaneously
Task T001: Add CORS preflight test to apps/api/tests/integration/test_companies.py
Task T003: Create apps/web/tests/api-network-error.test.ts

# After confirming both tests fail, implement fixes in parallel:
Task T002: Fix CORS config in apps/api/tessera_api/main.py
Task T004: Wrap fetch() in apps/web/lib/api.ts

# After both fixes, validate in parallel:
Task T005: cd apps/api && pytest
Task T006: cd apps/web && npm test
```

---

## Implementation Strategy

### MVP (US1 only — 2 tasks)

1. T001 — write failing CORS test
2. T002 — fix CORS config (makes T001 pass + unblocks all users)
3. **STOP and VALIDATE**: run OPTIONS curl, run integration tests, test in browser

### Full Fix (US1 + US2 — 4 tasks)

1. T001 + T003 in parallel (write failing tests)
2. T002 + T004 in parallel (implement fixes)
3. T005 + T006 + T007 (validate)

### Estimated scope

- T001: ~10 lines (one test function)
- T002: ~2 lines changed in `main.py`
- T003: ~20 lines (one test file with fetch mock)
- T004: ~8 lines changed in `api.ts`
- Total diff: < 50 lines across 4 files

---

## Notes

- [P] tasks = different files, no blocking dependencies
- TDD is non-negotiable (Constitution IV): confirm the test is RED before writing code
- `settings.frontend_url` already defaults to `"http://localhost:3000"` — no new env
  var or config key is introduced
- No database migration, no new domain entity, no new API endpoint
- After T002 the `getSuggestions()` call on the company page will also start working
  correctly (it was silently failing for the same CORS reason)
