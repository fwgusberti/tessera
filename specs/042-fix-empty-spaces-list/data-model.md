# Phase 1 Data Model: Fix Empty Spaces List

No new tables, columns, or domain entities. This feature ensures existing
`SpaceMembership` records are created at the right time and backfilled where
missing.

## Entities touched (all pre-existing)

- **Space** (`spaces`): unchanged. Read (`id`, `company_id`) to drive both the
  creation-time grant and the backfill join; never written beyond its
  existing `create()` path.
- **SpaceMembership** (`space_memberships`): the entity being correctly
  populated. `role=ADMIN` for every row this feature creates, whether at
  space-creation time or via the backfill.
- **CompanyMembership** (`company_memberships`): read-only source of "who is
  an admin of this space's company" for the backfill join.

## Behavior change 1: `POST /v1/spaces` (creation-time grant)

| Step | Before | After |
|---|---|---|
| 1 | `Space` row created | `Space` row created (unchanged) |
| 2 | *(nothing)* | `SpaceMembership(space_id=<new space>, user_id=<creator>, role=ADMIN)` created in the same request |
| 3 | Response: `{"space": {...}}` | Response: `{"space": {...}}` (unchanged shape — the new membership is not echoed in the response body; the caller observes it via `GET /v1/spaces` or `GET /v1/spaces/{id}/members`) |

**Validation rule**: the membership's `user_id` MUST be the authenticated
caller (`CompanyContext`'s `user_info["sub"]`), the same identity already
used to authorize the request — no new input is accepted for this.

## Behavior change 2: One-time backfill (migration `0013`)

For every `Space` row where `space_memberships` currently has **zero** rows
with that `space_id`:

- Insert one `SpaceMembership(role=ADMIN)` row for each `CompanyMembership`
  row with `role='admin'` and matching `company_id` on that space's company.
- Idempotent: a second run inserts nothing new (guarded by `ON CONFLICT
  (space_id, user_id) DO NOTHING`, the same unique constraint
  `uq_space_membership` already enforced on the table).
- Spaces that already have at least one membership row (legitimate,
  pre-existing access) are untouched — the `WHERE NOT EXISTS (...)` guard is
  per-space, not per-user, so it never adds a second admin row next to an
  existing membership of any role.

**Edge case handling** (per spec FR-006): if a space's company has zero
`company_memberships` rows with `role='admin'` (should not occur — every
company requires an `admin_user_id` at creation, and migration `0010`
already guarantees that owner has an admin membership) the backfill simply
inserts zero rows for that space rather than erroring; the migration as a
whole still completes for every other space.
