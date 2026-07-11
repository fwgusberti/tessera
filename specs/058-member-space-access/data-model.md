# Data Model: Space Access Management for Company Members (058)

**No database schema changes.** The feature reuses existing tables and adds one
in-memory read model in the domain layer.

## Existing entities (reused, unchanged)

### SpaceMembership (`space_memberships`)

The authoritative access record — created/updated/deleted by this feature
through the existing `MembershipService` only.

| Field | Type | Notes |
|---|---|---|
| id | UUID | PK |
| space_id | UUID | FK → spaces; tenant scope derives from the space's `company_id` |
| user_id | UUID | FK → users |
| role | enum `SpaceRole` | `admin` \| `editor` \| `viewer` |
| invited_by_user_id | UUID | actor who granted access |

Invariants (existing, unchanged): unique per `(space_id, user_id)` — duplicate
grant raises "already a member" (mapped to 400); role-change/removal rules
(e.g., last-admin protections) enforced by `MembershipService`.

### Space (`spaces`)

Read-only in this feature. `company_id` scopes every query;
`parent_space_id` drives access inheritance (recursive CTE, role propagates
downward).

### CompanyMembership (`company_memberships`)

Read-only. Defines who is a *manageable member* (target must hold a row for the
caller's active company) and who is a *company admin* (caller's `role`,
resolved at the request boundary — `CompanyAdminContext` /
`CompanyMemberContext`).

### AuditRecord (`audit_log`)

Written only via existing paths: `member_invited`, `member_role_changed`,
`member_removed` (from `MembershipService`) and `cross_tenant_denied` probes.
No new audit actions.

## New domain read model (no persistence)

### MemberSpaceAccess (`packages/core/tessera_core/domain/member_space_access.py`)

One row per company space, describing a specific member's standing on it.

| Field | Type | Notes |
|---|---|---|
| space | `Space` | the company space |
| direct_role | `SpaceRole \| None` | the member's own `space_memberships` row, if any |
| effective_role | `SpaceRole \| None` | direct or inherited-from-ancestor role; `None` = no access |
| is_direct | bool | `True` only when `direct_role` is set |

Derivation (in `MemberAccessService`):
`list_by_company(company_id)` (all spaces) ⟕ `list_accessible_by_user(member_id,
company_id)` (effective role + is_direct via existing CTE) ⟕
`list_by_user(member_id)` filtered to company spaces (direct role).

Invariants:

- Every space of the company appears exactly once; spaces of other companies
  never appear (both source queries are `company_id`-scoped).
- `is_direct = (direct_role is not None)`; inherited-only access has
  `direct_role = None`, `effective_role != None`.
- Revoke/change controls apply only where `is_direct` — inherited access is
  displayed as informational (it follows the ancestor membership).

## Modified read semantics (no schema impact)

### SpaceAccess (existing, `tessera_core/domain/space_access.py`)

For **company admins**, the accessible set becomes: membership-derived accesses
(unchanged values) ∪ every remaining company space as
`SpaceAccess(effective_role=SpaceRole.ADMIN, is_direct=False)` — the in-memory
expression of the implicit-admin rule (feature 036). Non-admin members:
unchanged.

## State transitions

Access lifecycle (all via existing `MembershipService`, audited):

```text
(no access) --grant(role)--> member of space (direct)
member --change_role(new)--> member with new role
member --revoke--> (no access; inherited access may remain via ancestors)
(company membership removed) --> company context unavailable → no space reachable
```
