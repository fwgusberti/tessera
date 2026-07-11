---

description: "Task list for 056 — Admin-Added Members Skip the Onboarding Trap"
---

# Tasks: Admin-Added Members Skip the "Create a Company" Onboarding Trap

**Input**: Design documents from `/specs/056-fix-added-user-onboarding/`

**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, contracts/onboarding-gate.md, quickstart.md

**Tests**: REQUIRED. Constitution Principle IV (TDD, NON-NEGOTIABLE) mandates
test-first for the core domain rule and companion coverage for every change.
Per `project_test_env_baseline`, validate by covering the new/changed lines, not
the repo-wide 85% gate. Per `feedback_async_markers` /
`feedback_integration_testclient`: core tests use `pytest-asyncio`; API tests use
`anyio` + `fastapi.testclient.TestClient` — do not mix.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 / US2 / US3 (maps to spec.md user stories)

## Path Conventions

Monorepo: `packages/core/` (pure domain), `apps/api/` (FastAPI). No `apps/web/`
changes in this feature.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new project scaffolding required — existing packages, test
suites, and tooling are reused.

- [X] T001 Confirm baseline is green for the files in scope: run `pytest packages/core/tests/test_onboarding_repo.py apps/api/tests/integration/test_onboarding_gate.py apps/api/tests/integration/test_onboarding.py -q` and note any pre-existing failures per `project_test_env_baseline` so new regressions are distinguishable.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The pure domain predicate that BOTH gates (US1) and the broader
coverage (US2/US3) consume. Written test-first per Principle IV.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 [P] Write failing unit tests for the onboarding-satisfaction predicate in `packages/core/tests/test_onboarding_progress.py` (`@pytest.mark.asyncio` package convention; the function itself is sync so plain test fns are fine) covering the C1 truth table from `contracts/onboarding-gate.md`: (a) `completed_at` set + no membership → True; (b) `completed_at` None + has membership → True; (c) `completed_at` None + no membership → False; (d) `progress is None` + has membership → True; (e) `progress is None` + no membership → False. Confirm the tests FAIL (function not yet defined).
- [X] T003 Implement `has_completed_onboarding(progress: OnboardingProgress | None, has_company_membership: bool) -> bool` in `packages/core/tessera_core/domain/onboarding_progress.py` as a pure module-level function (no framework/persistence imports): return `True` if `has_company_membership` or (`progress is not None` and `progress.completed_at is not None`), else `False`. Run T002 tests until green. Ensure Ruff/Black clean.

**Checkpoint**: Predicate exists and is unit-proven — gate wiring can begin.

---

## Phase 3: User Story 1 - Admin-added member reaches the app instead of the onboarding trap (Priority: P1) 🎯 MVP

**Goal**: A user added to a company by an admin logs in and lands in the app with
document access — never redirected to onboarding, never asked to create a company.

**Independent Test**: Register user B, stop at the "create a company" step; as
admin A add B to company Acme; log in as B → `GET /v1/onboarding/status` returns
`completed=true`, a documents call returns 200 (no `onboarding_required`), and B
is never shown the create-company step.

### Tests for User Story 1 (write first, ensure they FAIL)

- [X] T004 [P] [US1] Extend `apps/api/tests/integration/test_onboarding_gate.py` with a test proving the server gate admits a full-token user who has a membership but `completed_at IS NULL`: the request does NOT return `403 onboarding_required` (contract C2). Ensure it FAILS against current `bearer.py`.
- [X] T005 [P] [US1] Extend `apps/api/tests/integration/test_onboarding.py` with a test that `GET /v1/onboarding/status` returns `completed=true` for a member whose `completed_at IS NULL` (contract C3). Ensure it FAILS against current `onboarding.py`.
- [X] T006 [P] [US1] Extend `apps/api/tests/integration/test_companies.py` with the end-to-end admin-add journey: admin adds an already-registered, not-yet-onboarded user → the added user (full token) gets `200` on a documents/company-scoped endpoint and `completed=true` from status (contract table rows 1–2). Ensure it FAILS.
- [X] T007 [P] [US1] Extend `apps/api/tests/unit/test_company_members_router.py` (or `test_company_add_user_router.py`) asserting that after `POST /companies/members` the target's `OnboardingProgress` is completed (`completed_at` set, `company_join_method="added"`, `company_id` = active company) AND an `onboarding.completed` audit record is written for the target (contract C4). Ensure it FAILS.

