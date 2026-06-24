# Phase 0 Research: Close Company & User Scope Gaps

All unknowns are resolved against the existing 031 tenant-isolation
implementation. There are no NEEDS CLARIFICATION items; the open decisions are
**how** to apply the established pattern to each gapped flow.

## Established pattern (from feature 031) — the baseline to reuse

- **Boundary dependency**: `require_company_context(request) -> (user_info,
  company_id)` (oidc.py) resolves the active company from the JWT `company_id`
  claim or session, then **re-validates the membership in the DB** (catches
  revocation mid-session, FR-012). Returns 403 `no_company_context` when absent
  (FR-011).
- **Scoped reads**: repositories expose `get_by_id_for_company(id, company_id)`
  and `list_by_company(company_id)` that add an explicit `company_id` predicate.
  A miss returns `None`.
- **Indistinguishable denial (FR-010)**: on a `None` result the router writes a
  `cross_tenant_denied` audit record and raises `403` with a generic body
  (`{"error": {"code": "forbidden", "message": "Access denied"}}`) — identical
  whether the row is missing or owned by another company.
- **Audit on denial (FR-013)**: `write_audit(..., action="cross_tenant_denied",
  entity_type=<resource>, entity_id=<id>, metadata={"company_id": str(cid)})` —
  the existing `spaces.get_space` denial is the reference implementation.

Decision: every gap below is closed by mechanically applying this baseline. The
only design choices are the join path used to reach `company_id` and one schema
change.

---

## Decision 1 — Proposal scoping path (US1)

**Decision**: Scope proposals via the join
`update_proposals.document_id → documents.space_id → spaces.company_id`. Add
`SqlProposalRepository.get_by_id_for_company(proposal_id, company_id)` and
`list_for_company(company_id, state, space_id)`. The router uses
`require_company_context`, loads the proposal scoped, loads the target document
via the existing `SqlDocumentRepository.get_by_id_for_company`, and on a miss
emits `cross_tenant_denied` + 403.

**Rationale**: A proposal has exactly one document, and a document already
carries `space_id`/`company_id` (031). No new column needed; the join mirrors
how documents are already scoped.

**Approval authorization (FR-004)**: After tenant scoping, approve/reject must
also require publish rights. The domain already exposes
`can_approve_proposal(ctx, document)` (delegates to `can_publish_document`) in
`packages/core/tessera_core/permissions/access.py`. The router builds an
`AccessContext(user, space_permissions)` exactly as the documents publish path
does and denies with 403 when the decision is `DENY`. This keeps the role rule
in the domain (Principle I).

**Alternatives considered**:
- *Add `company_id` directly to `update_proposals`* — rejected: denormalizes an
  immutable derivation and needs a backfill migration for no query benefit.
- *Filter in Python after a global fetch* — rejected: violates Principle VI
  ("explicit `company_id` filter" in the query) and leaks via timing/count.

---

## Decision 2 — Connector scoping path (US2)

**Decision**: Scope connectors via `connectors.space_id → spaces.company_id`.
- *Create*: `validate_space_for_company(space_id, company_id)` (existing helper)
  before constructing the `Connector`.
- *Sync*: add `SqlConnectorRepository.get_by_id_for_company(connector_id,
  company_id)` (join to `spaces`); a miss → `cross_tenant_denied` + 403 and **no
  Celery task is enqueued** (FR-005 / acceptance "no sync job is started").

**Rationale**: A connector always has exactly one `space_id` (NOT NULL), so the
join is unambiguous and needs no new column.

**Alternatives considered**: adding `connectors.company_id` — rejected as
redundant with the space FK.

---

## Decision 3 — Agent-credential ownership (US3) — the one schema change

**Decision**: Add a `company_id` column to `agent_credentials` (migration 0009,
nullable FK to `companies`, backfilled from the company of the credential's
scoped spaces). Add `AgentCredential.company_id` to the domain entity and
`SqlAgentCredentialRepository.get_by_id_for_company`.
- *Issue*: bind `company_id = active company`; validate **every**
  `scoped_space_id` belongs to that company (reuse `validate_space_for_company`
  per id); reject otherwise (FR-006).
- *Revoke*: `get_by_id_for_company(credential_id, company_id)`; miss →
  `cross_tenant_denied` + 403, token stays active.

