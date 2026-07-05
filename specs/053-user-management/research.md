# Phase 0 Research: Company User Management Page

No open `NEEDS CLARIFICATION` items remained after reading the spec; the feature is
a read-only roster view over existing multi-tenant data. Research therefore focused
on reusing established patterns rather than choosing new technology.

## Decision 1: Where the admin gate and company scoping live

- **Decision**: Gate the endpoint with the existing `CompanyAdminContext`
  (`require_company_admin`) dependency and derive `company_id` from it.
- **Rationale**: `require_company_admin` already resolves the active company from a
  full-scoped JWT claim (or session `active_company_id`), verifies the caller's
  live `company_memberships` row, and requires `CompanyRole.ADMIN` — returning 403
  otherwise and 401 when unauthenticated. This satisfies FR-005 and Principle VI
  structurally: the tenant boundary is established at the request edge and the
  `company_id` is never accepted from client input.
- **Alternatives considered**:
  - *Path param `/companies/{company_id}/members` + `_require_company_admin`* (as
    the join-request endpoints do): works, but accepts a client-supplied
    `company_id` that must then be re-validated. Deriving it from the context is
    strictly safer and needs no path parameter for a "my active company" view.
  - *Per-space membership reuse (`members` router)*: rejected — that router models
    **space** roles (viewer/editor/admin), not the **company** role the spec asks
    for.

## Decision 2: No new domain service; router → repository directly

- **Decision**: Add `CompanyRepository.list_members()` and call it directly from the
  router after the admin gate, with no new `Service` class.
- **Rationale**: The feature carries no business rule beyond the boundary-level admin
  gate (it is a pure read). This is exactly how `list_join_requests` is already
  built (router → `_require_company_admin` → `jr_repo.list_pending_for_company`).
  Introducing a service would add a layer with no logic to hold.
- **Alternatives considered**: A `CompanyMemberQueryService` — rejected as
  ceremony; there is no invariant or orchestration to encapsulate.

## Decision 3: Query shape

- **Decision**: A single `SELECT` joining `company_memberships` to `users` filtered
  by `company_id`, ordered by `display_name`, mapped to a `CompanyMemberListing`
  value object per row.
- **Rationale**: Identical in shape to the proven `search_members_for_space` join in
  the same repository, minus the search/exclusion predicates and plus the role
  column. Roster size is small at current scale, so no pagination is needed (the
  spec defers very-large-list handling).
- **Alternatives considered**: Two queries (memberships, then N user lookups) — the
  pattern used by `list_join_requests`. Rejected here in favor of a single join to
  avoid an N+1 for a page whose entire purpose is the full list; the join is already
  an established pattern in this repository.

## Decision 4: Frontend surface

- **Decision**: A dedicated `/users` App Router page wrapped in `AuthGuard`, a small
  `CompanyRoleBadge` (admin=indigo, member=slate) component, a `getCompanyMembers()`
  helper in `lib/companies.ts`, and a "Users" link in `NavBar`.
- **Rationale**: Mirrors the `SpaceMembersPanel` table layout and the existing
  `RoleBadge` styling conventions, and conforms to the constitution's UI design
  system (slate neutrals, indigo-600 accent). The existing `RoleBadge` only knows
  space roles (viewer/editor/admin), so a company-role badge is a clean, small
  addition rather than an overload.
- **Alternatives considered**: Folding the roster into the existing `/admin` page —
  rejected because the spec asks for a *dedicated* user management page (FR-001) and
  `/admin` is already dense with space/permission/connector tooling.
- **Open UX note (deferred, non-blocking)**: The "Users" nav link is shown to all
  authenticated users; non-admins who click it get a clean access-denied state from
  the 403 (no roster rendered). Conditionally hiding the link for non-admins would
  require NavBar to know the active company role and is out of scope for this
  read-only first version.
