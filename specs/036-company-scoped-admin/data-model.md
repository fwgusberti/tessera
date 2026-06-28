# Phase 1 Data Model: Company-Scoped Admin Privileges

This feature is an **authorization-scoping** change. There is **no DDL** — no new
table, column, index, or type. The only persistence change is a data-only
backfill (migration 0010). The "model" changes are to in-memory domain shapes
that carry an authority boolean.

## Authority source (conceptual)

| Concept | Before | After |
|---------|--------|-------|
| "Is this caller an admin?" over company-owned data | `User.is_admin` (global, platform-wide) | `CompanyMembership.role == CompanyRole.ADMIN` in the **active** company |
| Where it is decided | inside pure domain predicates (`user.is_admin`) | at the API boundary, passed in as `is_company_admin: bool` |
| `users.is_admin` flag | authorizes everything everywhere | authorizes ONLY the platform-operator endpoints in `admin.py` |

`CompanyMembership` (existing entity, unchanged) is the authoritative record:

```
CompanyMembership
  id: UUID
  user_id: UUID
  company_id: UUID
  role: CompanyRole   # ADMIN | MEMBER  ← the source of admin authority
  joined_at: datetime
```

Resolved per request by `SqlCompanyRepository.get_membership(user_id, company_id)`
via `_resolve_company_membership` (auth/oidc.py). No change to its schema or repo.

## Domain shape changes (in-memory only, `packages/core`)

### `AccessContext` (permissions/access.py)

Add one field; default fail-closed.

```
AccessContext
  user: User
  space_permissions: list[RolePermission]
  is_company_admin: bool = False      # NEW — replaces reads of ctx.user.is_admin
```

Functions that read `ctx.user.is_admin` (`can_read_document`,
`can_publish_document` → `can_approve_proposal`, `can_admin_space`) read
`ctx.is_company_admin` instead.

### Space-membership predicate signatures (permissions/access.py)

Add a trailing `is_company_admin: bool = False` parameter; replace `user.is_admin`
reads in `effective_space_role` and `can_read_space_document`:

```
effective_space_role(user, space_id, memberships, is_company_admin=False)
can_write_document(user, space_id, memberships, is_company_admin=False)
can_manage_members(user, space_id, memberships, is_company_admin=False)
can_read_space_document(user, space_id, memberships, is_company_admin=False)
```

A company admin is implicit `SpaceRole.ADMIN` for spaces **in their own company**
(callers guarantee the space belongs to the active company via the existing
`validate_space_for_company` check — feature 035). This preserves FR-007 / SC-005
without re-introducing cross-company reach.

### `MembershipService` (services/membership.py)

`invite`, `change_role`, `remove` gain `is_company_admin: bool = False` and pass
it to `can_manage_members`. They no longer rely on `actor.is_admin`.

## Persistence change — Migration 0010 (data-only)

`db/migrations/versions/0010_backfill_company_admin_memberships.py`

- **upgrade()**: for every `companies` row, ensure a `company_memberships` row
  exists with `(user_id = companies.admin_user_id, company_id = companies.id,
  role = 'admin')`. Insert only when absent; if a membership row already exists
  with `role = 'member'`, **do not** change it (clarification: owners get admin,
  but no existing member is silently elevated — and the company owner is the
  creator, expected to already be admin). Generate `id`/`joined_at` as the table
  defaults dictate.
  - Implement with a single `INSERT ... SELECT ... WHERE NOT EXISTS` so it is
    idempotent and safe to re-run.
- **downgrade()**: no-op (cannot distinguish backfilled rows from organically
  created ones, and removing owner admin access would be unsafe). Document this.

No `users.is_admin` value is read or written by this migration.

### Validation / invariants after migration (SC-007)

- Every `companies.admin_user_id` has exactly one `company_memberships` row with
  `role = 'admin'` for that company.
- No user holds `role = 'admin'` in a company where, before migration, they held
  only `role = 'member'`.
- Count of `role = 'admin'` memberships increases by **at most** the number of
  owner companies missing the row; it never decreases.

## State transitions

None. Roles already transition through the existing member-management flow
(`MembershipService` / companies.py); this feature changes *who is authorized to
drive those transitions*, not the transitions themselves.
