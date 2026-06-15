# API Contract: User Registration

**Endpoint**: `POST /v1/auth/register`  
**Backend source**: `apps/api/tessera_api/routers/auth.py`  
**Used by**: `apps/web/lib/api.ts` → `authRegister()`

---

## Request

```
POST /v1/auth/register
Content-Type: application/json
Authorization: (none — public endpoint)
```

### Body

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `email` | string | yes | Must contain "@" and "." after "@"; stored lowercased |
| `password` | string | yes | Minimum 8 characters |
| `display_name` | string | yes | 1–100 characters |

```json
{
  "email": "user@example.com",
  "password": "s3cur3pass",
  "display_name": "Alice Smith"
}
```

---

## Responses

### 201 Created — success

```json
{
  "user": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "email": "user@example.com",
    "display_name": "Alice Smith",
    "is_admin": false,
    "created_at": "2026-06-15T10:00:00.000000"
  }
}
```

> **Frontend behaviour**: discard this response body; immediately call `authLogin(email, password)` to obtain JWT tokens, then update auth state and redirect.

### 409 Conflict — email already registered

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

> **Frontend behaviour**: show "This email is already registered. [Sign in instead?](/login)" and stop submitting.

### 422 Unprocessable Entity — validation failure (backend)

Should not occur in production if client-side validation (FR-003) is correct. If received, treat as generic error (FR-008).

### 5xx Server Error

> **Frontend behaviour**: show generic "Something went wrong. Please try again later." message (FR-008).

---

## Frontend API Function Signature

To be added to `apps/web/lib/api.ts`:

```typescript
export async function authRegister(
  displayName: string,
  email: string,
  password: string,
): Promise<void>
```

Returns `void` — the response body is intentionally discarded because the auto-login step handles obtaining tokens.
