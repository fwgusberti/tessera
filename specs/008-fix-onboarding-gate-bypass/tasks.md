# Tasks: Fix Onboarding Gate Bypass

**Input**: Design documents from `specs/008-fix-onboarding-gate-bypass/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, quickstart.md ✅

**Note**: This is a single-file bug fix. All three user stories (US1/US2/US3) are resolved by the same code change — adding three exempt patterns to `require_onboarding_complete` in `apps/api/tessera_api/auth/bearer.py`. Tasks are TDD-ordered per Constitution IV.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1/US2/US3)

---

## Phase 1: Setup

**Purpose**: Confirm test harness and identify the exact lines to change.

- [X] T001 Read `apps/api/tessera_api/auth/bearer.py` lines 51–90 to confirm current `exempt_patterns` list and the three missing entries (see research.md)
- [X] T002 Read `apps/api/tests/integration/test_companies.py` to understand the existing `_make_jwt_header` and `_make_progress` helpers (will be reused in the new test file)

---

## Phase 2: Foundational — Write Failing Tests (TDD)

**Purpose**: Write tests that capture the three broken scenarios AND the regression guard. All four tests MUST fail before the fix is applied.

**⚠️ CRITICAL**: Constitution IV requires tests written and confirmed failing before implementation.

- [X] T003 Create `apps/api/tests/integration/test_onboarding_gate.py` with the `_make_jwt_header` helper (reuse pattern from `test_companies.py`) and mock helpers that simulate a mid-onboarding user (`OnboardingProgress.completed_at = None`)
- [X] T004 [US1] In `test_onboarding_gate.py`, add `TestOnboardingGateExemptions::test_create_company_allowed_mid_onboarding` — mocks `SqlOnboardingRepository.get_by_user_id` to return progress with `completed_at=None`, calls `POST /v1/companies`, asserts status is NOT 403
- [X] T005 [P] [US2] In `test_onboarding_gate.py`, add `test_get_suggestions_allowed_mid_onboarding` — same mock, calls `GET /v1/companies/suggestions`, asserts NOT 403
- [X] T006 [P] [US3] In `test_onboarding_gate.py`, add `test_join_company_allowed_mid_onboarding` — same mock, calls `POST /v1/companies/{uuid}/join`, asserts NOT 403
- [X] T007 In `test_onboarding_gate.py`, add `TestOnboardingGateRegression::test_non_exempt_endpoint_still_blocked` — same mid-onboarding mock, calls `GET /v1/companies/{uuid}/join-requests`, asserts 403 with `code=onboarding_required`
- [X] T008 Run `cd apps/api && uv run pytest tests/integration/test_onboarding_gate.py -v` and confirm T004–T007 all FAIL (403 returned for the exempt paths, proving the bug exists)

**Checkpoint**: Four failing tests confirm the bug is reproduced. Implementation can now proceed.

---

## Phase 3: User Stories 1, 2 & 3 — Fix the Gate (P1) 🎯 MVP

**Goal**: Add three missing exemptions to `require_onboarding_complete` so `POST /companies`, `GET /companies/suggestions`, and `POST /companies/{id}/join` are accessible during onboarding.

**Independent Test**: Run `uv run pytest tests/integration/test_onboarding_gate.py -v` — all 4 tests must pass.

### Implementation

- [X] T009 [US1] [US2] [US3] In `apps/api/tessera_api/auth/bearer.py`, extend the `exempt_patterns` list (lines ~63–68) with three new entries:
  - `(r"^/v1/companies$", {"POST"})` — create company
  - `(r"^/v1/companies/suggestions$", {"GET"})` — get suggestions
  - `(r"^/v1/companies/[^/]+/join$", {"POST"})` — join company
  
  Match the existing entry structure: each entry is a `(pattern, allowed_methods_set)` tuple checked with `re.match(pattern, path) and request.method in allowed_methods`.

**Checkpoint**: Run the failing tests from Phase 2 — all 4 should now pass.

---

## Phase 4: Polish & Verification

**Purpose**: Confirm no regressions in the broader test suite.

- [X] T010 Run `cd apps/api && uv run pytest tests/ -v` and confirm no regressions in `test_companies.py`, `test_onboarding.py`, or any other integration test
- [X] T011 Run `uv run ruff check tessera_api/auth/bearer.py` and `uv run black --check tessera_api/auth/bearer.py` — fix any lint/format issues
- [ ] T012 Manually verify the fix with the quickstart.md end-to-end steps: register user → complete profile → call `POST /v1/companies` → confirm 201 (not 403)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — T003 must precede T004–T007
- **Implementation (Phase 3)**: T009 can start after confirming T008 shows failing tests
- **Polish (Phase 4)**: Depends on Phase 3 completion

### Parallel Opportunities

- T005 and T006 are independent of each other (different test methods) — write in parallel
- T010 and T011 can run in parallel after T009

---

## Parallel Example: Phase 2 (Test Writing)

```bash
# After T003 (file created), write US2 and US3 tests in parallel:
Task: "test_get_suggestions_allowed_mid_onboarding in test_onboarding_gate.py"
Task: "test_join_company_allowed_mid_onboarding in test_onboarding_gate.py"
```

---

## Implementation Strategy

### MVP (Only path needed)

1. Complete Phase 1: Read existing code (5 min)
2. Complete Phase 2: Write 4 failing tests (15 min)
3. Complete Phase 3: Add 3 lines to bearer.py (5 min)
4. **VALIDATE**: All 4 tests pass, suite is green
5. Done — no further stories

---

## Notes

- T009 is the entire fix — three lines added to one list in one file
- The pattern matching in `require_onboarding_complete` uses `re.match` (anchored at start) and a set of allowed HTTP methods; match the existing pattern exactly
- Do NOT change the router registration in `main.py` — the fix lives entirely in the guard function
- [P] tasks = different methods/test classes in the same file, safe to write in parallel
