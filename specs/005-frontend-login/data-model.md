# Data Model: Frontend Login

**Feature**: 005-frontend-login | **Date**: 2026-06-15

This document covers client-side state and storage — there are no new database entities. All persistent data lives in the existing backend (Users, RefreshTokens tables already created in the JWT auth feature).

---

## Client-Side State: AuthState

Held in React Context (`AuthContext`) and derived from `localStorage`.

| Field | Type | Description |
|-------|------|-------------|
| `user` | `AuthUser \| null` | Currently authenticated user; `null` when logged out |
| `accessToken` | `string \| null` | JWT access token for `Authorization` header |
| `refreshToken` | `string \| null` | Opaque refresh token; rotated on each use |
| `expiresAt` | `number \| null` | Unix timestamp (ms) when the access token expires |
| `status` | `"loading" \| "authenticated" \| "unauthenticated"` | Drives `AuthGuard` render decisions; `"loading"` during initial hydration from `localStorage` |

### AuthUser (decoded from access token payload)

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | UUID of the user (`sub` claim in JWT) |
| `email` | `string` | User's email address (`email` claim in JWT) |
| `isAdmin` | `boolean` | Admin flag (`is_admin` claim in JWT) |

---

## localStorage Keys

| Key | Format | Lifecycle |
|-----|--------|-----------|
| `tessera_access_token` | JWT string | Written on login/refresh; removed on logout |
| `tessera_refresh_token` | Opaque string | Written on login/refresh; removed on logout |
| `tessera_expires_at` | ISO 8601 string (stringified number: ms since epoch) | Written on login/refresh; removed on logout |

**Key prefix**: `tessera_` to avoid collisions with other apps on the same origin during development.

---

## LoginCredentials (form input)

| Field | Type | Validation |
|-------|------|------------|
| `email` | `string` | Required; must contain `@` (client-side, matches FR-003) |
| `password` | `string` | Required; non-empty (client-side, matches FR-003) |

---

## API Response Shapes (from backend)

### POST /v1/auth/login → LoginResponse

| Field | Type | Notes |
|-------|------|-------|
| `access_token` | `string` | JWT; signed with HS256; claims: `sub`, `email`, `is_admin`, `exp` |
| `refresh_token` | `string` | Opaque secure random string |
| `token_type` | `"bearer"` | Constant |
| `expires_in` | `number` | Seconds until access token expires |

### POST /v1/auth/refresh → RefreshResponse

Same shape as `LoginResponse`.

### POST /v1/auth/logout → 204 No Content

No response body.

---

## State Transitions

```
               ┌──────────────────────────────────────────┐
               │                                          │
    ┌──────────▼──────────┐   hydrate     ┌──────────────────────────┐
    │      loading         │ ─────────────► authenticated             │
    │  (initial mount)     │               │ user, tokens in state    │
    └──────────────────────┘   hydrate     └─────────────┬────────────┘
               │               (no tokens) ──────────────┐│
               └──────────────────────────────────────────┼┘
                                                          │
                          ┌───────────────────────────────▼───────────────┐
                          │            unauthenticated                     │
                          │  user=null, accessToken=null                   │
                          └────────────────────────────────────────────────┘
                                    ▲                   │
                                    │ logout / 401      │ login success
                                    │ refresh fails     │
                                    └───────────────────┘
```

Transitions:
- `loading → authenticated`: `localStorage` contains valid tokens on mount
- `loading → unauthenticated`: `localStorage` is empty or tokens are missing on mount
- `authenticated → unauthenticated`: explicit logout, or refresh token is invalid/expired
- `unauthenticated → authenticated`: successful login
