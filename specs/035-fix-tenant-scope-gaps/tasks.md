---
description: "Task list for feature 035 — Close Company & User Scope Gaps"
---

# Tasks: Close Company & User Scope Gaps

**Input**: Design documents from `/specs/035-fix-tenant-scope-gaps/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/scope-gaps.md, quickstart.md

**Tests**: Test tasks ARE included — TDD is mandated by Constitution Principle IV
("each gap gets a failing cross-tenant test first") and SC-001/SC-002/SC-006
require an automated cross-company test for every hardened flow.

**Organization**: Tasks are grouped by user story (US1–US6) so each can be
implemented and verified independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task belongs to (US1–US6)
- File paths are relative to repo root `/home/felipe/Projetos/tessera/`

## Path Conventions

- Transport / API: `apps/api/tessera_api/`
- Domain: `packages/core/tessera_core/`
- Migrations: `db/migrations/versions/`
- Tests: `apps/api/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the working environment and the 031 pattern this feature reuses.

- [X] T001 Verify branch `035-fix-tenant-scope-gaps` is checked out and the test suite is green at baseline: run `cd apps/api && pytest --cov=tessera_api --cov=tessera_core` and record the starting coverage (must end ≥ 85%).
- [X] T002 Re-read the 031 reference implementation to mirror it exactly: `require_company_context` in `apps/api/tessera_api/auth/oidc.py`, the existing `*_for_company` methods + `validate_space_for_company` in `apps/api/tessera_api/adapters/repo.py` and `apps/api/tessera_api/routers/spaces.py`, and the `cross_tenant_denied` audit write in `apps/api/tessera_api/routers/spaces.py` (`get_space` denial path).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The schema change, domain field, repository methods, and the shared
`require_company_admin` dependency that the user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Migration & domain entity (US3 schema dependency)

- [X] T003 Create additive migration `db/migrations/versions/0009_agent_credential_company_id.py` (down_revision `0008`): add nullable `company_id UUID` FK → `companies.id` to `agent_credentials`, add index `ix_agent_credentials_company` on `company_id`, backfill `company_id` from `spaces.company_id` of the first `scoped_space_ids[1]` for rows with ≥1 scoped space (leave NULL otherwise); downgrade drops the index then the column.
- [X] T004 Add `company_id UUID` column + `AgentCredentialModel.company_id` mapping to the agent-credentials model in `apps/api/tessera_api/adapters/models.py` (pure SQLAlchemy column, matches migration 0009).
- [X] T005 [P] Add `company_id: UUID | None = None` field to the `AgentCredential` entity in `packages/core/tessera_core/domain/entities.py` (pure data attribute, no framework import — Principle I/II).
- [X] T006 Apply and verify the migration: run `make migrate` (or `alembic -c db/alembic.ini upgrade head`) and confirm with `alembic -c db/alembic.ini history | grep 0009`.

### Repository scoped methods (consumed by US1–US3)

- [X] T007 [P] Extend repository port interfaces in `packages/core/tessera_core/ports/repositories.py` with the new scoped signatures: `ProposalRepository.get_by_id_for_company(proposal_id, company_id)` and `list_for_company(company_id, state=None, space_id=None)`; `ConnectorRepository.get_by_id_for_company(connector_id, company_id)`; `AgentCredentialRepository.get_by_id_for_company(credential_id, company_id)`.
- [X] T008 [US1] Implement `SqlProposalRepository.get_by_id_for_company` and `list_for_company` in `apps/api/tessera_api/adapters/repo.py` — join `UpdateProposalModel → DocumentModel → SpaceModel` filtered by `SpaceModel.company_id == company_id`, with optional `state`/`space_id` filters on the list; a miss returns `None`.
- [X] T009 [P] [US2] Implement `SqlConnectorRepository.get_by_id_for_company` in `apps/api/tessera_api/adapters/repo.py` — join `ConnectorModel → SpaceModel` filtered by `SpaceModel.company_id == company_id`; miss returns `None`.
- [X] T010 [P] [US3] Implement `SqlAgentCredentialRepository.get_by_id_for_company` in `apps/api/tessera_api/adapters/repo.py` — filter `AgentCredentialModel` by `company_id == company_id`; miss returns `None`.

