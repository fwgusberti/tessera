# Implementation Plan: Company Selection at Sign-In

**Branch**: `059-fix-tenant-selection` | **Date**: 2026-07-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/059-fix-tenant-selection/spec.md`

## Summary

A user with two or more company memberships receives a `token_kind: "select"`
credential at login (`POST /v1/auth/login` even sets
`tenant_selection_required: true`), but the web app ignores it: it stores the
tokens, treats the session as complete, and routes the user into the app. The
OnboardingGuard lets them through (`/v1/onboarding/status` reports
`completed: true` because membership is authoritative), and then every data
endpoint rejects the select token with 403 `credential_not_scoped`, whose raw
message — *"Credential is not scoped to a tenant; call /auth/select-tenant
first"* — pages render verbatim. The user is locked out.

**Technical approach — web-only fix** (confirmed: the backend already provides
everything; see research.md):

1. **Token-kind awareness in the auth layer** (`lib/auth.tsx`): decode
   `token_kind` (and `company_id`) from the JWT payload alongside the existing
   claims; expose it on the auth context and add a `selectTenant(companyId)`
   action that calls `POST /v1/auth/select-tenant` with the select token and
   swaps the stored credential pair for the returned full-scoped pair.
2. **New route `/select-company`** (`app/select-company/page.tsx`): lists the
   user's companies (name + role) via existing `GET /v1/companies/me` (works
   with a select token), lets them pick one or sign out, and maps the
   `company_suspended` / `not_a_member` error codes to human-readable messages
   while keeping the remaining companies selectable.
3. **TenantGuard** (`lib/auth-guard.tsx`, mounted in `app/layout.tsx`): any
   authenticated session whose token kind is `select` is redirected from
   protected pages to `/select-company?redirect=<intended path>`; a scoped
   session that opens `/select-company` is sent into the app.
4. **Global interception of `credential_not_scoped`** (`lib/api.ts`): a 403
   with that error code triggers a redirect to `/select-company` (new
   `onTenantSelectionRequired` callback wired by `AuthProvider`) and surfaces a
   friendly message — the raw backend text is never rendered (FR-005).
5. **Login flow** (`app/login/page.tsx`): when the login response carries
   `tenant_selection_required`, route to `/select-company` (preserving the
   `redirect` param) instead of the destination page.

No backend changes; single-company (`full`) and no-company (`onboarding`)
login paths are untouched (FR-003).

## Technical Context

**Language/Version**: TypeScript 5, Next.js 15 (App Router), React 19 —
`apps/web` only. No Python changes.

**Primary Dependencies**: Next.js, React, Tailwind CSS. No new dependencies.

**Storage**: N/A (no schema changes; no new server-side state). Client keeps
using the existing `localStorage` token slots (`tessera_access_token`,
`tessera_refresh_token`, `tessera_expires_at`) — no new data is persisted
client-side.

**Testing**: Vitest + Testing Library (jsdom), existing setup in
`apps/web/tests/`.

**Target Platform**: Modern browsers, desktop and mobile viewports.

**Project Type**: Web application — monorepo; this feature touches `apps/web`
exclusively.

**Performance Goals**: Selection step adds exactly one round-trip
(`GET /v1/companies/me`) plus one exchange (`POST /v1/auth/select-tenant`);
company list renders in a single fetch (SC-003: completable in < 30 s).

**Constraints**: Raw `credential_not_scoped` message must never reach the user
(FR-005 / SC-002). Selected scope must survive reloads and background refresh
(FR-007) — guaranteed because `/auth/refresh` preserves `token_kind` +
`company_id` from the stored refresh token. Guard must not redirect-loop
(`/select-company` exempt from itself; scoped users bounced off it).

**Scale/Scope**: 1 new page, 1 new guard, ~4 modified web modules
(`auth.tsx`, `api.ts`, `auth-guard.tsx`, `login/page.tsx`, `types.ts`,
`layout.tsx`), ~5 new/extended Vitest suites. Zero API/core changes, zero
migrations.

## Constitution Check

*GATE: evaluated against Constitution v1.4.0 — PASS (initial and post-design).*

**I. Domain-Driven Architecture — PASS.** No domain logic added or changed;
this is presentation/session-flow work in the web adapter. The
credential-exchange business rules stay in the API/core where they already
live.

**II. Separation of Concerns — PASS.** The web app consumes existing
transport contracts (`tenant_selection_required` flag, error `code` values);
no product definition changes.

**III. Data Locality & Consent — PASS.** No new client-side persistence: the
exchanged tokens overwrite the same three `localStorage` keys already
documented and in use for the session credential (feature 040-era auth). The
company choice itself is not stored separately — it is embedded in the
credential, exactly like a single-company login.

**IV. TDD (non-negotiable) — PASS.** All new behavior written test-first in
Vitest: select-company page (list/pick/error/sign-out), TenantGuard redirects,
`selectTenant` token swap, `credential_not_scoped` interception, login
routing. The 85% statement-coverage rule targets Python modules — no Python
module changes here; web suites follow the repo's existing Vitest coverage
setup.

**V. Quality Gates — PASS.** No Python changes (Ruff/Black untouched);
web code follows the existing ESLint/TS strictness.

**VI. Tenant Data Isolation (non-negotiable) — PASS.** See dedicated section
below.

**Audit logging — PASS.** The only state-changing action (credential
exchange) is the existing `POST /v1/auth/select-tenant`, which already writes
an `auth.credential.issued` audit record; sign-out reuses `/v1/auth/logout`
(`auth.logout`). No new state-changing paths are introduced.

### Tenant Isolation (required section)

**Tables accessed**: none directly — this feature adds no backend code. The
web flow consumes three existing endpoints:

- `GET /v1/companies/me` — already scoped to the authenticated user's own
  memberships (`list_memberships_for_user(user_id)` from the token `sub`).
- `POST /v1/auth/select-tenant` — the tenant-scoping mechanism itself: it
  validates company activeness and the caller's membership
  (`get_membership(user_id, company_id)`) before issuing a company-scoped
  credential, and rejects onboarding tokens
  (`require_unscoped_or_full_token`). 403 `not_a_member` /
  `company_suspended` on violation.
- `POST /v1/auth/refresh` — preserves the `company_id`/`token_kind` recorded
  server-side on the refresh-token row; the client cannot escalate scope
  through refresh.

**Scoping guarantees**: the company the user lands in is established
exclusively by the server-issued credential — the client never sends a
`company_id` on data requests, so a tampered selection cannot widen access
beyond memberships the server verifies.

**Isolation tests**: server-side coverage already exists for select-tenant
membership validation (auth integration tests + `test_tenant_isolation.py`);
this feature adds web tests asserting (a) a failed selection
(`not_a_member`, `company_suspended`) shows a friendly error and does NOT
store tokens, and (b) the raw `credential_not_scoped` text is never rendered.

## Project Structure

### Documentation (this feature)

```text
specs/059-fix-tenant-selection/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── company-selection.md   # Consumed API contracts + frontend route contract
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
apps/web/
├── app/
│   ├── layout.tsx                    # MODIFIED: mount TenantGuard inside AuthProvider
│   ├── login/page.tsx                # MODIFIED: route to /select-company when selection required
│   └── select-company/page.tsx       # NEW: company selection step
├── lib/
│   ├── types.ts                      # MODIFIED: LoginResponse.tenant_selection_required,
│   │                                 #           AuthUser.tokenKind/companyId, TokenKind type
│   ├── auth.tsx                      # MODIFIED: decode token_kind; selectTenant(); login()
│   │                                 #           returns selection-required signal
│   ├── api.ts                        # MODIFIED: authSelectTenant(); onTenantSelectionRequired
│   │                                 #           callback on 403 credential_not_scoped
│   └── auth-guard.tsx                # MODIFIED: new TenantGuard (+ exempt /select-company
│                                     #           in OnboardingGuard)
└── tests/
    ├── select-company.test.tsx       # NEW: list, pick, suspended/revoked errors, sign-out
    ├── tenant-guard.test.tsx         # NEW: select-token redirects, scoped pass-through
    ├── auth.test.tsx                 # MODIFIED: selectTenant token swap, tokenKind decode
    ├── api.test.tsx                  # MODIFIED: credential_not_scoped interception
    └── login.test.tsx                # MODIFIED: multi-company login → /select-company
