---

description: "Task list for Enrollment Admin Role Assignment (032)"
---

# Tasks: Enrollment Admin Role Assignment

**Input**: Design documents from `/specs/032-enrollment-admin-role/`

**Prerequisites**: plan.md, spec.md, data-model.md, contracts/onboarding.md, quickstart.md

**Tests**: Constitution IV (TDD) is NON-NEGOTIABLE — failing tests MUST be written and confirmed failing before each implementation task.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Exact file paths are included in every description

---

## Phase 1: Setup

**Purpose**: Create the database migration — the only setup artifact this feature requires.

- [X] T001 Create Alembic migration `db/migrations/versions/0008_onboarding_company_id.py` — `ALTER TABLE onboarding_progress ADD COLUMN company_id UUID REFERENCES companies(id) ON DELETE SET NULL`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain entity and port signature updates that ALL adapter and router changes depend on. Both can be done in parallel (different files).

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Add `company_id: UUID | None = None` field to `OnboardingProgress` dataclass in `packages/core/tessera_core/domain/entities.py`
- [X] T003 [P] Add `company_id: UUID | None = None` keyword argument to `advance_step` abstract method in `packages/core/tessera_core/ports/repositories.py`
- [X] T004 [P] Add `company_id` nullable `UUID` column (FK → `companies.id`) to `OnboardingProgressModel` in `apps/api/tessera_api/adapters/models.py`

**Checkpoint**: Foundation ready — adapter and router implementation can now begin.

---

## Phase 3: User Story 1 — Company Creator Receives Admin Role on Enrollment Completion (Priority: P1) 🎯 MVP

**Goal**: A user who creates a company during enrollment is automatically assigned `CompanyRole.ADMIN` the moment `POST /onboarding/complete` is called, idempotently and without any manual step.

**Independent Test**: Create a fresh user, complete enrollment with a new company, call `GET /companies/me` — role MUST be `"admin"` before any other action.

### Tests for User Story 1 ⚠️ Write FIRST — confirm FAILING before implementation

- [X] T005 [US1] Write failing integration tests `test_complete_assigns_admin_for_creator`, `test_complete_idempotent_admin_already_exists`, `test_complete_does_not_assign_admin_for_joiner`, `test_complete_no_company_join_method_safe` in `apps/api/tests/integration/test_onboarding.py`
- [X] T006 [P] [US1] Write failing unit test for idempotent `add_membership` (no duplicate on second call) in `apps/api/tests/unit/test_company_repo.py`

### Implementation for User Story 1

- [X] T007 [US1] Update `SqlOnboardingRepository.advance_step` to accept and persist `company_id`, and update `_from_model` to populate `OnboardingProgress.company_id` in `apps/api/tessera_api/adapters/repo.py`
- [X] T008 [US1] Pass `company_id=company.id` to `advance_step` call inside `create_company` in `apps/api/tessera_api/routers/companies.py`
- [X] T009 [US1] Extend `complete_onboarding` with idempotent admin membership block (`get_membership` → conditional `add_membership`) and audit log for the assignment event in `apps/api/tessera_api/routers/onboarding.py`

**Checkpoint**: Run `cd apps/api && uv run pytest tests/integration/test_onboarding.py tests/unit/test_company_repo.py -v` — all tests from T005 and T006 MUST pass.

---

## Phase 4: User Story 2 — Company Has At Least One Admin After Enrollment (Priority: P1)

**Goal**: Every company created through enrollment immediately has exactly one admin (its creator) and the system guarantees this invariant holds — no company exists without an admin at any point.

**Independent Test**: After enrollment, query `company_memberships WHERE company_id = <new_company_id>` — there MUST be exactly one row with `role = 'admin'`.

### Tests for User Story 2 ⚠️ Write FIRST — confirm FAILING before implementation