### Shared per-company admin dependency (US6 root-cause fix)

- [X] T011 Add `require_company_admin(request) -> (user_info, company_id, membership)` to `apps/api/tessera_api/auth/oidc.py` — calls `require_company_context` (which loads and returns the `CompanyMembership`) and raises 403 generic body unless `membership.role == CompanyRole.ADMIN`. Module-level imports only (per repo convention for patchable routers).

**Checkpoint**: Schema, domain, repos, and `require_company_admin` ready — user stories can now proceed.

---

## Phase 3: User Story 1 - Proposals stay inside the company (Priority: P1) 🎯 MVP

**Goal**: List/get/approve/reject proposals only ever touch proposals whose
document belongs to the active company, and approve/reject additionally require
publish rights in the document's space.

**Independent Test**: As a Company B member, list/open/approve/reject a Company A
proposal → every attempt refused (or absent from list); Company A's document and
version history unchanged; and an in-company member lacking publish rights is
refused on approve.

### Tests for User Story 1 ⚠️ (write first, must FAIL before implementation)

- [X] T012 [P] [US1] Add cross-tenant proposal cases to `apps/api/tests/test_tenant_isolation.py` (use `two_company_setup`): Company B `GET /v1/proposals` excludes A's proposal; `GET /v1/proposals/{A_id}` → 403 generic body, no document content; `POST /v1/proposals/{A_id}/approve` → 403 with A's doc + version history unchanged; `POST /v1/proposals/{A_id}/reject` → 403 with proposal state unchanged. Assert a `cross_tenant_denied` audit record (entity_type `proposal`, entity_id, metadata.company_id) for each denial, and that the 403 body is identical to a non-existent proposal id (SC-005).
- [X] T013 [P] [US1] Add in-company role case to `apps/api/tests/integration/test_proposal_approval.py`: a Company A member without publish rights in the document's space who approves → 403 (FR-004), distinct from the tenant denial path.

### Implementation for User Story 1

- [X] T014 [US1] Rewrite `GET /v1/proposals` and `GET /v1/proposals/{id}` in `apps/api/tessera_api/routers/proposals.py` to use `require_company_context` + `list_for_company` / `get_by_id_for_company`; on a get miss, write `cross_tenant_denied` audit (entity_type `proposal`) and raise 403 generic body.
- [X] T015 [US1] Rewrite `POST /v1/proposals/{id}/approve` and `POST /v1/proposals/{id}/reject` in `apps/api/tessera_api/routers/proposals.py` to: `require_company_context`, load proposal via `get_by_id_for_company`, load the target document via `SqlDocumentRepository.get_by_id_for_company`, on miss audit `cross_tenant_denied` + 403; then build `AccessContext(user, space_permissions)` and call `can_approve_proposal` from `packages/core/tessera_core/permissions/access.py`, raising 403 when the decision is DENY (FR-004).
- [X] T016 [US1] Run the US1 tests (T012, T013) and the proposals integration suite; confirm all green and the denial 403 bodies match the not-found bodies.

**Checkpoint**: US1 fully functional and independently testable (MVP).

---

## Phase 4: User Story 2 - Connectors stay inside the company (Priority: P1)

**Goal**: Connector create requires the target space to belong to a company the
caller administers; connector sync requires the connector to belong to it, and a
cross-company sync enqueues no Celery job.

**Independent Test**: As a Company B administrator, create a connector on a
Company A space and sync a Company A connector → both refused; no connector
created, no sync job enqueued.

### Tests for User Story 2 ⚠️ (write first, must FAIL before implementation)

- [X] T017 [P] [US2] Add cross-tenant connector cases to `apps/api/tests/test_tenant_isolation.py`: Company B admin `POST /v1/spaces/{A_space}/connectors` → 403, no connector row created; `POST /v1/connectors/{A_id}/sync` → 403 and assert the Celery sync task was NOT enqueued (patch/spy the task). Assert `cross_tenant_denied` audit (entity_type `connector`/`space`) for each.

### Implementation for User Story 2

