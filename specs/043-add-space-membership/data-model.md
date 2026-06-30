# Phase 1 Data Model: Add Space Membership (Frontend)

No new persisted tables or columns. This feature introduces one new **read
projection** assembled from existing tables, plus client-side UI state.

## Existing entities reused (unchanged)

- **User** (`users`): `id`, `email`, `display_name`. Source of search match fields.
- **CompanyMembership** (`company_memberships`): `user_id`, `company_id`, `role`.
  Scopes the search to the active company (Constitution Principle VI).
- **SpaceMembership** (`space_memberships`): `space_id`, `user_id`, `role`.
  Used both to exclude existing members from search results and, unchanged, to
  persist the new membership via the existing `POST /v1/spaces/{id}/members`
  flow (`MembershipService.invite`).

## New read projection: `CompanyMemberSearchResult`

Not a domain entity with its own table — a query-time shape returned by the new
search endpoint and consumed by the frontend picker.

| Field | Type | Source | Notes |
|---|---|---|---|
| `user_id` | UUID | `users.id` | Used as the value submitted to `POST /members` |
| `display_name` | string | `users.display_name` | Primary label shown in results |
| `email` | string | `users.email` | Secondary label; also the searchable field |

**Construction rule**: `SELECT users.id, users.display_name, users.email FROM
company_memberships JOIN users ON users.id = company_memberships.user_id WHERE
company_memberships.company_id = :company_id AND (users.email ILIKE :pattern OR
users.display_name ILIKE :pattern) AND users.id NOT IN (SELECT user_id FROM
space_memberships WHERE space_id = :space_id) ORDER BY users.display_name LIMIT
20`.

**Validation rules**:
- `:pattern` is `%<trimmed query>%`; query MUST be ≥2 characters (enforced
  client-side per FR-007; the query simply yields normal — possibly broad —
  results if called with a shorter string, since no new rate-limiting layer is
  introduced).
- `company_id` MUST come from the authenticated session's active company
  (`CompanyMemberContext`), never from a request parameter.
- `space_id` MUST be validated to belong to `company_id` before the query runs
  (reuses `validate_space_for_company`), so a foreign space_id 404s rather than
  leaking which users exist.

## Frontend UI state (`AddMemberForm`)

Component-local state, not persisted:

| Field | Type | Lifecycle |
|---|---|---|
| `query` | string | Reset on successful add or on form close |
| `results` | `CompanyMemberSearchResult[]` | Replaced on each debounced search response |
| `searchStatus` | `idle \| loading \| empty \| error` | Drives FR-008 empty/loading messaging |
| `selected` | `CompanyMemberSearchResult \| null` | Cleared on successful add; retained on submit failure (FR-010) |
| `role` | `"admin" \| "editor" \| "viewer"` | Defaults to `"viewer"`; retained on submit failure (FR-010) |
| `submitStatus` | `idle \| submitting \| error` | Drives FR-006 distinct error messaging |
| `submitError` | one of: `already_member \| forbidden \| ineligible \| network \| null` | Maps to the four FR-006 failure messages |

No state transitions touch persisted storage beyond the existing
`POST /v1/spaces/{id}/members` call already used by the prior form.
