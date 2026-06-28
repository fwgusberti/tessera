# Phase 0 Research: Company-Scoped Admin Privileges

All NEEDS CLARIFICATION from Technical Context are resolved below. Three spec
clarifications (Session 2026-06-26) already fixed the denial shape, the migration
policy, and the audit scope; the decisions here translate those into the codebase.

## Decision 1 — Source of admin authority

**Decision**: Authority over company-owned data is derived **solely** from
`CompanyMembership.role == CompanyRole.ADMIN` in the *active company* resolved at
the request boundary. The global `users.is_admin` flag is no longer consulted for
any company-owned resource.

**Rationale**: The active company (and the caller's membership in it) is already
resolved once per request by `_resolve_company_membership` in `auth/oidc.py`
(features 031/035). Reusing it makes admin authority follow the active company
automatically — satisfying FR-001, FR-002, FR-005 and the multi-company story
(US3) with no new state. The global flag's only legitimate remaining use is the
platform-operator exception (Decision 5).

**Alternatives considered**:
- *Keep `is_admin` but also check company membership*: still leaks — a global
  admin would pass the override before the company check ran. Rejected.
- *Introduce a new per-company "super" role*: unnecessary; `CompanyRole.ADMIN`
  already exists and is assigned to company creators (companies.py / feature 032).

## Decision 2 — Threading admin status into the pure domain layer

**Decision**: Replace each `user.is_admin` short-circuit in
`permissions/access.py` with an explicit `is_company_admin: bool` parameter
(default `False`), and add an `is_company_admin: bool = False` field to
`AccessContext`. `MembershipService.invite/change_role/remove` take the same
boolean. The boolean is computed at the API boundary and passed inward.

**Sites changed** (`access.py`): `can_read_document`, `can_publish_document`
(hence `can_approve_proposal`), `can_admin_space`, `effective_space_role` (hence
`can_write_document`, `can_manage_members`, `can_read_space_document`).

**Rationale**: Constitution Principle I forbids the domain importing framework,
transport, or persistence code, and forbids it re-deriving company context. A
primitive `bool` is the minimal contract that keeps the predicates pure and unit
-testable while moving the *source* of the boolean to the API boundary. Default
`False` is fail-closed: any un-migrated caller is treated as a non-admin.

**Alternatives considered**:
- *Pass the whole `CompanyMembership` into domain functions*: couples the
  generic access layer to the onboarding entity and tempts future I/O. Rejected.
- *Query membership inside the domain*: the domain cannot do I/O (Principle I).
  Rejected.
- *Delete the override entirely and rely only on SpaceMembership*: would strip a
  company admin of authority over spaces they never explicitly joined, regressing
  legitimate in-company admin power (FR-007, SC-005). Rejected — the override is
  kept but re-sourced to per-company admin.

## Decision 3 — Exposing the caller's company role to read-path routers

**Decision**: Add `require_company_member(request) -> (user_info, company_id,
membership)` in `auth/oidc.py`, a thin wrapper over the existing
`_resolve_company_membership`. Routers that build authority decisions on a read
path (proposals, documents, members) switch from `require_company_context` to
`require_company_member` and compute
`is_company_admin = membership.role == CompanyRole.ADMIN`. Admin-only write paths
keep `require_company_admin` (which already returns the membership).

**Rationale**: `_resolve_company_membership` already fetches the membership, so
no extra DB round-trip is added — `require_company_context` simply discarded it.
This keeps the single-lookup performance characteristic of 035.

**Alternatives considered**: a separate repo call per router to fetch the role —
redundant query, rejected.

## Decision 4 — Shape of the cross-company / not-found response (FR-004, SC-003)

**Decision**: Every **by-ID** company-scoped lookup returns **HTTP 404** with a
generic not-found body for *both* a genuinely-absent resource and one owned by
another company. The two cases are byte-identical. Exactly one
`cross_tenant_denied` audit record is written whenever the scoped
`*_for_company` fetch returns `None` on an admin-gated by-ID path (FR-008).

This **supersedes feature 035's 403** denial for these by-ID paths: a distinct
403 "forbidden" would reveal that the resource exists in another tenant, which
FR-004 forbids ("A distinct 'forbidden' outcome MUST NOT be used for
cross-company access").

**Important distinction** — *in-company* authorization failures are unchanged:
a caller authenticated in their own active company who lacks the admin role still
receives **403 Forbidden**. That is not a cross-tenant case (the resource is in
their own company; no existence is disclosed across tenants). So:

| Situation | Status |
|-----------|--------|
| By-ID resource absent OR owned by another company | **404** (+ 1 audit record on by-ID path) |
| Caller is a non-admin in their *own* active company attempting an admin action | **403** |
| No active company context established | **403** (`no_company_context`) |
| Unauthenticated | **401** |
| Listing endpoint — other tenants' rows are filtered out | 200 with only own rows, **no** denial audit |

**Rationale**: Indistinguishability is the explicit requirement (SC-003). The
scoped repo cannot tell "absent" from "other tenant," so collapsing both to 404
is both correct and the only implementable behavior; auditing the `None` path
conservatively over-records genuine 404s, which is acceptable (FR-008 only
mandates a record exists for real cross-company attempts).

**Migration note**: existing 035 tests asserting `403` for cross-tenant by-ID
denials must be updated to `404`. The `cross_tenant_denied` audit assertion is
unchanged.

**Alternatives considered**:
- *Keep 403 for cross-tenant*: violates FR-004 (discloses existence). Rejected.
- *404 for cross-tenant but 403 for in-company non-admin → distinguishable*: kept
  intentionally; the in-company 403 discloses nothing about *other* tenants and
  preserves the existing UX for "you're not an admin here."

## Decision 5 — Retaining the platform-operator exception (FR-010)

**Decision**: The global `users.is_admin` flag and the `admin.py` endpoints that
read it (`PUT /v1/users/{id}/platform-role`, `GET /v1/admin/spaces`,
`PUT /v1/admin/spaces/{id}/retention`, `POST /v1/admin/reindex`) are left
**unchanged**. They are the explicitly-modeled, separately-gated cross-tenant
exception permitted by Constitution Principle VI.

**Rationale**: After this feature, company admins do **not** hold the global flag
(it is granted only via `set_platform_role`, itself global-admin-gated and
audited), so ordinary company admin status cannot reach these endpoints — exactly
what FR-010 requires. Redesigning or expanding platform-operator tooling is out
of scope (spec Out of Scope §1). `GET /v1/admin/spaces` and `POST /v1/admin/reindex`
are not currently audited; adding audit there is out of scope and noted as a
follow-up, not a blocker for this feature's guarantee.

## Decision 6 — Transition of existing users (FR-009, SC-007)

**Decision**: Data-only migration `0010_backfill_company_admin_memberships`
inserts a `CompanyRole.ADMIN` row into `company_memberships` for every
`companies.admin_user_id` that lacks one, scoped to that company. It does **not**:
- touch `users.is_admin` (retained for platform-operator use),
- elevate any existing non-admin member to admin,
- grant admin in any company the user did not create/own.

The migration is idempotent (`WHERE NOT EXISTS` / `ON CONFLICT DO NOTHING`).

**Rationale**: Company creation already grants the creator an ADMIN membership
(companies.py line ~149; feature 032), so for current data this is largely a
safety net guaranteeing SC-007 ("every owner holds an explicit company-admin
membership") and protecting any legacy/edge company whose creator membership was
never written. The clarification (Session 2026-06-26) explicitly limits the grant
to owned companies and forbids broader elevation.

**Alternatives considered**:
- *Auto-grant admin everywhere a global admin had a membership*: contradicts the
  clarification and would silently widen privilege. Rejected.
- *Drop `users.is_admin` in this migration*: it still gates platform-operator
  endpoints; dropping it is a separate, out-of-scope change. Rejected.
