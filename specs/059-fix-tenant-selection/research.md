# Research: Company Selection at Sign-In (059)

**Date**: 2026-07-11 | **Plan**: [plan.md](./plan.md)

All unknowns from the Technical Context were resolved by direct code
inspection; no external research was required.

## R1. Root cause of the reported error

**Decision**: Treat as a pure web-app gap; the backend behaves as designed.

**Rationale** (verified in code):

- `POST /v1/auth/login` (`apps/api/tessera_api/routers/auth.py:146`) counts
  memberships: 1 → `token_kind: "full"` with auto `company_id`; >1 →
  `token_kind: "select"`, no company, and the response includes
  `"tenant_selection_required": true`; 0 → `token_kind: "onboarding"`.
- The web `LoginResponse` type (`apps/web/lib/types.ts`) omits
  `tenant_selection_required`; `login()` in `apps/web/lib/auth.tsx` stores the
  tokens and marks the session `authenticated` unconditionally.
- `decodeJwtUser` parses only `sub`/`email`/`is_admin` — `token_kind` and
  `company_id` (both present in the JWT payload, see
  `apps/api/tessera_api/auth/jwt_auth.py:42`) are discarded.
- Every data endpoint resolves company context through
  `_resolve_company_membership` (`apps/api/tessera_api/auth/oidc.py:87`),
  which rejects non-`full` tokens with **403** `credential_not_scoped` and
  the raw message the user reported.
- The web `request()` helper (`apps/web/lib/api.ts`) special-cases only 401;
  a 403 becomes an `ApiError` whose `message` is the server text, which pages
  render into their generic error slots — hence the raw string on screen.
- `OnboardingGuard` does not intercept: `/v1/onboarding/status` accepts any
  token kind (`CurrentUser`) and reports `completed: true` for anyone with a
  membership, so multi-company users land on broken pages, not onboarding.

**Alternatives considered**: (a) Backend auto-scoping to the first membership
— rejected: silently picking a company is wrong UX and contradicts the
designed `select` flow; (b) backend 401 instead of 403 to ride the existing
refresh/logout path — rejected: it would log users out instead of letting
them complete sign-in, and changes shared auth semantics.

## R2. Endpoint for listing companies with an unscoped credential

**Decision**: Reuse `GET /v1/companies/me` unchanged.

**Rationale**: It authenticates via `CurrentUser` (`require_user`), which
imposes no token-kind gate, so a `select` token works. It returns
`{ companies: [{ id, name, role }] }` sorted by name — exactly the data
FR-001 requires (name + role). The web already has a typed client for it
(`getMyCompanies()` in `apps/web/lib/companies.ts`, `CompanyEntry` type).

**Alternatives considered**: a new `/v1/auth/tenants` endpoint scoped to
select tokens — rejected: duplicates an existing contract for no gain and
would violate the "no backend changes" scope.

## R3. Credential exchange contract

**Decision**: Call `POST /v1/auth/select-tenant` with the select token as
Bearer and `{ company_id }` body; replace the stored token pair with the
response.

**Rationale**: The endpoint (`auth.py:321`) accepts select *or* full tokens
(`require_unscoped_or_full_token`), validates company activeness and caller
membership, and returns a standard token-pair payload
(`access_token`/`refresh_token`/`expires_in`) with `token_kind: "full"` and
the company embedded. Error codes are machine-readable:
`company_suspended`, `not_a_member` (403), `wrong_token_kind` (onboarding
tokens, 403), `invalid_token` (401). It writes the `auth.credential.issued`
audit record.

**Persistence across reloads/refresh (FR-007)**: `POST /v1/auth/refresh`
copies `company_id` and `token_kind` from the stored refresh-token row into
the new pair, so once exchanged, background renewal keeps the scope with no
user interaction. Verified at `auth.py:276-306`.

## R4. Where token-kind awareness lives in the web app

**Decision**: Decode `token_kind`/`company_id` in `decodeJwtUser`
(`lib/auth.tsx`) and expose them via the auth context; add
`selectTenant(companyId)` to `AuthProvider`.

**Rationale**: The JWT is already the single client-side source of session
truth and is re-decoded on every state update (login, refresh, restore) — so
kind-awareness survives reloads with zero extra storage (Constitution III:
nothing new persisted). `AuthProvider` owns the `localStorage` writes and the
refs `api.ts` reads, so the exchange must happen there to stay atomic with
`updateState`. JWT payloads are unsigned-readable by design; no verification
is needed client-side (the server re-verifies every request).

**Alternatives considered**: storing a `tenant_selection_pending` flag in
`localStorage` — rejected: second source of truth that can desync from the
actual token (e.g., token swapped in another tab); deriving from a
`/companies/me` probe on boot — rejected: extra round-trip and races.

## R5. Routing enforcement pattern (FR-004)

**Decision**: A new `TenantGuard` client component in `lib/auth-guard.tsx`,
mounted in `app/layout.tsx` next to `OnboardingGuard`, plus a central
`credential_not_scoped` interceptor in `api.ts`.

**Rationale**: The repo's established pattern for flow gating is a layout
guard (`OnboardingGuard`). TenantGuard covers navigation/bookmark/restore
entry; the `api.ts` interceptor covers any in-flight 403
`credential_not_scoped` that slips through (e.g., token exchanged in another
tab, race between guard and fetch), satisfying acceptance scenario US2-2 and
SC-002 globally rather than per-page. Exempt paths: `/login`, `/register`,
`/select-company`, `/forgot-password`, `/reset-password`. On `/select-company`
with a `full` token, redirect into the app (spec edge case). The interceptor
is wired as an optional `onTenantSelectionRequired` callback in `ApiConfig`
so `api.ts` stays free of Next.js router imports.

**Alternatives considered**: per-page checks — rejected: exactly the
scattered approach that produced the bug; Next.js middleware — rejected:
tokens live in `localStorage`, invisible to the server/middleware layer.

## R6. Login-page handoff

**Decision**: `login()` returns `{ tenantSelectionRequired: boolean }`
(derived from the response flag / decoded token kind); the login page routes
to `/select-company?redirect=<dest>` when true.

**Rationale**: Keeps the intended destination (`redirect` param) flowing
through the selection step (FR-002 "taken to their intended destination").
TenantGuard is the safety net if a caller ignores the return value, so the
two mechanisms are redundant by design, not conflicting.

## R7. Failure handling on the selection screen (FR-006, US3)

**Decision**: Map `ApiError.code` → copy on the page:
`company_suspended` → "This company's account is suspended…";
`not_a_member` → "You no longer have access to this company…"; both keep the
picker rendered and trigger a company-list re-fetch so the options stay
accurate. Session expiry (401 after failed refresh) already funnels to
logout → `/login` via the existing `api.ts`/AuthGuard machinery; the page
needs no special handling beyond its unauthenticated redirect. Sign-out
button reuses `logout()` (FR-008), which server-revokes the refresh token
and clears storage.

**Alternatives considered**: auto-selecting the next company on failure —
rejected: surprising, and the user may prefer to sign out.

## R8. Test environment baseline

Per the recorded baseline (memory: `project_test_env_baseline`): web tests
run under Vitest + Testing Library (jsdom) in `apps/web/tests/`; this feature
adds no Python code, so the pre-existing API-side failures/coverage-gate
issues are out of scope. Validation = new Vitest suites green + full
`apps/web` suite green.
