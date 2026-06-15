# Data Model: New User Registration

**Feature**: 006-user-registration | **Date**: 2026-06-15

## New Types (frontend — `apps/web/lib/types.ts`)

### `RegisterCredentials`

```typescript
export interface RegisterCredentials {
  displayName: string;  // 1–100 chars after trimming; maps to API field "display_name"
  email: string;        // well-formed email; lowercased before submission
  password: string;     // min 8 chars
}
```

### `PasswordStrength`

```typescript
export type PasswordStrength = "weak" | "medium" | "strong";
```

Used exclusively by the registration form's strength indicator. Not persisted or sent to the server.

---

## Modified API Types (frontend — `apps/web/lib/types.ts`)

No existing types are modified. `RegisterResponse` is returned by the backend but only used transiently in `api.ts`; the registration flow immediately calls `login()` to obtain tokens rather than storing the register response.

---

## Existing Types Reused

| Type | Source | Usage |
|------|--------|-------|
| `LoginCredentials` | `lib/types.ts` | Passed to `login()` after successful registration |
| `LoginResponse` | `lib/types.ts` | Returned by `authLogin()` during auto-login step |
| `AuthUser` | `lib/types.ts` | Decoded from JWT after auto-login |
| `AuthStatus` | `lib/types.ts` | Checked in `useEffect` to redirect authenticated users |

---

## Backend Contract (reference — no frontend changes)

The backend `POST /v1/auth/register` (defined in `apps/api/tessera_api/routers/auth.py`) expects:

```json
{
  "email": "string",          // validated: contains "@" and "." after "@"
  "password": "string",       // min_length: 8
  "display_name": "string"    // min_length: 1, max_length: 100
}
```

Returns `201 Created`:
```json
{
  "user": {
    "id": "uuid",
    "email": "string",
    "display_name": "string",
    "is_admin": false,
    "created_at": "ISO8601"
  }
}
```

Returns `409 Conflict` when email already registered:
```json
{
  "detail": {
    "error": {
      "code": "email_already_registered",
      "message": "Email already registered"
    }
  }
}
```

---

## Validation Rules Summary

| Field | Client-side rule | Error message |
|-------|-----------------|---------------|
| Display name | Non-empty after trim | "Display name is required" |
| Display name | ≤ 100 characters | "Display name must be 100 characters or fewer" |
| Email | Contains "@" and "." | "Enter a valid email address" |
| Password | ≥ 8 characters | "Password must be at least 8 characters" |
| (all) | Non-empty | "<Field> is required" |

---

## State Transitions (registration form)

```
idle
  → submitting    (user clicks "Create account", client validation passes)
    → success     (API returns 201; auto-login completes → redirect)
    → error:dup   (API returns 409 → show "Email already in use" message)
    → error:net   (API returns other error → show generic message)
    → idle        (user edits form after error)
```
