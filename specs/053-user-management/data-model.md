# Phase 1 Data Model: Company User Management Page

This feature introduces **no new persistent tables or columns**. It reads existing
tables and adds one in-memory domain value object to shape the read result.

## Existing tables (read-only in this feature)

### `company_memberships`
The association carrying a user's role within a company. Source of the roster and
the role each row displays.

| Column       | Type        | Notes                                             |
|--------------|-------------|---------------------------------------------------|
| `id`         | UUID (PK)   |                                                   |
| `user_id`    | UUID (FK → `users.id`, ON DELETE CASCADE) | the member          |
| `company_id` | UUID (FK → `companies.id`, ON DELETE CASCADE) | **tenant scope key** |
| `role`       | varchar(20) | `"admin"` or `"member"` (`CompanyRole`)           |
| `joined_at`  | timestamptz |                                                   |

Unique constraint: `(user_id, company_id)`.

### `users`
Supplies the identifying information shown per row.

| Column         | Type         | Notes                        |
|----------------|--------------|------------------------------|
| `id`           | UUID (PK)    | joined on `company_memberships.user_id` |
| `email`        | varchar(255) | fallback identifier (FR-004) |
| `display_name` | varchar(255) | primary identifier (FR-004)  |

## New domain value object

### `CompanyMemberListing` (`packages/core/tessera_core/domain/company_member_listing.py`)
A framework-free row describing one company member for display. Mirrors the existing
`CompanyMemberMatch` value object, with the company `role` added.

| Field          | Type          | Source                              |
|----------------|---------------|-------------------------------------|
| `user_id`      | `UUID`        | `users.id`                          |
| `display_name` | `str`         | `users.display_name`                |
| `email`        | `str`         | `users.email`                       |
| `role`         | `CompanyRole` | `company_memberships.role`          |

Re-exported from `tessera_core.domain.entities` alongside the other domain types.

## Query

`SqlCompanyRepository.list_members(company_id: UUID) -> list[CompanyMemberListing]`

```sql
SELECT u.id, u.display_name, u.email, cm.role
FROM company_memberships cm
JOIN users u ON u.id = cm.user_id
WHERE cm.company_id = :company_id
ORDER BY u.display_name;
```

- **Tenant scope**: the `WHERE cm.company_id = :company_id` predicate is mandatory
  (Principle VI); `company_id` originates from the authenticated `CompanyAdminContext`,
  never from client input.
- **Ordering**: by `display_name` for a stable, scannable roster (SC-005).

## Validation / display rules

- **FR-003 / SC-004**: every row carries a `CompanyRole` — `"administrator"` or
  `"member"` — so no row is ever role-less. (The API returns the raw enum value
  `admin`/`member`; the UI renders the human labels "administrator"/"member".)
- **FR-004 / Edge case "missing display information"**: the UI shows `display_name`
  and, beneath it, `email`; if `display_name` is empty it falls back to `email` so
  no row is blank or unidentifiable.
- **FR-007 / single-member company**: the query naturally returns the one row (the
  admin viewing the page); the page renders it rather than an empty state.
