# Data Model: Fix Create Company "Failed to fetch"

## Schema Changes

**None.** This feature is a bug fix in transport-layer configuration (CORS) and
frontend error handling. No database entities, tables, columns, or migrations are
added or modified.

## Affected Entities (unchanged)

For reference, the entity touched by the existing `POST /v1/companies` handler:

### Company

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID PK | Auto-generated |
| `name` | varchar(255) | Required, non-empty |
| `industry` | varchar(100) \| null | Optional |
| `team_size` | varchar(20) \| null | Must be one of the valid enum values |
| `admin_user_id` | UUID FK → users | Set to the creating user |
| `created_at` | timestamptz | Auto-set |

### CompanyMembership

| Field | Type | Notes |
|-------|------|-------|
| `user_id` | UUID FK → users | |
| `company_id` | UUID FK → companies | |
| `role` | enum(ADMIN, MEMBER) | Creating user gets ADMIN |

### OnboardingProgress (state transition only)

After successful company creation, `advance_step(user_id, "invite",
company_join_method="created")` is called. No schema change — existing column updated.

## Validation Rules (unchanged)

- `name`: 1–255 characters, required
- `industry`: ≤ 100 characters, optional
- `team_size`: must be one of `{"1-10", "11-50", "51-200", "201-1000", "1000+"}` or null
