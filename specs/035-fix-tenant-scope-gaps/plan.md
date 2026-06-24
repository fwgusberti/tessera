# Implementation Plan: Close Company & User Scope Gaps

**Branch**: `035-fix-tenant-scope-gaps` | **Date**: 2026-06-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/035-fix-tenant-scope-gaps/spec.md`

## Summary

An audit found five flows that were never retrofitted with the tenant-scoping
pattern introduced in feature 031 (`require_company_context` + `*_for_company`
repository methods + `cross_tenant_denied` audit). They leak or mutate data
across companies and gate powerful actions on a single global `is_admin` JWT
flag instead of the caller's role inside the company that owns the resource:

1. **Proposals** (`proposals.py`) — list/get/approve/reject use `require_user`
   and unscoped queries; any signed-in user can read and rewrite another
   company's published documents.
2. **Connectors** (`connectors.py`) — create/sync gated only by global
   `is_admin`; no check that the space/connector belongs to the active company.
3. **Agent credentials** (`agent_credentials.py`) — issue does not verify the
   scoped spaces belong to the active company; revoke does not verify the token
   belongs to it.
4. **Members & permissions** (`members.py`, `spaces.py`) — read path
   (`list_members`) validates the company, but `invite`/`change_role`/`remove`/
   `members/me` and `create_permission` do not.
5. **Metrics** (`metrics.py`) — aggregates `total_queries` and pending proposals
   across **all** companies.

The technical approach reuses the established 031 pattern verbatim: promote each
handler from `require_user` to `require_company_context`, add `*_for_company`
repository methods that filter by `company_id` (directly or via a join through
`spaces.company_id`), emit `cross_tenant_denied` audit records on every denial,
and replace global-`is_admin` gates with a new `require_company_admin`
dependency that authorizes by the caller's `CompanyRole.ADMIN` membership in the
active company. One schema change (migration 0009) adds `company_id` to
`agent_credentials`, the only resource with no single-space anchor to scope by.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, SQLAlchemy (async), joserfc (JWT),
itsdangerous (SessionMiddleware), Alembic (migrations), Celery (connector sync),
pytest + anyio

**Storage**: PostgreSQL (async SQLAlchemy). One additive migration (0009):
`agent_credentials.company_id` (nullable FK + backfill). No other schema change —
proposals, connectors, members, metrics are scoped via existing `company_id`
columns and joins through `spaces.company_id`.

**Testing**: pytest + anyio; integration tests use
`fastapi.testclient.TestClient` (sync); cross-tenant tests use the
`two_company_setup` fixture in `tests/conftest.py`

**Target Platform**: Linux server (Docker/Kubernetes)

**Project Type**: Web service (FastAPI REST API) — monorepo with
`apps/api` (transport) and `packages/core` (domain)

**Performance Goals**: No new hot path. Added per-request work is one indexed
`company_id`/`space_id` lookup already performed by sibling scoped endpoints.

**Constraints**: Reuse the 031 scoping pattern exactly; denial and not-found
MUST be indistinguishable (403 with generic body); every denial audited; no new
resource types; domain layer (`packages/core`) MUST stay free of transport and
persistence imports.

**Scale/Scope**: 5 routers hardened, ~4 new repository methods, 1 new auth
dependency (`require_company_admin`), 1 migration. Cross-tenant test added for
every hardened flow (SC-001/SC-002).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | PASS | Authorization decisions (`can_approve_proposal`) already live in `packages/core/permissions`; this feature only wires routers/repos to them. No business rule moves into transport. |
| II. Separation of Concerns | PASS | Company scoping is enforced at the API boundary via `require_company_context` and pushed into repository `*_for_company` methods; domain entities unchanged except adding `company_id` to the `AgentCredential` entity (a data attribute, no framework import). |
| III. Data Locality & Consent | PASS | No client-side persistence; no new user data captured. |
| IV. Test-Driven Development | PASS (planned) | Each gap gets a failing cross-tenant test first (Company B acting on Company A → 403/empty), then the fix. 85%+ coverage maintained. |
| V. Quality Gates | PASS (planned) | Ruff + Black must pass before commit. |
| VI. Tenant Data Isolation | **PASS — this feature's purpose** | Closes the audit follow-up TODO recorded in the constitution v1.4.0 sync report. See Tenant Isolation section below. |

**Tenant Isolation section** (required per Security Requirements):

- **Tables accessed & scoping**:
  - `update_proposals` → scoped via join `update_proposals.document_id →
    documents.space_id → spaces.company_id`. New: `get_by_id_for_company`,
    `list_for_company`.
  - `documents` → existing `get_by_id_for_company` (031).
  - `connectors` → scoped via join `connectors.space_id → spaces.company_id`.
    New: `get_by_id_for_company`.
  - `spaces` → existing `get_by_id_for_company` / `validate_space_for_company`
    (031), used by connectors, agent-credential issuance, member writes,
    permission writes.
  - `agent_credentials` → **new `company_id` column** (migration 0009); new
    `get_by_id_for_company`; issuance validates every `scoped_space_id` belongs
    to the active company.
  - `space_memberships` → member writes gated by `validate_space_for_company`
    before the existing `MembershipService` role check.
  - `role_permissions` → `create_permission` gated by
    `validate_space_for_company`.
  - `audit_records` → `total_queries` metric scoped by `company_id` written into
    the "query" audit `metadata` (consistent with existing `cross_tenant_denied`
    metadata); pending-proposal metric scoped via the proposal→space join.
- **New data-access paths**: all listed above receive a `company_id` predicate;
  no method accepts a bare entity ID without `company_id` (Principle VI rule).
- **Cross-tenant isolation tests** (one per flow, Company B vs Company A):
  list/get/approve/reject proposal; create/sync connector; issue/revoke agent
  credential; invite/change-role/remove/members-me; create permission; metrics
  count. Each asserts 403 (or empty), unchanged target data, and a
  `cross_tenant_denied` audit record (SC-001, SC-002, SC-006).
- **Intentional platform-wide operation (FR-014)**: the global `is_admin`
  (platform super-admin) capability is retained ONLY for the explicitly modelled,
  separately role-gated `PUT /v1/users/{id}/platform-role` endpoint
  (`admin.py`), which is already audit-logged. It is NOT used as an authorization
  shortcut for any company-owned resource after this feature. This is the single
  documented cross-tenant exception.

No constitution violations. Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/035-fix-tenant-scope-gaps/
├── plan.md              # This file
├── research.md          # Phase 0 output — scoping-strategy decisions
├── data-model.md        # Phase 1 — agent_credentials.company_id + scoping joins
├── quickstart.md        # Phase 1 — cross-tenant validation scenarios
├── contracts/
│   └── scope-gaps.md    # Phase 1 — per-endpoint before/after access matrix
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (files touched)

```text
apps/api/tessera_api/
├── auth/
│   └── oidc.py                  # NEW require_company_admin dependency (US6)
├── routers/
│   ├── proposals.py             # require_company_context + scoped repo + can_approve (US1)
│   ├── connectors.py            # require_company_admin + space/connector company check (US2)
│   ├── agent_credentials.py     # require_company_admin + scoped-space + scoped revoke (US3)
│   ├── members.py               # require_company_context + validate_space_for_company (US4)
│   ├── spaces.py                # create_permission: company check + require_company_admin (US4/US6)
│   └── metrics.py               # require_company_admin + per-company aggregation (US5/US6)
└── adapters/
    ├── repo.py                  # NEW *_for_company methods (proposals, connectors, agent creds)
    ├── models.py                # AgentCredentialModel.company_id column
    └── (assistant.py writes company_id into "query" audit metadata)  # routers/assistant.py

packages/core/tessera_core/
├── domain/entities.py           # AgentCredential.company_id field
└── ports/repositories.py        # extend repo interfaces with *_for_company signatures

db/migrations/versions/
└── 0009_agent_credential_company_id.py   # NEW additive migration

apps/api/tests/
├── conftest.py                  # reuse/extend two_company_setup; admin-role variant
├── test_tenant_isolation.py     # NEW classes: US1–US6 cross-tenant cases
└── integration/                 # per-router happy-path + denial regression tests
```

**Structure Decision**: Existing monorepo layout (031 precedent). Transport and
scoping live in `apps/api`; authorization predicates stay in
`packages/core/tessera_core/permissions`. No new packages or top-level dirs.

## Complexity Tracking

> No Constitution Check violations — section intentionally empty.
