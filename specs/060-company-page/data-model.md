# Data Model: Company Page (060)

**Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

No new tables, columns, or migrations. The feature reads and updates existing
entities and adds one repository operation.

## Entities

### Company (existing — `companies` table)

| Field | Type | Constraints | Role in this feature |
|---|---|---|---|
| `id` | UUID | PK | Tenant key; derived from the token context only |
| `name` | str | required, 1–255 chars (non-blank after trim) | Displayed; editable by admins |
| `industry` | str \| null | ≤100 chars | Displayed ("Not provided" when null); editable, nullable |
| `team_size` | str \| null | one of `1-10`, `11-50`, `51-200`, `201-1000`, `1000+` | Displayed ("Not provided" when null); editable, nullable |
| `admin_user_id` | UUID | FK users | Untouched (ownership transfer out of scope) |
| `created_at` | datetime (tz) | server default | Displayed, never editable |
| `updated_at` | datetime (tz) | auto `onupdate` | Bumped automatically on save |

**Validation rules** (API boundary, mirroring `POST /v1/companies`):

- `name`: reject empty or whitespace-only (422), reject >255 chars (422);
  stored value preserved on rejection (FR-005).
- `industry`: free text ≤100 chars or `null` (clears the value).
- `team_size`: member of `VALID_TEAM_SIZES` or `null` (clears); otherwise
  422 `invalid_team_size`.

**State transitions**: none — profile fields are plain mutable attributes;
concurrency is last-write-wins (spec assumption).

### CompanyMembership (existing — read-only here)

Resolved by the auth dependencies to establish `(user_info, company_id,
membership)`. `membership.role` (`admin` \| `member`) decides view-only vs
edit (FR-004/FR-008). Not modified by this feature.

### AuditRecord (existing — insert-only here)

One record per successful PATCH (FR-010, SC-004):

| Field | Value |
|---|---|
| `actor_type` | `"user"` |
| `actor_id` | admin's user id (token `sub`) |
| `action` | `"company.updated"` |
| `entity_type` | `"company"` |
| `entity_id` | company id |
| `metadata` | `{"company_id": "<uuid>", "changed": {"<field>": {"from": <old>, "to": <new>}}}` — only fields whose value actually changed |

## Repository operation (new)

`CompanyRepository.update_details(company_id: UUID, *, name: str,
industry: str | None, team_size: str | None) -> Company | None`

- Port: `packages/core/tessera_core/ports/repositories/company.py`
- Adapter: `apps/api/tessera_api/adapters/repositories/company.py`
- Semantics: load `WHERE id = :company_id` (tenant-scoped by definition —
  the tenant key is the row's own id); apply all three fields; flush; return
  the mapped domain `Company`. Return `None` when no row matches (router
  translates to 404, which is unreachable through the guarded endpoint but
  keeps the method honest).

## Client-side types (`apps/web/lib/companies.ts`)

```ts
export interface CompanyProfile {
  id: string;
  name: string;
  industry: string | null;
  team_size: string | null;
  created_at: string;        // ISO 8601
  role: "admin" | "member";  // caller's role in this company
}

export interface UpdateCompanyData {
  name: string;
  industry: string | null;
  team_size: string | null;
}
```

Shared option lists move to `apps/web/lib/companyOptions.ts`
(`INDUSTRIES`, `TEAM_SIZES`) and are imported by both the onboarding
`CompanyForm` and the new company page.