**Rationale**: Unlike proposals/connectors, a credential has a *list* of spaces
(and the list may be empty), so there is no single-space anchor to scope by.
Constitution Principle VI requires "an explicit `company_id` filter" on the
query and prohibits methods that "accept a bare entity ID without … the
`company_id`." A direct, indexed, auditable owning column is the
constitution-aligned choice and makes revoke a one-line scoped lookup.

**Backfill**: existing rows (early-stage data) are mapped to the company of
their first scoped space; rows with no scoped spaces are left NULL and treated as
un-revocable-by-tenant until reissued. Column stays nullable to avoid a failing
NOT NULL backfill; the issuance path always sets it going forward.

**Alternatives considered**:
- *Derive ownership from `scoped_space_ids` at revoke time* — rejected: breaks
  for empty lists and for tokens whose spaces span (incorrectly created)
  multiple companies; pushes scoping logic out of the query.

---

## Decision 4 — Member & permission writes (US4)

**Decision**: Bring the write paths to parity with the already-correct
`list_members` read path: call `require_company_context` then
`validate_space_for_company(space_id, company_id)` **before** invoking
`MembershipService` (which already enforces the per-space role rule). Applies to
`invite_member`, `change_member_role`, `remove_member`, `get_my_membership`
(members.py) and `create_permission` (spaces.py). `get_my_membership` returns
the same generic 403/404 for a cross-company space so it reveals nothing
(FR-007, acceptance "does not reveal Company A data").

**Rationale**: The read path already demonstrates the exact pattern; the fix is
to stop using bare `require_user` on the sibling writes. The role check is
unchanged and stays in the domain `MembershipService`.

**Alternatives considered**: moving the company check into `MembershipService` —
rejected: company context is a transport-boundary concern (Principle VI: "MUST
be established at the request boundary … MUST NOT be re-derived deeper in the
stack").

---

## Decision 5 — Per-company metrics (US5)

**Decision**: Compute both metrics from the active company only.
- *documents_with_drift / pending proposals*: count `update_proposals` joined
  through `documents → spaces` filtered by `spaces.company_id`.
- *total_queries*: write `metadata={"company_id": str(company_id)}` into the
  existing `action="query"` audit record (assistant.py) and count audit records
  where `action == "query"` and `record_metadata['company_id'] == str(cid)`.

**Rationale**: `audit_records` has no `company_id` column, only a JSONB
`metadata`. The existing `cross_tenant_denied` records already carry
`company_id` in `metadata`; tagging the "query" record the same way is
consistent and needs no migration on the high-volume audit table. PostgreSQL
JSONB key filtering (`record_metadata['company_id'].astext == ...`) is
first-class.

**Alternatives considered**:
- *Add `audit_records.company_id` column* — rejected for this feature: a
  migration touching the busiest write table for a single read-side metric is
  disproportionate; the metadata approach is consistent with the existing denial
  records. (Left as a future defense-in-depth item, like the RLS TODO.)

---

## Decision 6 — Per-company admin authorization (US6)

**Decision**: Add `require_company_admin(request) -> (user_info, company_id,
membership)` in oidc.py. It calls `require_company_context` (which already loads
and returns the `CompanyMembership`) and raises 403 unless
`membership.role == CompanyRole.ADMIN`. Replace every
`if not user_info.get("is_admin")` gate on a **company-owned** resource
(connectors, agent credentials, role permissions, metrics) with this dependency.

**Rationale**: `CompanyMembership.role` (ADMIN/MEMBER) already exists and is
assigned to company creators (feature 032). Authorizing by membership role in
the **owning** company is the single root-cause fix behind US2/US3/US5 and the
P2 permission write. The global `is_admin` JWT flag is a platform-operator
capability, not a per-company role.

**Retained global exception (FR-014)**: `PUT /v1/users/{id}/platform-role`
(admin.py) legitimately requires platform super-admin and is already
role-gated + audit-logged. It is the sole documented cross-tenant operation and
keeps using the global `is_admin`. No other endpoint may.

**Alternatives considered**:
- *Keep `is_admin` and add a separate company check alongside it* — rejected:
  leaves the misleading global gate in place and invites the next endpoint to
  rely on it again.

---

## No new dependencies

All changes reuse existing packages (FastAPI, SQLAlchemy, Alembic, joserfc,
Celery, pytest/anyio). The only new artifact is migration
`0009_agent_credential_company_id.py`.
