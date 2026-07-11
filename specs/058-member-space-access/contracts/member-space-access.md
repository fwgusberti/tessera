# API Contracts: Space Access Management for Company Members (058)

All endpoints require a Bearer JWT and an active-company context (existing
`X-Company-Id`/session convention). Errors follow the established shapes:
structured `{"error": {"code", "message"}}` where the touched router already
uses it, bare-string `detail` where it doesn't (members.py convention).

## NEW — GET `/v1/companies/members/{user_id}/space-access`

Member-centric access view. **Caller: company admin** (`CompanyAdminContext`).

**Path params**: `user_id` — UUID of a member of the caller's active company.

**200 response**:

```json
{
  "member": { "user_id": "…", "display_name": "…", "email": "…" },
  "spaces": [
    {
      "id": "…",
      "name": "Engineering",
      "slug": "engineering",
      "parent_space_id": null,
      "direct_role": "viewer",
      "effective_role": "viewer",
      "is_direct": true
    },
    {
      "id": "…",
      "name": "Engineering / Docs",
      "slug": "docs",
      "parent_space_id": "…",
      "direct_role": null,
      "effective_role": "viewer",
      "is_direct": false
    },
    {
      "id": "…",
      "name": "Finance",
      "slug": "finance",
      "parent_space_id": null,
      "direct_role": null,
      "effective_role": null,
      "is_direct": false
    }
  ]
}
```

Every space of the active company appears exactly once (FR-001, FR-012).
`direct_role`/`effective_role` ∈ `admin | editor | viewer | null`.

**Errors**:

- `401` — unauthenticated.
- `403` — caller is not an admin of the active company (FR-009).
- `404` (generic `not_found`) — `user_id` is not a member of the active
  company, including cross-company probes (indistinguishable from absent;
  emits `cross_tenant_denied` audit on cross-company hits, 053/054 convention).

## MODIFIED — GET `/v1/spaces`

Auth context changes `CompanyContext` → `CompanyMemberContext` (same caller
requirements; adds the caller's company-membership row server-side).

**Behavior change (company admins only, FR-005)**: response now includes every
space of the active company. Spaces the admin doesn't hold/inherit a membership
in are returned with `"effective_role": "admin", "is_direct": false` (implicit
admin, feature 036). Non-admin members: response unchanged (membership-derived
only).

**Response shape unchanged**:

```json
{ "spaces": [ { …space fields…, "effective_role": "admin", "is_direct": false } ] }
```

## MODIFIED — GET `/v1/spaces/{space_id}` and GET `/v1/spaces/{space_id}/ancestors`

Access check gains the same company-admin branch: a company admin can fetch any
space of the active company. Cross-company IDs keep returning generic `404`
with `cross_tenant_denied` audit. Response shapes unchanged.

## REUSED (unchanged) — write path & search

The panel drives writes exclusively through existing endpoints; contracts are
unchanged and already authorize company admins on any company space
(implicit-admin, feature 036):

- `POST /v1/spaces/{space_id}/members` — body `{ "user_id": UUID, "role": "admin"|"editor"|"viewer" }` → `201 { "membership": … }`; `400` already a member; `403` not allowed; `404` space/user not in company.
- `PUT /v1/spaces/{space_id}/members/{user_id}` — body `{ "role": … }` → `200`; existing role-change constraints apply.
- `DELETE /v1/spaces/{space_id}/members/{user_id}` → `204`; existing last-admin protections apply.
- `GET /v1/spaces/{space_id}/members/search?q=…` → eligible company members (join-path parity verified by tests, FR-006).

All grant/change/revoke operations keep emitting their existing audit records
(FR-010).

## UI contract (web)

- `/users` (Users page): each roster row exposes a "Spaces" action for company
  admins → opens `MemberSpaceAccessPanel` for that member (FR-004).
- `MemberSpaceAccessPanel`: lists the new endpoint's `spaces[]`; rows with
  `effective_role = null` offer *grant* (role select, default `viewer`); rows
  with `is_direct = true` offer *change role* and *revoke*; inherited-only rows
  are informational (FR-002, FR-003; data-model invariants).
- `/spaces` empty state (FR-007): non-admin with zero accesses → "No spaces
  have been shared with you yet. A company administrator can grant you
  access."; company admin with zero spaces → existing "no spaces" copy.
