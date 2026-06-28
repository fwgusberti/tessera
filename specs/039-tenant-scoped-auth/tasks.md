# Tasks: Tenant-Scoped Authentication

**Input**: Design documents from `/specs/039-tenant-scoped-auth/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/auth.yaml ✅

**Tests**: Included — Constitution §IV (TDD) is NON-NEGOTIABLE. Write each test block first and confirm it fails before implementing.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Core domain types, schema changes, and JWT utilities that every user story depends on. No user story work can begin until this phase is complete.

**⚠️ CRITICAL**: All Phase 2+ work is blocked until this phase is complete.

- [X] T001 [P] Create `TokenKind` domain type (`"full"` | `"select"` | `"onboarding"`) in `packages/core/tessera_core/domain/token_kind.py`
- [X] T002 [P] Extend `RefreshToken` domain entity with `company_id: UUID | None` and `token_kind: TokenKind` fields (default `"full"`) in `packages/core/tessera_core/domain/refresh_token.py`
- [X] T003 [P] Write Alembic migration `db/migrations/versions/0011_tenant_scoped_auth.py` — add `company_id UUID FK`, `token_kind VARCHAR(20) NOT NULL DEFAULT 'full'` to `refresh_tokens`; add `is_active BOOLEAN NOT NULL DEFAULT TRUE` to `companies`; add index `ix_refresh_tokens_company` on `refresh_tokens(company_id) WHERE company_id IS NOT NULL`
- [X] T004 [P] Add `company_id` (UUID FK, nullable) and `token_kind` (String, non-nullable, default `"full"`) columns to the SQLAlchemy `RefreshToken` ORM model in `apps/api/tessera_api/adapters/models/refresh_token.py`
- [X] T005 Extend `RefreshTokenRepository.create` and `get_by_hash` to persist and return `company_id` and `token_kind` in `apps/api/tessera_api/adapters/repositories/refresh_token.py` (depends on T004)
- [X] T006 Update `create_access_token` in `apps/api/tessera_api/auth/jwt_auth.py` to accept `token_kind: TokenKind` and `company_id: UUID | None` parameters and embed them as JWT claims (`token_kind` always present; `company_id` omitted when `None`) (depends on T001)

**Checkpoint**: Domain types, DB schema, ORM models, repository, and JWT builder are ready — user story implementation can now begin.

---

## Phase 2: User Story 1 — Authenticate and Scope to a Tenant (Priority: P1) 🎯 MVP

**Goal**: Login issues the correct `token_kind` based on membership count; data-access endpoints reject non-`full` tokens; refresh preserves scope.

**Independent Test**: Log in as a single-membership user → verify `token_kind == "full"` and `company_id` is present → make a data-access call → verify it succeeds.

### Tests for User Story 1 ⚠️ Write first — confirm they FAIL before implementing

- [X] T007 [P] [US1] Write failing login classification tests (single-membership → `full`, multi-membership → `select`, zero-membership → `onboarding`; verify JWT claims; verify `select`/`onboarding` tokens receive 403 on data endpoints) in `apps/api/tests/auth/test_auth_login.py`
- [X] T008 [P] [US1] Write failing refresh scope-preservation tests (refresh a `full` token → new access token carries same `token_kind` and `company_id`; refresh a `select` token → same `select` kind, no `company_id`) in `apps/api/tests/auth/test_auth_refresh.py`

### Implementation for User Story 1

- [X] T009 [US1] Update `apps/api/tessera_api/auth/oidc.py` — decode `token_kind` and `company_id` from JWT claims and expose them on the resolved principal; update `_resolve_company_membership` to raise 403 `credential_not_scoped` when `token_kind` is `"select"` or `"onboarding"` before any company-context check (depends on T006)
- [X] T010 [US1] Update the login handler in `apps/api/tessera_api/routers/auth.py` — count the user's active memberships; issue `"full"` token (with `company_id`) for exactly one membership, `"select"` token (no `company_id`) for multiple memberships, `"onboarding"` token for zero memberships; persist `company_id` and `token_kind` on the new refresh token record; include `token_kind` in the `auth.login.success` audit metadata (depends on T005, T006, T009)
- [X] T011 [US1] Update the refresh handler in `apps/api/tessera_api/routers/auth.py` — load `company_id` and `token_kind` from the refresh token record and pass them to `create_access_token` so the new access token carries the same scope (depends on T005, T006)

**Checkpoint**: Login returns correct `token_kind`; `select`/`onboarding` tokens are blocked from data endpoints; refresh preserves scope. US1 independently testable.

---

## Phase 3: User Story 2 — Reject Authentication for Non-Member Tenants (Priority: P1)

**Goal**: `POST /auth/select-tenant` validates membership and company status before issuing a `full` token; revoked memberships and deactivated companies are rejected on every request.

**Independent Test**: Attempt `POST /auth/select-tenant` with a valid `select` token but targeting a company the user has no membership in → verify 403 `not_a_member`.

### Tests for User Story 2 ⚠️ Write first — confirm they FAIL before implementing

- [X] T012 [P] [US2] Write failing select-tenant rejection tests (non-member company → 403 `not_a_member`; `full` token → 403 `wrong_token_kind`; `onboarding` token → 403 `wrong_token_kind`; inactive company → 403 `company_suspended`; unauthenticated → 401) in `apps/api/tests/auth/test_select_tenant.py`
- [X] T013 [P] [US2] Write failing cross-tenant isolation tests (`select` token blocked from all data endpoints; `full` token for Company A returns 403 on Company B resources; revoked membership → 403 on next request) in `apps/api/tests/test_tenant_auth_isolation.py`

### Implementation for User Story 2

- [X] T014 [US2] Add `require_select_token` FastAPI dependency to `apps/api/tessera_api/auth/oidc.py` — verifies the token is `"select"`-kind; raises 403 `wrong_token_kind` for any other kind (depends on T009)
- [X] T015 [US2] Extend `_resolve_company_membership` in `apps/api/tessera_api/auth/oidc.py` — query `companies.is_active`; raise 403 `company_suspended` when `False`; re-validate active membership from `company_memberships` on every request; raise 403 `not_a_member` when absent (depends on T014)
- [X] T016 [US2] Implement `POST /v1/auth/select-tenant` in `apps/api/tessera_api/routers/auth.py` — guard with `require_select_token`; validate active membership in the target company via `_resolve_company_membership`; call `create_access_token` with `token_kind="full"` and the target `company_id`; persist a new scoped refresh token; emit `auth.credential.issued` audit log (actor, company_id, timestamp); return `TokenResponse` (depends on T005, T006, T014, T015)

**Checkpoint**: Non-members, deactivated companies, and wrong token kinds are rejected at `select-tenant`. Revoked memberships rejected on subsequent requests. US2 independently testable.

---

## Phase 4: User Story 3 — Admin Authority Confined to the Scoped Tenant (Priority: P2)

**Goal**: `is_admin` in the JWT reflects the membership role for the scoped company only; admin-protected routes reject credentials scoped to a different company.

**Independent Test**: Log in as admin of Company A → attempt an admin-only operation on Company B's resources → verify 403.

### Tests for User Story 3 ⚠️ Write first — confirm they FAIL before implementing

- [X] T017 [P] [US3] Write failing cross-tenant admin isolation tests (admin of Company A cannot perform admin ops on Company B; dual-admin scoped to Company A cannot exercise Company B admin rights in the same session) in `apps/api/tests/test_tenant_auth_isolation.py`

### Implementation for User Story 3

- [X] T018 [US3] Ensure `is_admin` is resolved from the membership record for the scoped company at token issuance in `apps/api/tessera_api/routers/auth.py` — the `is_admin` JWT claim must derive from the `CompanyMembership.role` for the `company_id` being scoped to, not from any global user flag (depends on T010, T016)
- [X] T019 [US3] Verify that admin-guarded FastAPI dependencies in `apps/api/tessera_api/auth/oidc.py` enforce admin status only against the company_id embedded in the token — confirm no path exists where `is_admin` from one company credential grants admin access to another company's resources (depends on T015, T018)

**Checkpoint**: Admin rights are strictly confined to the scoped company. US3 independently testable alongside US1 and US2.

---

## Phase 5: User Story 4 — Switch Active Tenant Without Full Re-Login (Priority: P3)

**Goal**: A user holding a `full`-scoped credential can switch to another company they are a member of without re-entering credentials.

**Independent Test**: Hold a `full` token for Company A → call `POST /auth/select-tenant` with Company B (a valid membership) → receive a new `full` token scoped to Company B.

### Tests for User Story 4 ⚠️ Write first — confirm they FAIL before implementing

- [X] T020 [P] [US4] Write failing tenant-switch tests (full token + member company → new full token scoped to target; full token + non-member company → 403 `not_a_member`) in `apps/api/tests/auth/test_select_tenant.py`

### Implementation for User Story 4

- [X] T021 [US4] Create a combined `require_unscoped_or_full_token` dependency in `apps/api/tessera_api/auth/oidc.py` — accepts both `"select"` and `"full"` token kinds; rejects `"onboarding"` with 403 `wrong_token_kind` (depends on T014)
- [X] T022 [US4] Extend `POST /v1/auth/select-tenant` in `apps/api/tessera_api/routers/auth.py` to use `require_unscoped_or_full_token` instead of `require_select_token`; revoke the existing refresh token when switching from a `full` token before issuing the new scoped pair (depends on T016, T021)

**Checkpoint**: Multi-tenant users can switch active tenant with a single call. US4 independently testable alongside US1–US3.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates and end-to-end validation across all user stories.

- [X] T023 [P] Run `ruff check` and `black --check` across all modified files and fix any violations (`packages/core/`, `apps/api/tessera_api/`, `db/migrations/`)
- [X] T024 [P] Run the full API test suite (`cd apps/api && uv run pytest tests/ -v`) and verify coverage does not drop below the pre-feature baseline; fix any regressions
- [X] T025 Execute all six quickstart.md validation scenarios end-to-end (single-membership auto-scope, multi-membership select flow, select-tenant refuses non-member, revoked membership, refresh scope preservation, zero-membership onboarding token) — validated via automated tests: TestLoginTokenKindClassification (SC1,SC2,SC6), TestSelectTenantRejections (SC3), TestRevokedMembershipBlocksExistingToken (SC4), TestRefreshScopePreservation (SC5)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No external dependencies — start immediately. Blocks all user story phases.
- **User Story 1 (Phase 2)**: Requires Phase 1 complete. No dependency on US2/US3/US4.
- **User Story 2 (Phase 3)**: Requires Phase 1 complete. Builds on oidc.py changes from US1 (T009) — start US2 tests (T012, T013) in parallel with US1 implementation.
- **User Story 3 (Phase 4)**: Requires US1 (T010) and US2 (T015, T016) complete.
- **User Story 4 (Phase 5)**: Requires US2 (T016) complete.
- **Polish (Phase 6)**: Requires all desired user stories complete.

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 1 — no inter-story dependencies.
- **US2 (P1)**: Starts after Phase 1 — tests can be written in parallel with US1 implementation; implementation starts after T009.
- **US3 (P2)**: Starts after US1 (T010) and US2 (T015, T016) are complete.
- **US4 (P3)**: Starts after US2 (T016) is complete.

### Within Each User Story

1. Write tests first → confirm they **FAIL** → implement until tests pass
2. Domain types before repositories
3. Repository before router
4. Guards (oidc.py) before endpoint handler

### Parallel Opportunities (Phase 1)

```
T001 ──────────────────────► T006
T002 ──────────────────────► T005 (via T004)
T003 (independent migration)
T004 ──────────────────────► T005
```

All four of T001, T002, T003, T004 can start simultaneously.

### Parallel Opportunities (Phase 2 — US1)

```
T007 (login tests)    ─ write in parallel ─►
T008 (refresh tests)  ─ write in parallel ─►  then implement T009 → T010 → T011
```

---

## Implementation Strategy

### MVP (User Stories 1 + 2 Only)

1. Complete **Phase 1**: Foundational — domain types, migration, ORM, repository, JWT builder
2. Complete **Phase 2**: US1 — login classifies token kind; data-access guard rejects non-full tokens; refresh preserves scope
3. Complete **Phase 3**: US2 — select-tenant endpoint enforces membership; deactivated companies rejected on every request
4. **STOP and VALIDATE**: Run `tests/auth/` and `tests/test_tenant_auth_isolation.py`; execute quickstart scenarios 1–4
5. Deploy/demo if ready

### Incremental Delivery

1. Phase 1 → Foundation ready
2. Phase 2 → Token kind classification live (MVP auth behaviour)
3. Phase 3 → Non-member gate + select-tenant endpoint live (security gate complete)
4. Phase 4 → Admin confinement verified (P2 quality increment)
5. Phase 5 → Tenant switching live (P3 UX improvement)
6. Phase 6 → Polish and full validation

---

## Notes

- `[P]` tasks have no dependency on each other and touch different files
- `[Story]` label maps each task to its user story for traceability
- Constitution §IV (TDD): tests MUST be written first and confirmed failing — this is non-negotiable
- Constitution §VI (Tenant Isolation): every data-access query must include `company_id` scoping — verify in code review
- Commit after each phase checkpoint; tag with story ID for traceability
- The `select-tenant` endpoint's `tenant_selection_required: true` flag in `TokenResponse` signals the client to show a tenant picker — no backend change needed for this UI hint beyond the boolean field
