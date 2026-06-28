# Implementation Plan: Company-Scoped Admin Privileges

**Branch**: `036-company-scoped-admin` | **Date**: 2026-06-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/036-company-scoped-admin/spec.md`

## Summary

Today "admin" is a **platform-wide** status: the global `users.is_admin` flag is
read as an authorization shortcut in the domain permission layer
(`packages/core/.../permissions/access.py`) and in several routers, so any user
carrying it is implicitly treated as an administrator of **every** company. This
is a critical cross-tenant isolation breach (Constitution Principle VI).

This feature retires `is_admin` as a source of authority over company-owned data.
Admin authority becomes a pure function of the caller's **per-company role** —
`CompanyMembership.role == CompanyRole.ADMIN` in the *active* company resolved at
the request boundary (the same context established by features 031/035). The
global flag survives only as the gate for the explicitly-modeled, audited
platform-operator endpoints in `admin.py` (the single documented cross-tenant
exception).

Technical approach, reusing the 031/035 pattern:

1. **Domain stays pure**: replace every `user.is_admin` short-circuit in
   `access.py` (5 sites) and `MembershipService` with an explicit
   `is_company_admin: bool` parameter computed at the API boundary. The domain
   never learns about companies or sessions — it receives one boolean.
2. **API boundary computes the boolean** from the `CompanyMembership` already
   resolved by `_resolve_company_membership`. A new `require_company_member`
   dependency returns `(user_info, company_id, membership)` so read-path routers
   can derive `is_company_admin` without a second DB hit.
3. **Cross-company by-ID access is indistinguishable from missing**: every
   company-scoped by-ID lookup returns **404 + generic body** for both a
   genuinely-absent resource and one owned by another company, emitting exactly
   one `cross_tenant_denied` audit record on that path (FR-004, FR-008). This
   supersedes 035's 403 denial for these by-ID paths. A non-admin acting inside
   *their own* company still receives **403** (not a cross-tenant case).
4. **Migration 0010 (data-only)** backfills an explicit `CompanyRole.ADMIN`
   membership for every `companies.admin_user_id` (the creator/owner), so no
   owner loses access when the global flag stops conferring it (FR-009, SC-007).
   It elevates nobody else.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, SQLAlchemy (async), joserfc (JWT),
itsdangerous (SessionMiddleware), Alembic (migrations), pytest + anyio

**Storage**: PostgreSQL (async SQLAlchemy). **No schema/DDL change.** One
data-only migration (0010) backfills owner admin memberships into the existing
`company_memberships` table. The `users.is_admin` column is retained (it still
gates the platform-operator endpoints) — not dropped.

**Testing**: pytest + anyio; integration tests use
`fastapi.testclient.TestClient` (sync); cross-tenant tests extend the
`two_company_setup` fixture in `apps/api/tests/conftest.py` with an admin-role
variant. Domain permission changes are unit-tested in
`packages/core/tests/test_permissions.py` (pytest-asyncio markers there; anyio in
the API package — do not mix).

**Target Platform**: Linux server (Docker/Kubernetes)

**Project Type**: Web service (FastAPI REST API) — monorepo with `apps/api`
(transport) and `packages/core` (domain)

**Performance Goals**: No new hot path. `is_company_admin` is derived from the
`CompanyMembership` already fetched by `_resolve_company_membership`; read-path
routers that previously called `require_company_context` now call
`require_company_member`, reusing that same single indexed lookup (no extra
query).

**Constraints**: Domain layer (`packages/core`) MUST stay free of transport and
persistence imports — admin status enters as a plain `bool`. Cross-company by-ID
denial and genuine not-found MUST be byte-identical (same 404 status and body)
and audited exactly once. No new resource types, no new tables, no DDL.

**Scale/Scope**: 2 domain files (`access.py`, `membership.py`), 1 auth
dependency module, ~5 routers re-wired off the global flag, 1 data-only
migration. Per-company authorization unit tests + one cross-company isolation
test per admin-gated flow (US1–US4).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | PASS | Authority decisions remain in `packages/core/.../permissions`. The domain receives an `is_company_admin: bool`; it gains no framework, transport, or persistence import. The "which company is active" decision stays at the API boundary. |
| II. Separation of Concerns | PASS | Product/domain definitions unchanged by technology. Company scoping is enforced at the API boundary and threaded into pure predicates via a primitive boolean — no infrastructure leaks into the domain. |
| III. Data Locality & Consent | PASS | No client-side persistence; no new user data captured. |
| IV. Test-Driven Development | PASS (planned) | Each authority change gets a failing per-company test first (admin in A denied in B), then the fix. Migration 0010 gets an idempotency/backfill test. 85%+ coverage maintained. |
| V. Quality Gates | PASS (planned) | Ruff + Black must pass before commit. |
| VI. Tenant Data Isolation | **PASS — this feature's purpose** | Removes the last implicit cross-tenant authorization shortcut (`is_admin`) over company-owned data. See Tenant Isolation section. |

**Tenant Isolation section** (required per Security Requirements):

- **Tables accessed & scoping**:
  - `company_memberships` → authoritative source of admin authority; read via the
    existing `get_membership(user_id, company_id)` already resolved at the request
    boundary. Migration 0010 backfills owner ADMIN rows. No bare-ID access.
  - `documents`, `spaces`, `update_proposals`, `connectors`, `agent_credentials`
    → already scoped by `company_id` (031/035) via `*_for_company` repo methods.
    This feature only changes the **authorization** decision applied after the
    scoped fetch (was: global-admin override; now: per-company admin), and
    standardizes the denial to 404.
  - `space_memberships`, `role_permissions` → management gated by per-company
    admin (was global admin) after the existing `validate_space_for_company`
    check (035).
  - `users.is_admin` → read ONLY by the platform-operator endpoints in `admin.py`;
    never consulted for company-owned data after this feature.
- **New data-access paths**: none. No method gains a bare entity ID; admin
  status is a derived boolean, not a query key.
- **Cross-tenant isolation tests** (one per admin-gated flow, admin-in-A vs
  company B): manage members, manage permissions, manage connectors, issue/revoke
  agent credentials, read metrics, approve/reject proposals, reindex/edit
  documents. Each asserts the action is denied, target data is unchanged, the
  denial is **404 + generic body indistinguishable from genuine not-found**
  (SC-003), and exactly one `cross_tenant_denied` audit record exists for by-ID
  attempts / none for filtered listings (SC-004). Multi-company test (US3):
  admin-in-A + member-in-B succeeds with A active, denied (403) with B active.
- **Intentional cross-tenant exception (FR-010)**: the global `is_admin`
  capability is retained ONLY for the explicitly-modeled, audited platform-operator
  endpoints in `admin.py` (`PUT /v1/users/{id}/platform-role`,
  `GET /v1/admin/spaces`, `PUT /v1/admin/spaces/{id}/retention`,
  `POST /v1/admin/reindex`). After this feature these are unreachable via ordinary
  company admin status (company admins do not hold the global flag). Building or
  expanding platform-operator tooling is out of scope; this is the single
  documented exception, carried forward from 035.

No constitution violations. Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/036-company-scoped-admin/
├── plan.md              # This file
├── research.md          # Phase 0 — authority-model & denial-shape decisions
├── data-model.md        # Phase 1 — AccessContext field, authority source, migration 0010
├── quickstart.md        # Phase 1 — per-company / cross-company validation scenarios
├── contracts/
│   └── authorization-matrix.md   # Phase 1 — per-endpoint authority source before/after
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (files touched)

```text
packages/core/tessera_core/
├── permissions/access.py        # is_company_admin replaces user.is_admin in
│                                 #   AccessContext + can_read_document /
│                                 #   can_publish_document / can_admin_space /
│                                 #   effective_space_role / can_read_space_document
│                                 #   / can_write_document / can_manage_members
└── services/membership.py       # invite/change_role/remove accept is_company_admin

