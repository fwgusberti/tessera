# Phase 0 Research: Add User on the Company User Management Page

All Technical Context items resolved from the existing codebase; no external
research required. Each decision below records what was chosen, why, and the
alternatives rejected.

## 1. How does an invited user get a role? (FR-004, FR-011)

- **Decision**: Add a `role` column to the `invitations` table (migration `0015`,
  `String(20)`, `NOT NULL`, server default `'member'`) and a `role: CompanyRole =
  CompanyRole.MEMBER` field on the `Invitation` domain model. The
  invitation-acceptance branch of `POST /companies/{id}/join` grants
  `invitation.role` instead of the currently hard-coded `CompanyRole.MEMBER`.
- **Rationale**: The invitation is the only durable record that survives between
  "admin invites" and "invitee accepts", so the chosen role must be persisted on
  it. There is no other place to carry the admin's role choice across the
  accept-later boundary.
- **Alternatives considered**:
  - *Always grant MEMBER on acceptance, change role afterwards* — rejected:
    violates FR-011 ("with the role that was assigned at invite time") and
    role-management is explicitly out of scope for this feature.
  - *Store the intended role in a side table* — rejected: needless; the
    invitation row is the natural owner of the datum. Backward compatible because
    existing rows and the legacy bulk `POST /invitations` default to `member`.

## 2. Two endpoints or one for adding? (US1, US2)

- **Decision**: Two purpose-specific endpoints plus one search endpoint, all on
  the existing `companies` router and all gated by `CompanyAdminContext`:
  - `POST /v1/companies/members` — direct add of an existing user → 201 + the new member row.
  - `POST /v1/companies/invitations` — invite by email + role → invitation outcome.
  - `GET  /v1/companies/addable-users?q=` — type-ahead search of registered users not in the company.
- **Rationale**: The two add methods have fundamentally different results (an
  immediate membership row vs. a pending invitation) and different failure modes
  (no-such-user vs. malformed-email / send-failed). Separate endpoints keep each
  response shape and status code clean and match the read/write split already on
  the router.
- **Alternatives considered**:
  - *Single `POST /companies/members` with a `mode` discriminator* — rejected:
    conflates two response shapes and mixes 201-created semantics with
    invitation-sent semantics.
  - *Reuse the existing `POST /invitations` (bulk) endpoint* — rejected: it
    resolves the company from `admin_memberships[0]` (not the active-company
    context), which would violate FR-010 for a multi-company admin, and it has no
    role parameter. The new invite endpoint uses `CompanyAdminContext` and reuses
    only the shared `send_invitation_email` helper and the invitation repo.

## 3. Finding an already-registered user to direct-add (FR-005)

- **Decision**: Add `CompanyRepository.search_addable_users(company_id, query,
  limit=20)` — a case-insensitive `ILIKE` match on `users.display_name` /
  `users.email`, **excluding** users already in `company_memberships` for
  `company_id`, ordered by display name, limited. It returns only identity fields
  (`user_id`, `display_name`, `email`). The endpoint enforces a minimum query
  length (≥ 2 characters).
- **Rationale**: Mirrors the proven shape of `search_members_for_space` (same
  join + `ILIKE` + `notin_` exclusion), but inverts the exclusion (exclude
  *current company members* instead of *current space members*) and searches the
  whole user table rather than only the company's members. The `users` table is a
  global identity store, not tenant-owned data, so a directory search is the
  correct primitive; scoping the exclusion and the eventual write to the context
  `company_id` preserves tenant isolation.
- **Alternatives considered**:
  - *Email-only exact match (type the full address)* — rejected: FR-005 and US2
    scenario 3 require identifying the person by name **and/or** email before
    adding, i.e. a search with human-readable results.
  - *Return full user records* — rejected: exposes more than needed; identity
    fields only, and never the candidate's other-company memberships.

## 4. Preventing duplicates and races (FR-007, FR-008, edge cases)

- **Decision**:
  - *Already a member*: both paths call `get_membership(user_id, company_id)`
    first and return a clean "already a member" outcome. The existing
    `uq_company_membership (user_id, company_id)` constraint is the backstop —
    `add_membership` is wrapped so a concurrent-insert `IntegrityError` maps to
    the same "already a member" outcome rather than a 500.
  - *Already invited*: the invite path checks `get_pending_for_email` for the
    company first; migration `0015` also adds a **partial unique index** on
    `(company_id, lower(email)) WHERE status = 'pending'`, so two near-simultaneous
    invites collapse to exactly one pending invitation (the loser's
    `IntegrityError` maps to "already invited").
- **Rationale**: Check-then-write matches the existing `POST /invitations`
  behavior and gives friendly messages on the common path; the DB constraints make
  the concurrent edge cases (spec "Concurrent adds") correct without app-level
  locking.
- **Alternatives considered**: *App-level advisory locks* — rejected as
  over-engineering for admin-triggered, low-frequency actions when unique
  constraints already express the invariant.

## 5. How the roster reflects an add (FR-013)

- **Decision**: On a successful **direct add**, the endpoint returns the new
  member row and the page appends it to the existing 053 roster table in place (no
  full reload). On a successful **invite**, the page shows an unambiguous
  "invitation sent" confirmation; the roster continues to list *members* only.
- **Rationale**: The 053 roster is a members-only table, and managing invitations
  (list/resend/revoke) is explicitly out of scope. Representing the immediate
  member in the roster and the pending invite as a confirmation is the minimal
  behavior that satisfies FR-013's "reflect the result ... consistent with how the
  company roster is presented" without inventing invitation-management UI.
- **Alternatives considered**: *Add a "pending invitations" section to the
  roster* — deferred: it implies revoke/resend affordances that are out of scope
  for this feature.

## 6. Authorization and tenant scoping (US4)

- **Decision**: Reuse `CompanyAdminContext` verbatim for all three endpoints;
  take `company_id` only from the resolved context.
- **Rationale**: Identical to 053. The dependency already returns 401
  (unauthenticated), 403 (non-admin / no active company / revoked membership), and
  guarantees `company_id` comes from the JWT/session, never client input —
  satisfying US4, FR-009, FR-010, SC-003, SC-004 structurally.
- **Alternatives considered**: *Per-endpoint manual `_require_company_admin` on a
  path `company_id`* — rejected: that pattern (used by the older join-request
  endpoints) takes the company from the URL, which is exactly the client-supplied
  source Principle VI forbids for new work.
