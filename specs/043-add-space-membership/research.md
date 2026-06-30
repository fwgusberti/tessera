# Phase 0 Research: Add Space Membership (Frontend)

No open `NEEDS CLARIFICATION` markers remain in the Technical Context — the one
material ambiguity (search endpoint authorization scope) was resolved during
`/speckit-clarify`. This document records the implementation-approach decisions
made while turning the spec into a concrete plan.

## Decision: Search endpoint shape and placement

- **Decision**: Add `GET /v1/spaces/{space_id}/members/search?q=<term>` to the
  existing `apps/api/tessera_api/routers/members.py` router, alongside
  `list_members` and `invite_member`.
- **Rationale**: The endpoint is space-scoped (results are "who can be added to
  *this* space"), and authorization mirrors `invite_member`'s `can_manage_members`
  check exactly. Keeping it in `members.py` reuses `_require_space_in_company` /
  `validate_space_for_company` and the existing `CompanyMemberContext` dependency
  instead of introducing a new auth context type.
- **Alternatives considered**: A company-level `GET /v1/companies/{id}/members`
  endpoint was considered (simpler, reusable elsewhere) but rejected because the
  clarified requirement (FR-002a) scopes authorization and exclusion to one
  specific space — a company-level endpoint would need the same per-space checks
  bolted on anyway, with no reuse benefit yet.

## Decision: Query implementation

- **Decision**: A single SQL query joins `company_memberships` to `users` filtered
  by `company_id = :company_id` and `(email ILIKE :pattern OR display_name ILIKE
  :pattern)`, then excludes any `user_id` already present in `space_memberships`
  for the target `space_id` (via `NOT IN` subquery or `LEFT JOIN ... IS NULL`),
  ordered by `display_name`, limited to 20 rows.
- **Rationale**: Matches Constitution Principle VI (explicit `company_id` filter,
  no bare ID lookups) and FR-003 (exclude existing space members) in one
  round-trip. 20-row cap keeps payloads small and avoids needing pagination UI
  for a typeahead.
- **Alternatives considered**: Full-text search (`pg_trgm`/`tsvector`) would scale
  better for very large companies but is unnecessary complexity for current scale
  (no existing index infra for this); `ILIKE '%term%'` on an already small,
  per-tenant-filtered set is sufficient and matches existing query patterns in
  the codebase (no other repository in this project uses trigram search).

## Decision: Frontend debouncing and minimum query length

- **Decision**: `AddMemberForm` debounces input by 300ms and only issues a
  request once the trimmed query has ≥2 characters (FR-007), client-side guard
  in addition to the server simply returning results for whatever it's given.
- **Rationale**: Matches FR-007/FR-008 and SC-002 without adding server-side
  rate limiting infrastructure that doesn't otherwise exist in this codebase.
- **Alternatives considered**: Server-side minimum-length enforcement (400 on
  short queries) was considered but rejected as unnecessary — an empty/short
  query simply returning an empty or capped result set server-side is simpler
  and the UI never sends one due to the client guard.

## Decision: Replace vs. add alongside `InviteMemberForm`

- **Decision**: `AddMemberForm` replaces `InviteMemberForm` entirely in
  `SpaceMembersPanel`; the old component and its raw-user-ID input are deleted.
- **Rationale**: Confirmed in spec Assumptions — the raw-ID form is the thing
  this feature targets, and keeping both would be a confusing duplicate entry
  point for the same `POST /v1/spaces/{id}/members` action.
- **Alternatives considered**: Keep `InviteMemberForm` as an "advanced" fallback
  for entering a raw ID. Rejected — no requirement calls for it, and it
  reintroduces the exact UX gap (FR-001) this feature exists to close.
