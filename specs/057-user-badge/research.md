# Phase 0 Research: User Badge

## R1 — How does the display name reach the client?

**Decision**: Add a small read-only `GET /v1/auth/me` endpoint that returns the
caller's own identity (`id`, `email`, `display_name`, `is_admin`), and have the
`UserBadge` fetch it once per auth session. Email is rendered immediately from the
already-decoded access token; the display name and initials enrich when the fetch
resolves.

**Context established from the codebase**:
- The web `AuthProvider` decodes the JWT client-side into
  `AuthUser = { id, email, isAdmin }` (`apps/web/lib/auth.tsx`,
  `decodeJwtUser`). Email is available synchronously; **display name is not in
  the token**.
- `create_access_token` (`apps/api/.../auth/jwt_auth.py`) emits only
  `sub`, `email`, `is_admin`, `token_kind`, `company_id`. Display name is absent.
- `SqlUserRepository` already exposes `get_by_id` and `get_by_subject`
  (`apps/api/.../adapters/repositories/user.py`).
- Routers obtain the authenticated principal via the `CurrentUser` dependency,
  a dict carrying `sub` / `email` / `is_admin` (used e.g. in `companies.py`).

**Rationale**:
- Localized and additive: one new endpoint reading the caller's own row. It does
  not touch security-critical token-issuance code.
- Tenant-safe by construction: identity is derived from the verified token
  subject; no company-scoped query and no user-supplied ID.
- Matches the spec's "identity temporarily unavailable → neutral placeholder /
  omit until known" edge case, which anticipates asynchronous identity
  resolution.
- Reusable: a canonical "who am I" endpoint is broadly useful beyond the badge.

**Alternatives considered**:
- **Embed `display_name` in the JWT.** Rejected: `create_access_token` is called
  from **six** sites (login, refresh, switch-company, password-change, and two in
  `companies.py`); several (switch-company, password-change) lack `display_name`
  in scope and would need extra lookups. Threading a new claim through
  security-critical issuance code is disproportionately invasive for a display
  aid, and enlarges every token.
- **Email-only badge (no backend change).** Rejected: FR-002 makes showing the
  display name a MUST *when one is available*; email-only silently violates it
  whenever a name exists, and yields weaker initials (FR-007).
- **Derive name from the already-fetched company members list.** Rejected:
  couples identity to company context, is unavailable before a company is
  selected, and risks reading beyond the caller's own row.

## R2 — Deriving the visual marker (initials)

**Decision**: A pure `initials(name?, email)` helper. If a display name with ≥2
whitespace-separated words exists, use the first letter of the first and last
word; if a single-word name, use its first two letters; otherwise fall back to
the first two characters of the local-part of the email. Uppercase, max 2 chars.

**Rationale**: Deterministic, testable in isolation, and gracefully degrades to
email when no name is available (spec "Missing name" edge case). No I/O.

**Alternatives considered**: Server-computed initials — rejected as unnecessary
coupling; initials are pure presentation and belong in the web layer.

## R3 — Placement, truncation, and responsiveness

**Decision**: Render `<UserBadge/>` inside the existing `NavBar` in both the
desktop bar and the mobile menu, next to the current Account / Sign-out controls.
Use the initials in a small rounded avatar chip; show the email (and name when
present) as text that truncates with `truncate`/`max-w-*` and exposes the full
value via `title` (native tooltip). Gate rendering on
`status === "authenticated"` so it disappears on sign-out and never shows while
unauthenticated.

**Rationale**: `NavBar` is already the persistent primary navigation present on
every authenticated page (FR-003), already branches on auth status, and already
has a mobile menu (FR-009). Constitution UI system: `slate-*` neutrals,
`indigo-*` accent, no new color families — mirrors the existing `RoleBadge` /
`CompanyMenu` styling.

**Alternatives considered**: A separate floating badge outside `NavBar` —
rejected: duplicates layout concerns and risks inconsistent placement across
pages. An interactive account menu — out of scope per spec Assumptions.

## R4 — Reacting to account switches

**Decision**: The badge re-derives from `useAuth()` (`status`, `user.email`) and
re-fetches `/auth/me` when the authenticated user id changes. On sign-out
(`status` → `unauthenticated`) it renders nothing.

**Rationale**: `AuthProvider` already updates `user` on login/logout/refresh and
listens to cross-tab `storage` events, so the badge tracks the active account
without extra plumbing (FR-005, SC-003).

**Alternatives considered**: Polling — rejected as wasteful; auth state is
already push-updated by the provider.

## Outcome

All NEEDS CLARIFICATION resolved. No new dependencies, no schema changes, no
constitution violations.