### Implementation for User Story 1

- [X] T008 [US1] Update the server onboarding gate in `apps/api/tessera_api/auth/bearer.py`: after loading `progress`, fetch the caller's memberships via `SqlCompanyRepository(session).list_memberships_for_user(UUID(user_info["sub"]))` and call `has_completed_onboarding(progress, has_company_membership=bool(memberships))`; raise `403 onboarding_required` only when it returns `False`. Keep the non-`full` token short-circuit above unchanged. Import the predicate at module level (per `feedback_router_imports`).
- [X] T009 [US1] Update `apps/api/tessera_api/routers/onboarding.py` so `get_status` derives `completed` from membership: load the caller's memberships and compute `completed = has_completed_onboarding(progress, bool(memberships))` in `_status_response`/`get_status` (pass the flag in). Leave `current_step`, `completed_steps`, `company_join_method` sourced from `progress`. Module-level import of the predicate and `SqlCompanyRepository`.
- [X] T010 [US1] Augment `add_company_member` in `apps/api/tessera_api/routers/companies.py`: after the membership is created (and its `company.member_added` audit), persist the target's onboarding completion — get-or-create the target's `OnboardingProgress` via `SqlOnboardingRepository`, set it complete (`complete()`), and record `company_join_method="added"` and `company_id=company_id` (idempotent if already complete); then `write_audit(action="onboarding.completed", actor_id=admin_id, entity_type="user", entity_id=body.user_id)`. Reuse the existing `ob_repo`/`_get_or_create_progress` pattern from `onboarding.py`/`approve_join_request`.
- [X] T011 [US1] Run T004–T007 to green; run Ruff + Black on `bearer.py`, `onboarding.py`, `companies.py`. Verify no regression in `apps/api/tests/integration/test_onboarding_gate.py` existing cases.

**Checkpoint**: MVP — admin-added users reach the app and their documents; the reported bug is fixed for the direct-add path.

---

## Phase 4: User Story 2 - A member is never asked to create a company (Priority: P2)

**Goal**: Any user with ≥1 membership is treated as onboarded regardless of how
they joined; a company-less user is still onboarded normally (FR-007).

**Independent Test**: For a self-created-company member and an approve-joined
member, status reports `completed=true` via the membership branch even with
`completed_at` manipulated to null; a brand-new no-company user still gets
`completed=false` / `403 onboarding_required`.

> The production code from US1 (predicate-based gates) already generalizes to all
> membership paths — US2 is coverage that locks in that generality and the
> negative case. No new production code is expected; add code only if a test
> reveals a path the US1 change missed.

### Tests for User Story 2 (write first)

- [X] T012 [P] [US2] Add to `apps/api/tests/integration/test_onboarding.py` a parametrized test that a member reached via the self-create and approve-join paths reports `completed=true` from status even when `completed_at` is forced null in the DB — proving membership, not `completed_at`, is authoritative (FR-005).
- [X] T013 [P] [US2] Add to `apps/api/tests/integration/test_onboarding_gate.py` the FR-007 negative case: a registered user with ZERO memberships and null `completed_at` still receives `403 onboarding_required` on a data endpoint, and `GET /v1/onboarding/status` returns `completed=false`.
- [X] T014 [US2] Confirm/adjust implementation so T012–T013 pass with the US1 predicate wiring; make no new production change unless a test fails (then patch the relevant gate). Ruff + Black clean.

**Checkpoint**: Membership is authoritative across all join paths; company-less users are unaffected.

---

## Phase 5: User Story 3 - Existing trapped members are recovered (Priority: P3)