- [X] T018 [US2] Update `POST /v1/spaces/{space_id}/connectors` in `apps/api/tessera_api/routers/connectors.py` to use `require_company_admin` + `validate_space_for_company(space_id, company_id)` (replacing the global `is_admin` gate); on miss audit `cross_tenant_denied` + 403; bind the created connector to the validated space.
- [X] T019 [US2] Update `POST /v1/connectors/{id}/sync` in `apps/api/tessera_api/routers/connectors.py` to use `require_company_admin` + `SqlConnectorRepository.get_by_id_for_company`; on miss audit `cross_tenant_denied` + 403 and return BEFORE enqueuing the Celery sync task (FR-005).
- [X] T020 [US2] Run T017 and the connectors integration tests; confirm both green.

**Checkpoint**: US1 and US2 both work independently.

---

## Phase 5: User Story 3 - Agent access tokens stay inside the company (Priority: P1)

**Goal**: Token issuance validates every scoped space belongs to the active
company and binds `company_id`; revoke validates the token belongs to the active
company.

**Independent Test**: As a Company B administrator, issue a token scoped to a
Company A space and revoke a Company A token → both refused; no token issued; the
Company A token remains active.

### Tests for User Story 3 ⚠️ (write first, must FAIL before implementation)

- [X] T021 [P] [US3] Add cross-tenant agent-credential cases to `apps/api/tests/test_tenant_isolation.py`: Company B admin `POST /v1/agent-credentials` scoped to an A space → 403, no credential row created; `POST /v1/agent-credentials/{A_id}/revoke` → 403 and the A credential still active. Assert `cross_tenant_denied` audit (entity_type `agent_credential`). Add a positive case: a Company A admin issues a token scoped to A spaces → 200 and the stored credential carries `company_id == A`.

### Implementation for User Story 3

- [X] T022 [US3] Update `POST /v1/agent-credentials` in `apps/api/tessera_api/routers/agent_credentials.py` to use `require_company_admin`, validate EVERY `scoped_space_id` via `validate_space_for_company` (reject with 403 + `cross_tenant_denied` audit if any space is not in the active company — FR-006), and set `company_id = active company` on the issued credential. Response shape unchanged (`{ "credential": {…}, "token": "<once>" }`).
- [X] T023 [US3] Update `POST /v1/agent-credentials/{id}/revoke` in `apps/api/tessera_api/routers/agent_credentials.py` to use `require_company_admin` + `get_by_id_for_company`; on miss audit `cross_tenant_denied` + 403 and leave the token active.
- [X] T024 [US3] Run T021 and the agent-credentials tests; confirm green, including the positive `company_id`-bound issuance.

**Checkpoint**: All P1 stories (US1–US3) independently functional.

---

## Phase 6: User Story 4 - Member & permission writes stay inside the company (Priority: P2)

**Goal**: Bring member-write paths and the role-permission action to parity with
the already-correct `list_members` read path — verify the target space belongs to
the active company before the per-space role check.

**Independent Test**: As a Company B member, invite/change-role/remove/members-me
and set a role permission against a Company A space → every attempt refused
identically to the existing list-members refusal; an in-company member whose role
disallows the action is still refused on role.

### Tests for User Story 4 ⚠️ (write first, must FAIL before implementation)

- [X] T025 [P] [US4] Add cross-tenant member-write cases to `apps/api/tests/test_tenant_isolation.py`: Company B against a Company A space for `POST /v1/spaces/{A}/members`, `PUT /v1/spaces/{A}/members/{uid}`, `DELETE /v1/spaces/{A}/members/{uid}`, `GET /v1/spaces/{A}/members/me` → 403/404 revealing no Company A data; assert `cross_tenant_denied` audit (entity_type `space`) where applicable.
- [X] T026 [P] [US4] Add cross-tenant permission case to `apps/api/tests/test_tenant_isolation.py`: Company B admin `POST /v1/spaces/{A_space}/permissions` → 403 with `cross_tenant_denied` audit (entity_type `role_permission`/`space`).

### Implementation for User Story 4