apps/api/tessera_api/
├── auth/oidc.py                 # NEW require_company_member -> (user_info, company_id, membership);
│                                 #   helper is_company_admin(membership)
├── routers/proposals.py         # AccessContext.is_company_admin from membership; 404 on cross-company
├── routers/documents.py         # reindex/create use per-company admin; 404 on cross-company
├── routers/members.py           # pass is_company_admin; 404 on cross-company
├── routers/spaces.py            # permission management uses per-company admin
├── routers/metrics.py           # confirm no global is_admin consumption (035 already require_company_admin)
└── adapters/audit.py            # (reused) cross_tenant_denied writer — no change

apps/api/tessera_api/routers/admin.py   # UNCHANGED — documented platform-operator exception

db/migrations/versions/
└── 0010_backfill_company_admin_memberships.py   # NEW data-only migration (FR-009)

apps/api/tests/
├── conftest.py                  # admin-role variant of two_company_setup
└── test_company_scoped_admin.py # NEW — US1–US4 per-company + cross-company cases
packages/core/tests/
└── test_permissions.py          # per-company admin unit cases (is_company_admin)
```

**Structure Decision**: Existing monorepo layout (031/035 precedent). Transport
and the active-company decision live in `apps/api`; authorization predicates stay
pure in `packages/core/.../permissions`. No new packages, tables, or top-level
dirs.

## Complexity Tracking

> No Constitution Check violations — section intentionally empty.