- [X] T010 [P] [US2] Write failing cross-tenant isolation test: user authenticated as Company A calling `POST /onboarding/complete` MUST NOT create admin membership on Company B in `apps/api/tests/integration/test_onboarding.py`
- [X] T011 [P] [US2] Extend `test_onboarding_gate.py` with admin invariant assertion: immediately after company creation, `company_memberships` for the new company MUST contain exactly one row with `role = ADMIN` in `apps/api/tests/integration/test_onboarding_gate.py`

### Implementation for User Story 2

No new implementation files required — US2's invariant is fully enforced by the Phase 3 implementation. This phase only adds the verification tests mandated by the constitution (tenant isolation + gate).

**Checkpoint**: Run `cd apps/api && uv run pytest tests/integration/test_onboarding.py tests/integration/test_onboarding_gate.py -v` — all tests MUST pass.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across the full test suite and end-to-end quickstart scenarios.

- [X] T012 [P] Run full test suite and confirm statement coverage ≥ 85% via `cd apps/api && uv run pytest tests/ -v --cov`
- [X] T013 Run quickstart.md validation scenarios (Scenario 1 golden path, Scenario 2 idempotency, Scenario 3 joiner, Scenario 4 interrupted enrollment) against running API

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: No dependencies — start immediately in parallel with T001
- **User Story 1 (Phase 3)**: Depends on Phase 2 (T002, T003, T004) complete
- **User Story 2 (Phase 4)**: Depends on Phase 3 implementation complete (T007, T008, T009)
- **Polish (Phase 5)**: Depends on all prior phases complete

### Within Each Phase

- Phases 1 and 2 can run concurrently (T001 is independent; T002/T003/T004 are parallel)
- Phase 3 tests (T005, T006) should be written before implementation (T007–T009)
  - T005 and T006 are parallel (different files)
  - T007 must complete before T008 and T009 (T008/T009 are parallel with each other)
- Phase 4 tests (T010, T011) are parallel (different files)
- Phase 5 tasks (T012, T013) are sequential after all tests pass

### Parallel Opportunities

```bash
# Phase 2 — all three can run simultaneously:
Task T002: Add company_id to OnboardingProgress entity
Task T003: Update advance_step port signature
Task T004: Add company_id column to adapter model

# Phase 3 — tests first (T005 and T006 are parallel):
Task T005: Integration tests in test_onboarding.py
Task T006: Unit test in test_company_repo.py

# Phase 3 — then implementation (T008 and T009 are parallel after T007):
Task T007 → Task T008 (companies.py)
         → Task T009 (onboarding.py)

# Phase 4 — both tests are parallel:
Task T010: Isolation test in test_onboarding.py
Task T011: Gate test in test_onboarding_gate.py
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. Complete Phase 1: Create migration
2. Complete Phase 2: Domain entity + port + adapter model
3. Complete Phase 3: US1 tests (failing) → US1 implementation → verify passing
4. **STOP and VALIDATE**: `uv run pytest tests/integration/test_onboarding.py -v` all green
5. Deploy/demo if ready

### Incremental Delivery

1. Phase 1 + Phase 2 → Foundation ready
2. Phase 3: US1 → Creator gets admin → validate → deploy (MVP)
3. Phase 4: US2 → Isolation + gate tests → validate → deploy
4. Phase 5: Polish → coverage gate → quickstart pass

---

## Notes

- [P] = different files, no cross-task dependencies within the phase
- TDD is constitution-mandated (Principle IV): every test must be written AND confirmed failing before implementation
- `advance_step` signature change (T003/T007) is additive (`company_id=None` default) — no breaking change to existing callers (invite join path)
- `company_id` in `OnboardingProgress` is server-set (from `progress.company_id`, never from request body) — satisfies Principle VI tenant isolation
- Idempotency relies on the existing `uq_company_membership (user_id, company_id)` unique constraint — `get_membership → conditional add_membership` avoids integrity errors
- Test markers: use `@pytest.mark.anyio` (not `@pytest.mark.asyncio`) per project convention
- Integration tests: use `fastapi.testclient.TestClient` (sync), not `httpx.ASGITransport`