- [X] T027 [US4] Update `invite_member`, `change_member_role`, `remove_member`, and `get_my_membership` in `apps/api/tessera_api/routers/members.py` to use `require_company_context` + `validate_space_for_company(space_id, company_id)` before invoking `MembershipService`; on miss audit `cross_tenant_denied` + generic 403/404 (no Company A data leaked). `MembershipService` role check stays unchanged.
- [X] T028 [US4] Update `create_permission` (`POST /v1/spaces/{space_id}/permissions`) in `apps/api/tessera_api/routers/spaces.py` to use `require_company_admin` + `validate_space_for_company` (replacing the global `is_admin` gate); on miss audit `cross_tenant_denied` + 403.
- [X] T029 [US4] Run T025, T026, and `apps/api/tests/integration/test_members.py`; confirm all green.

**Checkpoint**: US1–US4 independently functional.

---

## Phase 7: User Story 5 - Usage metrics reflect only the active company (Priority: P2)

**Goal**: `total_queries` and pending-proposal/drift counts are computed from the
active company only.

**Independent Test**: With known activity in both companies, a Company B
administrator's `GET /v1/metrics` totals exclude Company A's queries and
proposals.

### Tests for User Story 5 ⚠️ (write first, must FAIL before implementation)

- [X] T030 [P] [US5] Add per-company metrics case to `apps/api/tests/test_tenant_isolation.py`: seed query-audit + proposals for both companies; Company B admin `GET /v1/metrics` → `total_queries` and drift/pending counts reflect only B (exclude A). Assert no field aggregates across companies (SC-003).

### Implementation for User Story 5

- [X] T031 [US5] Tag the assistant "query" audit with company in `apps/api/tessera_api/routers/assistant.py`: add `metadata={"company_id": str(company_id)}` to the existing `action="query"` audit write (consistent with `cross_tenant_denied` metadata).
- [X] T032 [US5] Update `GET /v1/metrics` in `apps/api/tessera_api/routers/metrics.py` to use `require_company_admin` and compute scoped counts: `total_queries` = audit records where `action == "query"` and `record_metadata['company_id'].astext == str(company_id)`; drift/pending = `update_proposals` joined `documents → spaces` filtered by `spaces.company_id`. Response shape unchanged.
- [X] T033 [US5] Run T030 and the metrics tests; confirm green and values exclude the other company.

**Checkpoint**: US1–US5 independently functional.

---

## Phase 8: User Story 6 - Administrator power is scoped to a single company (Priority: P2)

**Goal**: Confirm the `require_company_admin` dependency (built in T011 and wired
in US2/US3/US4/US5) authorizes by the caller's ADMIN role in the OWNING company,
and that the global `is_admin` flag no longer gates any company-owned resource.

**Independent Test**: A user who is ADMIN of Company A but only MEMBER (or
non-member) of Company B is refused every admin-only action on Company B
resources; the same user succeeds on Company A resources.

### Tests for User Story 6 ⚠️ (write first, must FAIL before implementation)

- [X] T034 [P] [US6] Add per-company-admin cases to `apps/api/tests/test_tenant_isolation.py` using an ADMIN-role fixture variant (per quickstart: `create_access_token(..., is_admin=False)` + ADMIN `CompanyMembership`): admin-of-A / member-of-B attempts each admin-gated B action (connector create/sync, agent-credential issue/revoke, permission create, metrics) → 403 (SC-004); admin-of-A performs the same action on A → succeeds.

### Implementation / verification for User Story 6

- [X] T035 [US6] Audit every remaining `if not user_info.get("is_admin")` / global-`is_admin` gate across `apps/api/tessera_api/routers/` (grep) and confirm the ONLY surviving global gate is `PUT /v1/users/{id}/platform-role` in `apps/api/tessera_api/routers/admin.py` (FR-014). Replace any other lingering global gate on a company-owned resource with `require_company_admin`.
- [X] T036 [US6] Run T034; confirm cross-company admin refusals and same-company admin successes pass.

**Checkpoint**: All six user stories independently functional.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Validation, quality gates, and final verification across all stories.