**Goal**: Accounts that are already members but flagged not-onboarded (e.g., the
reporter's pre-existing added user) log in normally with no migration or manual
action.

**Independent Test**: Seed a membership with an `OnboardingProgress` that has
`completed_at IS NULL` (simulating a pre-fix admin-added account, created WITHOUT
going through the augmented `add_company_member`); the user passes the server gate
and status reports `completed=true` — with no migration executed.

### Tests for User Story 3 (write first)

- [X] T015 [P] [US3] Add to `apps/api/tests/integration/test_onboarding_gate.py` (or `test_onboarding.py`) a recovery test: directly insert a `CompanyMembership` + a null-`completed_at` `OnboardingProgress` (bypassing the augmented endpoint) → the user's full-token data call returns 200 and status `completed=true`, asserting recovery happens purely via the derive-from-membership path with no backfill.
- [X] T016 [US3] Confirm T015 passes on the US1 wiring; assert in the test/PR notes that no Alembic migration is added for this feature (recovery is read-derived). Ruff + Black clean.

**Checkpoint**: Pre-existing trapped members are recovered automatically; no data migration shipped.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validation and consistency.

- [X] T017 [P] Run the full validation in `specs/056-fix-added-user-onboarding/quickstart.md` (automated commands + the manual reporter-mirroring flow) and record results.
- [X] T018 [P] Confirm no `apps/web/` changes were needed: verify `OnboardingGuard` admits the user once `/v1/onboarding/status` reports `completed=true` (manual smoke or existing web tests) — documentation note only.
- [X] T019 Final Ruff + Black across changed files (`packages/core/tessera_core/domain/onboarding_progress.py`, `apps/api/tessera_api/auth/bearer.py`, `apps/api/tessera_api/routers/onboarding.py`, `apps/api/tessera_api/routers/companies.py`) and run the feature's test files together to confirm green.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none — start immediately.
- **Foundational (Phase 2)**: after Setup — **BLOCKS all user stories** (the predicate is consumed by every gate).
- **User Stories (Phase 3–5)**: all depend on Phase 2.
  - US1 (P1) delivers the production code (both gates + persistence).
  - US2 (P2) and US3 (P3) are primarily coverage over the same US1 code; they can be written in parallel with/after US1 but their tests only pass once US1 wiring (T008–T010) lands.
- **Polish (Phase 6)**: after all desired stories.

### User Story Dependencies

- **US1 (P1)**: after Foundational. Self-contained; the MVP.
- **US2 (P2)**: after Foundational; verified green only once US1's T008–T010 are implemented (shared code).
- **US3 (P3)**: after Foundational; verified green only once US1's T008–T009 are implemented (shared gates).

### Within Each User Story

- Tests written first and observed FAILING before implementation (Principle IV).
- Predicate (Phase 2) before gates (US1). Gate wiring before broader coverage (US2/US3).

### Parallel Opportunities

- T002 (core test) is independent of all API work.
- Within US1, the four test tasks T004, T005, T006, T007 are `[P]` (different files) and can be written together; the implementation tasks T008, T009, T010 touch three different files and can proceed in parallel once the predicate (T003) exists.
- US2 and US3 test tasks (T012, T013, T015) are `[P]` across different concerns.

---

## Parallel Example: User Story 1

```bash
# Write all US1 tests first (different files, in parallel):
Task: "Server-gate membership test in apps/api/tests/integration/test_onboarding_gate.py"   # T004
Task: "Status completed-via-membership test in apps/api/tests/integration/test_onboarding.py" # T005
Task: "Admin-add E2E journey test in apps/api/tests/integration/test_companies.py"          # T006
Task: "add_company_member persistence+audit test in apps/api/tests/unit/test_company_members_router.py" # T007

# Then implement across the three files in parallel (after T003):
Task: "Wire membership into gate in apps/api/tessera_api/auth/bearer.py"        # T008
Task: "Derive completed from membership in apps/api/tessera_api/routers/onboarding.py" # T009
Task: "Persist onboarding on add in apps/api/tessera_api/routers/companies.py"  # T010
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup (baseline note).
2. Phase 2 Foundational (predicate, test-first) — CRITICAL, blocks everything.
3. Phase 3 US1 — both gates + persistence.
4. **STOP and VALIDATE**: run the quickstart manual flow; the reporter's bug is fixed.

### Incremental Delivery

1. Foundational → predicate ready.
2. US1 → admin-added users work (MVP, ship).
3. US2 → lock in generality across all join paths + FR-007 negative case.
4. US3 → prove automatic recovery of pre-existing trapped accounts (no migration).

---

## Notes

- No Alembic migration and no `apps/web/` changes in this feature (by design — see plan.md and research.md Decision 1).
- `[P]` = different files, no incomplete-task dependency.
- Module-level imports in touched routers/gate (per `feedback_router_imports`) for patchability.
- Commit after each task or logical group; keep Ruff/Black clean per commit (Principle V).
