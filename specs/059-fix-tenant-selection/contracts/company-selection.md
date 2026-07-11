# Contracts: Company Selection at Sign-In (059)

**Date**: 2026-07-11 | **Plan**: [../plan.md](../plan.md)

This feature adds **no backend endpoints**. Section A pins down the three
existing API contracts the web app newly consumes (source of truth:
`apps/api/tessera_api/routers/auth.py`, `routers/companies.py`,
`auth/oidc.py`). Section B defines the frontend contracts introduced.

## A. Consumed API contracts (existing — must not change)

### A1. `POST /v1/auth/login`

Request: `{ "email": string, "password": string }` — unchanged.

Response `200` (multi-membership case):

```json
{
  "access_token": "<jwt with token_kind: \"select\", no company_id>",
  "refresh_token": "<opaque>",
  "token_type": "bearer",
  "expires_in": 1800,
  "tenant_selection_required": true
}
```

`tenant_selection_required` is present only when the user has ≥ 2 company
memberships. Single-membership logins return a `full` token with `company_id`;
zero-membership logins return an `onboarding` token. Neither carries the flag.

### A2. `GET /v1/companies/me`

Auth: Bearer token of **any** kind (`select` included).

Response `200`:

```json
{ "companies": [ { "id": "<uuid>", "name": "Acme", "role": "admin" } ] }
```

Sorted by name. Roles: `"admin" | "member"`. Companies whose record no longer
exists are omitted.

### A3. `POST /v1/auth/select-tenant`

Auth: Bearer token of kind `select` or `full` (onboarding rejected).

Request: `{ "company_id": "<uuid>" }`

Response `200`: standard token pair, now company-scoped:

```json
{
  "access_token": "<jwt with token_kind: \"full\", company_id, is_admin per membership role>",
  "refresh_token": "<opaque, scope recorded server-side>",
  "token_type": "bearer",
  "expires_in": 1800
}
```

Errors (all bodies `{ "error": { "code": ..., "message": ... } }`):

| Status | `code` | Client behavior (this feature) |
|---|---|---|
| 403 | `company_suspended` | Friendly "company unavailable" copy; keep picker; re-fetch list |
| 403 | `not_a_member` | Friendly "no longer have access" copy; keep picker; re-fetch list |
| 403 | `wrong_token_kind` | Onboarding token — route to `/onboarding` (existing flow) |
| 401 | `invalid_token` | Existing session-expired path → `/login` |

Side effect: writes `auth.credential.issued` audit record.

### A4. Scope-preservation guarantees relied upon

- `POST /v1/auth/refresh` copies `company_id` + `token_kind` from the stored
  refresh-token row into the new pair (FR-007).
- Data endpoints reject non-`full` tokens with **403**
  `{ code: "credential_not_scoped" }` — the trigger for the client-side
  interceptor (never displayed).

## B. Frontend contracts (new)

### B1. Route `/select-company`

| Aspect | Contract |
|---|---|
| Query params | `redirect` — same sanitization as `/login` (must start with `/`, not `//`) |
| Unauthenticated session | redirect to `/login` |
| `tokenKind === "full"` | redirect to sanitized `redirect` or `/` |
| `tokenKind === "onboarding"` | redirect to `/onboarding` |
| `tokenKind === "select"` | render picker: one action per company showing name + role; a Sign out action |
| On pick success | navigate to sanitized `redirect` or `/` |
| On pick failure | mapped message (see A3), picker stays interactive, list re-fetched |
| On sign out | `logout()` (server revocation + storage clear) → `/login` |

### B2. `AuthContextValue` additions (`lib/auth.tsx`)

```ts
interface AuthContextValue {
  // existing: status, user, accessToken, login, logout, refreshIfNeeded
  user: AuthUser | null;          // AuthUser gains tokenKind, companyId
  login(credentials: LoginCredentials): Promise<{ tenantSelectionRequired: boolean }>;
  selectTenant(companyId: string): Promise<void>; // NEW — throws ApiError-compatible Error on failure
}
```

`selectTenant` MUST: call A3 with the current access token (raw fetch, no
auth-injection retry), persist the returned pair via the existing
`writeStorage`/`updateState` path, and leave existing state untouched on
failure.

### B3. `ApiConfig` addition (`lib/api.ts`)

```ts
interface ApiConfig {
  // existing: getAccessToken, refreshIfNeeded, forceRefresh, onUnauthorized
  onTenantSelectionRequired?(): void; // NEW
}
```

`request()` MUST invoke it on any `403` response whose error `code` is
`credential_not_scoped`, then throw a friendly `ApiError` (message e.g.
"Please choose a company to continue.") — the server's raw message MUST NOT
propagate. Wired by `AuthProvider` to navigate to `/select-company`.

### B4. `TenantGuard` (`lib/auth-guard.tsx`, mounted in `app/layout.tsx`)

| Condition | Behavior |
|---|---|
| `status !== "authenticated"` | pass through (AuthGuard/pages handle) |
| `tokenKind === "select"` and path not exempt | `router.replace("/select-company?redirect=" + encodeURIComponent(pathname))`; render nothing |
| `tokenKind !== "select"` | pass through |

Exempt paths: `/login`, `/register`, `/select-company`, `/forgot-password`,
`/reset-password`. (`/onboarding` is not exempt: an onboarding token is not
`select`-kind and passes through to the existing OnboardingGuard.)
