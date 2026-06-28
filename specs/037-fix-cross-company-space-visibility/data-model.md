# Phase 1 Data Model: Confine Space Visibility to the Active Company

**No schema change. No migration.** This feature removes one query method and adds audit
rows to the existing `audit_records` table. The model notes below describe the entities as
they participate in space visibility and the one behavioral change to each.

## Entities (existing — unchanged structure)

### Company (tenant)
- `id: UUID` — the active company resolved at the request boundary
  (`require_company_context` → `company_id`, from JWT claim or session
  `active_company_id`).
- Owns zero or more Spaces. A person acts on behalf of exactly one company per request.

### Space
- `id: UUID`, `slug`, `name`, `sector`, `company_id: UUID` (owner — **already present and
  indexed**), `default_language`, `retention_policy: JSONB`, `confidence_threshold`.
- **Visibility rule (the invariant this feature enforces)**: a Space is visible to a
  request iff `space.company_id == active company_id`. There is no membership-level or
  group-level narrowing of the *visible set* — every space of the active company is
  visible to that company's authorized members (spec Edge Case: "Space with no individual
  members" is still visible to the company's admins). In-space *role* (read/write/admin)
  is resolved separately and is unchanged by this feature.

### CompanyMembership
- `(user_id, company_id, role)`. Establishes that a person may act as a company. Unchanged.
- A person's `users.is_admin` (platform-wide) is **not** consulted for everyday space
  visibility after this feature.

### RolePermission
- `(space_id, idp_group, role, max_confidentiality)`. Maps an IdP group to an in-space
  role. **Behavioral change**: no longer joined to compute the *visible set* (that join
  lived only inside the removed `list_for_user`). Still read per-space for in-space role
  resolution, which is already space/company-scoped.

### AuditRecord (existing table `audit_records`)
- `actor_type`, `actor_id`, `action`, `entity_type`, `entity_id`, `metadata: JSONB`,
  timestamp. Append-only. **Behavioral change**: a new `action` value is emitted on the
  operator surface (see below). No column change.

## SpaceRepository port — method delta

| Method | Before | After |
| ------ | ------ | ----- |
| `get_by_id_for_company(space_id, company_id)` | scoped by-ID, 404 on miss | unchanged |
| `list_by_company(company_id)` | `WHERE company_id = :active` | unchanged — **the** visibility query |
| `list_all()` | every company's spaces | unchanged — reachable **only** from audited `/v1/admin/*` |
| `list_for_user(user)` | `is_admin → list_all`; else unscoped group-join | **REMOVED** from port + impl |

After this change the `SpaceRepository` port exposes no method that returns
multi-tenant data without an explicit `company_id` argument, except `list_all()` whose
sole caller is the audited operator surface.

## Audit action: `cross_company_admin_access`

Emitted by the platform-operator endpoints when an authorized global admin reads or
mutates across companies (FR-008, FR-009).

| Field | Value |
| ----- | ----- |
| `actor_type` | `"user"` |
| `actor_id` | the global admin's user id |
| `action` | `"cross_company_admin_access"` |
| `entity_type` | `"space"` (or `"spaces"` for the list/reindex sweep) |
| `entity_id` | the affected space id, or a sentinel/zero UUID for fleet-wide ops |
| `metadata` | `{ "endpoint": <path>, "operation": "list" | "retention" | "reindex", ... }` |

Distinct from the existing `cross_tenant_denied` action (a *denied* everyday by-ID
attempt) so audit queries cleanly separate authorized operator access from blocked leaks.

## State transitions

None. Visibility is a pure read predicate (`space.company_id == active company_id`); no
entity changes state as part of this feature.

## Validation rules (restated from requirements)

- **FR-001/FR-003**: every space-visibility read is `list_by_company(active company_id)`;
  no path returns spaces of another company to a company-member request.
- **FR-004**: `users.is_admin` confers no everyday visibility; it gates only the audited
  operator surface.
- **FR-007**: by-ID access to another company's space is 404 + generic body, identical to
  a non-existent id (no existence disclosure) — preserved from 036.
- **FR-008/FR-009**: cross-company operator access is the single documented exception and
  emits `cross_company_admin_access`.
