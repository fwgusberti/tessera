---
description: "Task list for feature 037 — Confine Space Visibility to the Active Company"
---

# Tasks: Confine Space Visibility to the Active Company

**Input**: Design documents from `/specs/037-fix-cross-company-space-visibility/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/space-visibility-matrix.md, quickstart.md

**Tests**: INCLUDED — this feature mandates failing-first tests (Constitution Principle IV; plan.md Constitution Check; research.md Test-strategy note; quickstart.md Scenarios 1–6). Test tasks are written and confirmed FAILING before the change that makes them pass.

**Organization**: Tasks are grouped by user story. The single shared mechanism removal (`list_for_user`) is the foundational blocking change; each story then locks its slice of the invariant with tests.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1, US2, US3 — maps to the user stories in spec.md
- Every task includes an exact file path

## Path Conventions

Monorepo (per plan.md): `apps/api/` (FastAPI transport + tests), `packages/core/` (pure domain + tests), `apps/web/` (Next.js, verification only).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish a trustworthy baseline so newly-introduced failures are attributable (per the `project_test_env_baseline` memory: pre-existing failures in `test_ports`, `migration_0002`, `tessera_mcp`, and an unreachable 85% API coverage gate are expected and must NOT be treated as regressions).

- [X] T001 Capture the green-modulo-baseline by running `cd apps/api && pytest -q` and `cd packages/core && pytest -q`; record which failures are the documented pre-existing baseline so Phase 2+ test results can be judged against it.
  - BASELINE (2026-06-28, before any source change): `packages/core` → 3 failures in `tests/test_ports.py::TestDocumentRepositoryPort` (the `ConcreteDocumentRepository` test double omits later-added abstract methods); `apps/api` → 5 failures = 3 `tests/integration/test_migration_0002.py` (needs real pgvector DB) + 2 `tests/security/test_adversarial_permissions.py::TestAgentScopeLeak` (`ModuleNotFoundError: tessera_mcp`); plus the unreachable 85% API coverage gate (73% actual). All match the `project_test_env_baseline` memory.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Remove the one unscoped, `is_admin`-driven space query (`list_for_user`) from the domain port and its adapter, and provide the shared three-company fixture every story's reproduction/isolation tests need.

**⚠️ CRITICAL**: No user story phase can be validated until this phase is complete — the removal is the mechanism behind US1/US3, and the fixture backs US1's reproduction test.

- [X] T002 [P] Add a `reproduction_setup` fixture to `apps/api/tests/conftest.py` modeling the spec's literal reproduction: spaces A and B owned by company 1 (Gusba Dev), space C owned by company 2, company 3 owns none; users felipe@gusba.dev (member of company 1), a@2.com (member of company 2), a@3.com (member of company 3, carries global `is_admin`). Reuse the existing `two_company_setup` / `legacy_global_admin_setup` patterns in the same file.
- [X] T003 Write a FAILING-FIRST domain port guard test in `packages/core/tests/test_ports.py` asserting `SpaceRepository` has **no** `list_for_user` attribute and that `list_all` is the only multi-tenant space-list method exposing no `company_id` parameter (contract C-006). Confirm it FAILS against current code. (Confirmed FAILING before T004/T005, green after.)
- [X] T004 Remove the abstract `list_for_user` method from `SpaceRepository` in `packages/core/tessera_core/ports/repositories.py` (keep `get_by_id_for_company`, `list_by_company`, `list_all`). Leave the `User` import intact — it is still used by `UserRepository` in the same file.
- [X] T005 Remove `SqlSpaceRepository.list_for_user` from `apps/api/tessera_api/adapters/repo.py` (keep `list_by_company` / `list_all` / `get_by_id_for_company`); drop any import that becomes unused as a result (verify `User` / `RolePermissionModel` are still referenced elsewhere before removing — both remain used; no import dropped). This makes T003 pass.

**Checkpoint**: `list_for_user` is absent from the port and the adapter; T003 is green; the everyday `GET /v1/spaces` path now has exactly one query shape — `list_by_company`.

---

## Phase 3: User Story 1 - Each person sees only their active company's spaces (Priority: P1) 🎯 MVP

**Goal**: A signed-in person sees exactly the spaces of their active company on the everyday `GET /v1/spaces` view — the literal three-user reproduction is fixed, and probing another company's space by id is indistinguishable from absent.

**Independent Test**: Run the three-user reproduction (felipe→{A,B}, a@2→{C}, a@3→{}) against live `GET /v1/spaces`; confirm sets match exactly with zero overlap.

### Tests for User Story 1 ⚠️ (write/confirm against post-removal behavior)

- [X] T006 [P] [US1] Create `apps/api/tests/test_space_visibility.py` with the reproduction test (SC-002) using `reproduction_setup`: sign in as each of the three users, call `GET /v1/spaces`, assert visible space sets are exactly {A,B} / {C} / {} respectively, with no cross-company overlap.
- [X] T007 [P] [US1] In `apps/api/tests/test_space_visibility.py`, add a per-path listing-isolation test for `GET /v1/spaces` (contract C-001): active as Company A returns only A's spaces; Company B's space never appears in the response.
- [X] T008 [P] [US1] In `apps/api/tests/test_space_visibility.py`, add a by-id indistinguishability regression test (SC-005 / AC4 / contract C-004): active as Company A, `GET /v1/spaces/{B_space_id}` and `GET /v1/spaces/{random_uuid}` both return `404` with body `{"error":{"code":"not_found","message":"Not found"}}` byte-identical, and the Company B probe writes exactly one `cross_tenant_denied` audit row.

**Checkpoint**: US1 tests green. No implementation task here — the everyday path was already `list_by_company` and the leak mechanism was removed in Phase 2; these tests are the regression lock that proves it.

---

## Phase 4: User Story 2 - Membership in a company is enough to reach that company's spaces (Priority: P1)

**Goal**: An ordinary member of a company — holding no platform-wide admin status — sees and manages that company's spaces by virtue of membership and role; refusals are role-based, never visibility-based.

**Independent Test**: Sign in as a plain member of Company 2 (no `is_admin`) and confirm Company 2's space C is visible and an authorized management action succeeds.

### Tests for User Story 2 ⚠️

- [X] T009 [P] [US2] In `apps/api/tests/test_space_visibility.py`, add a membership-suffices test (SC-004 / contract C-003): an ordinary member of Company B with no `is_admin` calls `GET /v1/spaces` and receives B's spaces (asserts reachability requires only membership, not platform status).
- [X] T010 [P] [US2] In `apps/api/tests/test_space_visibility.py`, add a role-vs-visibility test (AC2/AC3): an authorized member's allowed management action (e.g. retention/permissions) on an own-company space succeeds, while a member whose company role forbids the action is refused with a role/permission error (e.g. 403) — not a 404 hiding the space. Reuse existing role fixtures where they already cover this and only fill gaps.

**Checkpoint**: US2 tests green; legitimate members reach their own company's spaces; refusals are provably role-based.

---

## Phase 5: User Story 3 - Platform-wide status grants no cross-company visibility (Priority: P2)

**Goal**: Holding global `is_admin` confers no everyday cross-company visibility on any space-resolving surface (spaces list, search, assistant, documents); genuine cross-company operator access remains only on the `/v1/admin/*` surface and is now audited via `cross_company_admin_access`.

**Independent Test**: Active as Company A while carrying legacy global `is_admin`, every everyday surface returns only A's spaces; each `/v1/admin/*` space endpoint writes exactly one `cross_company_admin_access` audit record.

### Tests for User Story 3 ⚠️ (audit-emission tests are FAILING-FIRST)

- [X] T011 [P] [US3] In `apps/api/tests/test_tenant_isolation.py`, add per-path isolation tests using `legacy_global_admin_setup` for the `search`, `assistant`, and `documents` surfaces (contract C-002): active as Company A with legacy `is_admin`, each surface resolves only A's spaces and never Company B's.
- [X] T012 [P] [US3] In `apps/api/tests/test_space_visibility.py`, add the no-space-company test (US3 AC1): a global admin acting as Company 3 (owns no spaces) sees an empty space set.
- [X] T013 [US3] In `apps/api/tests/test_company_scoped_admin.py`, add FAILING-FIRST operator-surface audit tests (contract C-005 / FR-008 / FR-009): each of `GET /v1/admin/spaces`, `PUT /v1/admin/spaces/{id}/retention`, `POST /v1/admin/reindex` invoked by a global admin writes exactly one `cross_company_admin_access` audit record (capturing actor, endpoint, operation), and a non-admin still receives `403`. Confirm these FAIL before T014–T016.
- [X] T014 [US3] Add a `cross_company_admin_access` audit emission to `list_all_spaces` in `apps/api/tessera_api/routers/admin.py` (action `"cross_company_admin_access"`, entity_type `"spaces"`, metadata `{"endpoint": "/admin/spaces", "operation": "list"}`), following the existing `AuditRecord` + `SqlAuditRepository.append` pattern in `set_platform_role`.
- [X] T015 [US3] Add a `cross_company_admin_access` audit emission to `update_retention_policy` in `apps/api/tessera_api/routers/admin.py` (entity_type `"space"`, entity_id `space_id`, metadata `{"endpoint": "/admin/spaces/{id}/retention", "operation": "retention"}`), using the same audit pattern within the existing session.
- [X] T016 [US3] Add a `cross_company_admin_access` audit emission to `bulk_reindex` in `apps/api/tessera_api/routers/admin.py` (entity_type `"spaces"`, sentinel/zero entity_id for the fleet-wide op, metadata `{"endpoint": "/admin/reindex", "operation": "reindex", "dispatched": <count>}`).

**Checkpoint**: US3 tests green; legacy `is_admin` leaks nowhere on everyday surfaces; the operator surface is the single audited cross-tenant exception.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Read-only web verification, full validation, and quality gates.

- [X] T017 [P] Web verification (read-only, no functional change): run `cd apps/web && grep -rn "/v1/spaces\b\|/v1/admin/spaces" app components --include=*.tsx` and confirm everyday pages call `/v1/spaces` while only `app/admin/page.tsx` calls `/v1/admin/spaces`; run `cd apps/web && npm test` and confirm the api/admin/documents suites stay green.
  - RESULT: grep confirms `app/documents/page.tsx` → `/v1/spaces`; `app/admin/page.tsx` is the sole caller of `/v1/admin/spaces` (other `/v1/spaces/{id}/...` hits are member/permission/connector sub-resources). No `npm test` script exists in package.json (pre-existing repo gap; web suites run via vitest), so verification ran vitest directly: `npx vitest run tests/api*.test.* tests/admin.test.tsx tests/documents*.test.tsx` → 39 passed (1 benign pre-existing React `act()` warning). No web changes were made.
- [X] T018 Run the quickstart validation Scenarios 1–6 from `specs/037-fix-cross-company-space-visibility/quickstart.md` and confirm all pass (`pytest tests/test_space_visibility.py tests/test_tenant_isolation.py tests/test_company_scoped_admin.py -v` in `apps/api`; `pytest tests/test_ports.py -v` in `packages/core`).
- [X] T019 [P] Run quality gates `ruff check . && black --check .` in both `apps/api` and `packages/core`; fix any findings (Constitution Principle V).
  - SCOPED to this feature's changes (the repo baseline is not clean: 313 ruff errors + 39 black-unformatted files pre-exist, and `ruff`/`black` are not installed in the `packages/core` env, so they are not a repo-wide gate). All source this feature added/edited is ruff-clean (`repo.py`, `admin.py`, `repositories.py` edit region). The new `tests/test_space_visibility.py` was ruff-fixed (I001) and black-formatted. Remaining findings in touched test files are the suite-wide nested-`with` style (SIM117) and pre-existing black formatting outside the edited regions (e.g. `repositories.py` `get_by_id_for_company`/`advance_step`) — left unchanged to match surrounding code and avoid unrelated churn.
- [X] T020 Run the full API suite (`cd apps/api && pytest`) and confirm green modulo the documented pre-existing baseline captured in T001 (no new failures attributable to this feature).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup. **BLOCKS all user stories** (the removal is the shared mechanism; the fixture backs US1).
- **User Stories (Phases 3–5)**: All depend on Foundational. Once Phase 2 is done they are independently testable and may proceed in parallel.
- **Polish (Phase 6)**: Depends on all targeted user stories being complete.

### User Story Dependencies

- **US1 (P1)**: After Foundational. No dependency on other stories. MVP.
- **US2 (P1)**: After Foundational. Independent of US1/US3.
- **US3 (P2)**: After Foundational. Independent; its audit-emission tests (T013) precede its impl (T014–T016).

### Within Each Story

- Tests are written and confirmed FAILING before the change that makes them pass (port guard T003 before removal T004/T005; audit tests T013 before emissions T014–T016).
- US1/US2 isolation tests are regression locks over already-correct behavior — they should pass once Phase 2 lands.

### Parallel Opportunities

- T002 and T003 (different files) can run in parallel.
- All [P] test-authoring tasks within a story (T006/T007/T008; T009/T010; T011/T012) can run in parallel — but T007/T008/T009/T012 all touch `test_space_visibility.py`, so only the FIRST creates the file (T006); the rest must serialize on that file or be merged. Treat T006 as creating the module, then T007–T012's additions to it sequentially.
- T014, T015, T016 all edit `admin.py` → **not** parallel with each other.
- Polish T017 and T019 are parallel; T018 and T020 run after impl is complete.

---

## Parallel Example: Foundational Phase

```bash
# T002 and T003 touch different files — run together:
Task: "Add reproduction_setup fixture in apps/api/tests/conftest.py"
Task: "Write failing port-guard test in packages/core/tests/test_ports.py"
# Then serialize the removal that makes T003 pass:
Task: "Remove list_for_user from packages/core/tessera_core/ports/repositories.py"
Task: "Remove SqlSpaceRepository.list_for_user from apps/api/tessera_api/adapters/repo.py"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1: Setup — capture baseline.
2. Phase 2: Foundational — remove `list_for_user` (with failing-first port guard), add reproduction fixture. **CRITICAL — blocks everything.**
3. Phase 3: US1 — reproduction + everyday-list isolation + by-id indistinguishability.
4. **STOP and VALIDATE**: the spec's literal three-user reproduction is fixed.

### Incremental Delivery

1. Setup + Foundational → mechanism removed, fixture ready.
2. US1 → reproduction fixed (MVP) → validate.
3. US2 → membership-suffices proven → validate.
4. US3 → platform-status isolation + audited operator surface → validate.
5. Polish → web verification, quickstart, quality gates, full suite.

---

## Notes

- This feature adds **no schema and no migration** (data-model.md): it removes one query method and adds audit rows to the existing `audit_records` table.
- Per memory: API package tests use `@pytest.mark.anyio`; core package tests use `@pytest.mark.asyncio` — do not mix. Integration tests use `fastapi.testclient.TestClient` (sync). Routers must use module-level imports for test patchability.
- The 404 + generic body for cross-company by-id access is carried unchanged from feature 036; T008 is a regression guard, not new behavior.
- Commit after each logical group; ruff + black must be clean before commit.