```

**Structure Decision**: Existing monorepo layout; all changes confined to
`apps/web`. No new packages, no migrations, no backend edits.

## Design Decisions (summary — details in research.md)

1. **Web-only fix.** Verified in code: login already returns
   `tenant_selection_required`, `GET /v1/companies/me` accepts any token kind,
   `POST /v1/auth/select-tenant` exchanges select→full, and refresh preserves
   scope. The spec's core assumption holds; no backend work.
2. **Token kind decoded from the JWT**, not stored separately — the access
   token payload already carries `token_kind`, and `decodeJwtUser` already
   parses the payload. One source of truth; survives reload for free.
3. **Dedicated `/select-company` route + TenantGuard**, mirroring the
   established OnboardingGuard pattern, rather than a modal — it must be
   reachable by redirect from any protected page, bookmarks, and API-error
   interception (FR-004).
4. **`selectTenant` lives in `AuthProvider`** because it must atomically swap
   the token pair in `localStorage` + context refs, which only `auth.tsx`
   owns. It uses a raw (non-intercepted) API call like the other auth
   endpoints.
5. **403 `credential_not_scoped` handled centrally in `api.ts`** via a new
   optional `onTenantSelectionRequired` config callback — pages keep their
   generic error handling and never see the raw message; only `AuthProvider`
   wires the callback (SC-002 across all screens, including future ones).
6. **Selection failures re-fetch the company list** (FR-006 / edge cases):
   on `not_a_member` / `company_suspended` the page shows the mapped message
   and reloads `GET /v1/companies/me` so the remaining companies stay
   accurate; session expiry falls through the existing 401→refresh→logout
   path to `/login`.

## Complexity Tracking

No constitution violations — table intentionally empty.
