# Tasks: Company-Scoped Admin Privileges

**Input**: Design documents from `/specs/036-company-scoped-admin/`

**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/authorization-matrix.md ✓, quickstart.md ✓

**Tests**: INCLUDED. The Constitution (Principle IV, TDD) and the plan require a failing per-company test before each authority change; quickstart.md defines the validation suites. Test tasks are therefore generated and ordered **before** the implementation they cover.

**Organization**: Tasks are grouped by user story (P1 → P2) so each story is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Exact file paths are included in each description

## Project conventions (apply to every task)

- Domain layer `packages/core` MUST NOT import transport/persistence — admin status enters only as a primitive `bool`.
- Routers MUST use **module-level imports** (not deferred) so collaborators stay test-patchable.
- Core tests use **pytest-asyncio** (`@pytest.mark.asyncio`); API tests use **anyio** (`@pytest.mark.anyio`) — do not mix.
- Integration tests use `fastapi.testclient.TestClient` (sync), not `httpx.ASGITransport`.
- Cross-company by-ID denial == genuine not-found: **HTTP 404 + generic body**, exactly **one** `cross_tenant_denied` audit record (supersedes 035's 403 for by-ID paths). In-company non-admin attempting an admin action still gets **403**.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the exact change surface before editing.

- [X] T001 Catalog every `is_admin` / `user.is_admin` consumption site (expected: 5 sites in `packages/core/tessera_core/permissions/access.py`, the override in `packages/core/tessera_core/services/membership.py`, and routers `proposals.py`, `documents.py`, `members.py`, `spaces.py`, `connectors.py`, `agent_credentials.py`, `metrics.py`); confirm `apps/api/tessera_api/routers/admin.py` is the only file that legitimately keeps reading the global flag. Record findings as the baseline for Phase 2/3.

  **Findings (baseline):**
  - `access.py`: 5 authorization reads of `user.is_admin` — `can_read_document`, `can_publish_document`, `can_admin_space`, `effective_space_role`, `can_read_space_document`. All replaced by `is_company_admin`.
  - `services/membership.py`: no direct `actor.is_admin` read; authority flowed through `can_manage_members` → `effective_space_role`. Now threads `is_company_admin`.
  - Routers reading the global flag for **authorization**: only `documents.py` reindex (`is_admin = user_info.get("is_admin")`). Replaced by per-company admin. The other routers (`proposals/members/spaces/connectors/agent_credentials/metrics`) already authorized via space role or `require_company_admin` (035) — re-sourced/confirmed.
  - Legitimate remaining readers of the global flag (NOT authorization over company data): `admin.py` (platform-operator exception), plus JWT-minting / session-payload sites in `auth.py`, `companies.py`, `oidc.py` and persistence plumbing in `repo.py`/`models.py`/`entities.py`. Confirmed `admin.py` is the only authorization consumer (T025 re-verified post-implementation).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Move admin authority from the global flag to a per-company `is_company_admin: bool` threaded from the API boundary into the pure domain, expose the caller's membership to read-path routers, backfill owner admin memberships, and provide the shared admin-role test fixture.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete — every router in Phase 3+ depends on the new domain signatures and the new auth dependency.

### Tests for Foundational (write first; must FAIL before implementation) ⚠️

- [X] T002 [P] Unit tests in `packages/core/tests/test_permissions.py` (`@pytest.mark.asyncio`): assert `AccessContext(is_company_admin=True)` authorizes and `is_company_admin=False` denies for `can_read_document`, `can_publish_document`/`can_approve_proposal`, `can_admin_space`; assert the space predicates `effective_space_role`, `can_write_document`, `can_manage_members`, `can_read_space_document` treat `is_company_admin=True` as implicit space admin and default fail-closed when omitted. Confirm `ctx.user.is_admin` no longer affects any outcome.
- [X] T003 [P] Unit tests in `packages/core/tests/test_membership.py` (`@pytest.mark.asyncio`): assert `MembershipService.invite/change_role/remove` authorize on `is_company_admin=True`, deny on `False`, and no longer consult `actor.is_admin`.
- [X] T004 [P] Migration backfill + idempotency test in `apps/api/tests/test_migration_0010_backfill.py` (`@pytest.mark.anyio`): a company whose `admin_user_id` lacks a membership row gets exactly one `role='admin'` row after upgrade; an existing `role='member'` row is NOT elevated; re-running upgrade is a no-op; admin-membership count never decreases (SC-007).

### Implementation for Foundational

- [X] T005 [P] In `packages/core/tessera_core/permissions/access.py`: add `is_company_admin: bool = False` to `AccessContext` (fail-closed default) and replace `ctx.user.is_admin` reads with `ctx.is_company_admin` in `can_read_document`, `can_publish_document` (→ `can_approve_proposal`), and `can_admin_space`.
- [X] T006 In `packages/core/tessera_core/permissions/access.py`: add trailing `is_company_admin: bool = False` parameter to `effective_space_role`, `can_write_document`, `can_manage_members`, `can_read_space_document`, replacing their `user.is_admin` reads so a company admin is implicit `SpaceRole.ADMIN` for spaces in their own company. (Same file as T005 — sequential.)
- [X] T007 [P] In `packages/core/tessera_core/services/membership.py`: add `is_company_admin: bool = False` to `invite`, `change_role`, `remove`; pass it into `can_manage_members`; remove reliance on `actor.is_admin`.
- [X] T008 [P] In `apps/api/tessera_api/auth/oidc.py`: add `require_company_member(request) -> (user_info, company_id, membership)` as a thin wrapper over the existing `_resolve_company_membership` (no extra DB hit), plus an `is_company_admin(membership)` helper returning `membership.role == CompanyRole.ADMIN`.
- [X] T009 [P] Create `db/migrations/versions/0010_backfill_company_admin_memberships.py` (data-only, no DDL): `upgrade()` does a single idempotent `INSERT ... SELECT ... WHERE NOT EXISTS` adding a `role='admin'` `company_memberships` row for every `companies.admin_user_id` lacking one; never touches `users.is_admin`, never elevates an existing member; `downgrade()` is a documented no-op. `down_revision = '0009'`.
- [X] T010 [P] In `apps/api/tests/conftest.py`: add an **admin-role variant** of `two_company_setup` whose mocked `get_membership` returns `CompanyRole.ADMIN` for the caller in Company A (and MEMBER in B), reusable by US1/US2/US4.

**Checkpoint**: Domain accepts `is_company_admin`, the API boundary can derive it, owner admin memberships are backfilled, and the admin-role fixture exists. Foundational tests (T002–T004) now pass.

---

## Phase 3: User Story 1 - Admin authority confined to the active company (Priority: P1) 🎯 MVP

**Goal**: Every admin-gated **write/manage** action (members, connectors, agent credentials, proposals, space permissions, document reindex/create, metrics) succeeds inside the admin's active company and is refused for another company's resources — cross-company by-ID returning 404 + one audit record, listings excluding other tenants.

**Independent Test**: Sign in as admin of Company A; run each admin write/manage action against a Company A resource (2xx) and the equivalent Company B resource by ID (404 + exactly one `cross_tenant_denied`); confirm listings return only Company A rows.

### Tests for User Story 1 (write first; must FAIL before wiring) ⚠️

- [X] T011 [US1] Integration tests in `apps/api/tests/test_company_scoped_admin.py` (`@pytest.mark.anyio`, `TestClient`) using the admin-role fixture: for member invite/change-role/remove, connector create/sync, agent-credential issue/revoke, proposal approve/reject, space permission create, document reindex/create, and metrics read — assert success with Company A active; assert **404 + generic body + exactly one `cross_tenant_denied`** for the same action targeting a Company B resource by ID; assert listings (members, metrics) contain only Company A data with **no** denial audit.

### Implementation for User Story 1

- [X] T012 [P] [US1] `apps/api/tessera_api/routers/members.py`: switch to derive `is_company_admin` (via `require_company_member`/`is_company_admin`) and pass it into `MembershipService.invite/change_role/remove`; return **404 + one `cross_tenant_denied`** for cross-company space/member by-ID (supersedes 035's 403).
- [X] T013 [P] [US1] `apps/api/tessera_api/routers/proposals.py`: build `AccessContext(is_company_admin=...)` from the resolved membership for approve/reject; return 404 + one audit for a proposal owned by another company.
- [X] T014 [P] [US1] `apps/api/tessera_api/routers/connectors.py`: confirm create/sync authorize on company admin only (no `is_admin` path remains); convert cross-company by-ID denial to 404 + one audit.
- [X] T015 [P] [US1] `apps/api/tessera_api/routers/agent_credentials.py`: confirm issue/revoke authorize on company admin only; convert cross-company by-ID (revoke) denial to 404 + one audit.
- [X] T016 [P] [US1] `apps/api/tessera_api/routers/spaces.py`: permission creation (`POST /v1/spaces/{id}/permissions`) authorizes on company admin only; 404 + one audit for a space owned by another company.
- [X] T017 [P] [US1] `apps/api/tessera_api/routers/documents.py`: reindex and create pass `is_company_admin` into `can_write_document` (per-company admin replaces global override); 404 + one audit for a document/space owned by another company.
- [X] T018 [P] [US1] `apps/api/tessera_api/routers/metrics.py`: confirm it consumes no global `is_admin` (already `require_company_admin` per 035); aggregates returned per active company only.

**Checkpoint**: US1 is fully functional — admin write/manage authority is confined to the active company; MVP deliverable complete.

---

## Phase 4: User Story 2 - No cross-company visibility from admin status (Priority: P1)

**Goal**: Admin status grants no cross-company **read** access; a by-ID read of another company's resource is byte-identical to a genuine not-found, and no listing ever returns another tenant's rows.

**Independent Test**: As admin of Company A, `GET /v1/documents/{company_b_doc_id}` returns the exact same 404 status/body as `GET /v1/documents/{random_uuid}`, with one `cross_tenant_denied` record; every company-scoped listing excludes Company B with no denial audit.

### Tests for User Story 2 (write first) ⚠️

- [X] T019 [US2] Integration tests in `apps/api/tests/test_company_scoped_admin.py` (`@pytest.mark.anyio`, `TestClient`): assert `GET /v1/documents/{cross_company_id}` is byte-identical (status + body) to a random non-existent UUID and emits exactly one `cross_tenant_denied`; assert no Company B field appears in any response; assert document/member/space/metrics listings exclude Company B rows and emit **no** denial audit (SC-003, SC-004).

### Implementation for User Story 2

- [X] T020 [US2] `apps/api/tessera_api/routers/documents.py`: read path (`GET /v1/documents/{id}`) passes `is_company_admin` into `can_read_document` and returns 404 + one `cross_tenant_denied` for a document owned by another company (indistinguishable from absent). Depends on T017 (same file).

**Checkpoint**: US1 + US2 both independently testable — no cross-company read leakage, existence never disclosed.

---

## Phase 5: User Story 3 - Per-company authority for multi-company members (Priority: P2)

**Goal**: A user who is admin in Company A and ordinary member in Company B exercises admin authority only while A is active, and is treated as a non-admin (403, not 404) while B is active.

**Independent Test**: With `admin_in_a_member_in_b`, an admin-only action succeeds with A active and is denied **403** with B active.

### Implementation / Tests for User Story 3

- [X] T021 [US3] In `apps/api/tests/conftest.py`: add an `admin_in_a_member_in_b` fixture returning `(token_a, company_a_id, token_b, company_b_id)` where the caller is `CompanyRole.ADMIN` in A and `CompanyRole.MEMBER` in B. (Same file as T010 — sequential.)
- [X] T022 [US3] Integration tests in `apps/api/tests/test_company_scoped_admin.py` (`@pytest.mark.anyio`, `TestClient`): with Company A active, an admin-only action on a Company A resource succeeds; with Company B active, the same action is denied **403** (in-company non-admin, NOT a cross-tenant 404), validating authority follows the active company (SC-006). No new production code expected beyond Phase 2/3.

**Checkpoint**: Per-company authority verified across a company switch.

---

## Phase 6: User Story 4 - Tenant data protected from outside admins (Priority: P2)

**Goal**: No admin from another company — including a user still carrying the legacy `users.is_admin = True` flag but with no membership in the target company — can read or mutate that company's data.

**Independent Test**: Create data in Company B; a Company A admin who also carries `users.is_admin = True` (no B membership) attempts to read/edit/delete it → 404, data unchanged.

### Implementation / Tests for User Story 4

- [X] T023 [US4] In `apps/api/tests/conftest.py`: add a fixture variant whose Company A admin caller also has `users.is_admin = True` while holding **no** Company B membership. (Same file as T010/T021 — sequential.)
- [X] T024 [US4] Integration tests in `apps/api/tests/test_company_scoped_admin.py` (`@pytest.mark.anyio`, `TestClient`): the legacy-global-flag admin from A attempting read/edit/delete on a Company B document → **404**, document unchanged (FR-002, FR-007); confirm the global flag confers zero authority over Company B.
- [X] T025 [US4] Verification: assert no residual `user.is_admin` / `ctx.user.is_admin` authorization read remains in any company-scoped path under `packages/core/tessera_core/permissions/`, `packages/core/tessera_core/services/membership.py`, or `apps/api/tessera_api/routers/` (the only legitimate remaining reader is `apps/api/tessera_api/routers/admin.py`).

**Checkpoint**: All four user stories independently functional; legacy global-admin backdoor closed.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Reconcile superseded behavior, confirm the platform-operator exception, and run the quality + regression gates.

- [X] T026 [P] Update existing feature-035 cross-tenant tests asserting **403** for by-ID denials to assert **404** in `apps/api/tests/test_tenant_isolation.py` (and any other 035 cross-tenant by-ID assertions); keep `cross_tenant_denied` audit assertions unchanged (research.md migration note).
- [X] T027 Confirm `apps/api/tessera_api/routers/admin.py` is unchanged and its tests still pass — the documented platform-operator exception (`PUT /v1/users/{id}/platform-role`, `GET /v1/admin/spaces`, `PUT /v1/admin/spaces/{id}/retention`, `POST /v1/admin/reindex`) remains gated by the global flag and unreachable via company admin status (FR-010).
- [X] T028 [P] Run quickstart.md validation: apply migrations through 0010, run the SC-007 migration SQL checks (every owner has an admin membership; admin count never drops), and execute Scenarios 1–4.
- [X] T029 Run quality gates: `ruff` + `black` across `packages/core` and `apps/api` (Constitution Principle V) and resolve findings.
- [X] T030 [P] Run full regression: `pytest apps/api/tests packages/core/tests` — confirm new per-company/cross-company cases pass, in-company admin happy paths still pass (SC-005), and previously-403 by-ID assertions now assert 404.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup; **BLOCKS all user stories** (domain signatures + `require_company_member` + migration + fixture).
- **User Stories (Phase 3–6)**: all depend on Foundational completion. US1 and US2 are P1 (ship first); US3 and US4 are P2.
- **Polish (Phase 7)**: depends on the user stories being implemented (notably T026 reconciles the 403→404 change introduced across US1/US2).

### User Story Dependencies

- **US1 (P1)**: depends only on Foundational. No dependency on other stories.
- **US2 (P1)**: depends on Foundational; T020 edits `documents.py` after US1's T017 (same file).
- **US3 (P2)**: depends on Foundational; verification-only (no new production code). Fixture T021 shares `conftest.py` with T010.
- **US4 (P2)**: depends on Foundational; verification-only. Fixture T023 shares `conftest.py` with T010/T021.

### Within Each Story / Phase

- Tests are authored before the implementation they cover (TDD).
- Domain (`access.py`, `membership.py`) before the API boundary (`oidc.py`); boundary before routers.
- `access.py` tasks T005 → T006 are sequential (same file).
- The single test file `apps/api/tests/test_company_scoped_admin.py` is appended across US1–US4 (T011, T019, T022, T024) — keep those test-writing tasks sequential.
- `apps/api/tests/conftest.py` fixture tasks T010 → T021 → T023 are sequential (same file).

### Parallel Opportunities

- Foundational tests T002, T003, T004 can run in parallel (different files).
- Foundational implementation T005(+T006), T007, T008, T009, T010 are largely parallel (distinct files; T006 follows T005).
- US1 router tasks T012–T018 are all parallel (distinct router files) once Foundational is done.
- Polish T026, T028, T030 can run in parallel.

---

## Parallel Example: User Story 1

```bash
# After Foundational completes, write the US1 tests first, then wire routers in parallel:
Task: "members.py — pass is_company_admin; 404+audit cross-company"          # T012
Task: "proposals.py — AccessContext.is_company_admin; 404+audit"             # T013
Task: "connectors.py — CA-only; 404+audit"                                   # T014
Task: "agent_credentials.py — CA-only; 404+audit"                           # T015
Task: "spaces.py — permission create CA-only; 404+audit"                     # T016
Task: "documents.py — reindex/create per-company admin; 404+audit"          # T017
Task: "metrics.py — confirm no global is_admin"                             # T018
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1: Setup (T001).
2. Phase 2: Foundational (T002–T010) — **blocks everything**.
3. Phase 3: User Story 1 (T011–T018).
4. **STOP and VALIDATE**: run quickstart Scenario 1 — admin write/manage confined to active company.
5. Deploy/demo the core security fix.

### Incremental Delivery

1. Foundational → admin authority re-sourced to per-company membership.
2. US1 → write/manage confinement (MVP, P1).
3. US2 → read no-existence-disclosure (P1).
4. US3 → per-company authority on company switch (P2).
5. US4 → legacy global-flag backdoor closed (P2).
6. Polish → reconcile 035 tests, confirm operator exception, run gates.

---

## Notes

- [P] = different files, no incomplete dependencies.
- This feature adds **no DDL**; the only persistence change is the data-only migration 0010.
- The `cross_tenant_denied` audit writer in `apps/api/tessera_api/adapters/audit.py` is reused unchanged.
- Commit after each task or logical group; verify each phase's tests before moving to the next priority.