- [X] T037 Run the full quickstart isolation suite: `cd apps/api && pytest tests/test_tenant_isolation.py -k "US1 or US2 or US3 or US4 or US5 or US6" -v` — all 15 quickstart scenarios pass.
- [X] T038 Run the full regression with coverage: `cd apps/api && pytest --cov=tessera_api --cov=tessera_core` — suite green, coverage ≥ 85% (matches the T001 baseline).
- [X] T039 [P] Verify SC-005 across all hardened flows: cross-company denial 403 bodies are byte-identical to not-found 403 bodies (assert in the isolation tests).
- [X] T040 [P] Run quality gates: `ruff check` and `black --check` over `apps/api` and `packages/core`; fix any violations.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories. T003→T004→T006 (migration before model verify before apply); T005 and T007 parallel; T008–T010 depend on T007; T011 independent of repos.
- **User Stories (Phase 3–8)**: All depend on Foundational completion.
  - US1 depends on T008; US2 on T009 + T011; US3 on T004/T005/T010 + T011; US4 on T011 (and existing `validate_space_for_company`); US5 on T011; US6 verifies T011's wiring across US2–US5.
  - With staffing, US1–US5 can proceed in parallel after Phase 2; US6 is best done last (it verifies the others' admin gates).
- **Polish (Phase 9)**: Depends on all targeted user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Independent after Phase 2 (needs T008).
- **US2 (P1)**: Independent after Phase 2 (needs T009, T011).
- **US3 (P1)**: Independent after Phase 2 (needs T004/T005/T010, T011).
- **US4 (P2)**: Independent after Phase 2 (needs T011).
- **US5 (P2)**: Independent after Phase 2 (needs T011).
- **US6 (P2)**: Cross-cutting verification of T011 wiring; run after US2–US5 land.

### Within Each User Story

- Tests are written FIRST and must FAIL before implementation.
- Repository/domain before router; router before integration verification.
- Story complete and green before moving to the next priority.

### Parallel Opportunities

- T005 ∥ T007 (different files: entities vs ports).
- T009 ∥ T010 (independent repo methods — but both edit `repo.py`; serialize the actual edits if one developer).
- All per-story test tasks (T012, T013, T017, T021, T025, T026, T030, T034) are `[P]` — written against different scenarios; T012/T017/T021/T025/T026/T030/T034 all append to `test_tenant_isolation.py`, so serialize the file writes if a single developer is editing.
- After Phase 2, US1–US5 implementation can proceed on different routers in parallel across developers.

---

## Parallel Example: Foundational Phase

```bash
# After T003/T004 (migration + model), these touch different files:
Task: "T005 Add AgentCredential.company_id in packages/core/tessera_core/domain/entities.py"
Task: "T007 Extend repo port interfaces in packages/core/tessera_core/ports/repositories.py"
Task: "T011 Add require_company_admin in apps/api/tessera_api/auth/oidc.py"
```

## Parallel Example: P1 stories after Foundational

```bash
# Different routers, no shared files (assign per developer):
Developer A: US1 — apps/api/tessera_api/routers/proposals.py
Developer B: US2 — apps/api/tessera_api/routers/connectors.py
Developer C: US3 — apps/api/tessera_api/routers/agent_credentials.py
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1: Setup (T001–T002).
2. Phase 2: Foundational (T003–T011) — CRITICAL, blocks all stories.
3. Phase 3: User Story 1 (T012–T016).
4. **STOP and VALIDATE**: the most severe gap (cross-company proposal read/write) is closed.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 → test → the P1 two-way proposal breach is closed (MVP).
3. US2 → test → connector cross-tenant create/sync closed.
4. US3 → test → agent-token cross-tenant issue/revoke closed.
5. US4 → US5 → US6 → P2 gaps and the global-admin root cause closed.
6. Phase 9 polish → full regression + quality gates.

### Notes

- [P] = different files, no dependencies; serialize edits that share a file (notably `repo.py` and `test_tenant_isolation.py`).
- Every denial path must write a `cross_tenant_denied` audit record AND return the generic 403 body identical to not-found (FR-010 / SC-005).
- Routers must use module-level imports so tests can patch repositories/audit (repo convention).
- API tests use `@pytest.mark.anyio` and `fastapi.testclient.TestClient` (sync).
- Commit after each task or logical group; keep Ruff + Black clean (Principle V).
