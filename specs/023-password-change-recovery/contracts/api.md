# API Contracts: Password Change and Recovery Flow

All endpoints are prefixed with `/v1` and registered on the existing `auth` router.

---

## POST /v1/auth/change-password

Change the authenticated user's password.

**Auth**: Bearer JWT access token (required)

### Request body

```json
{
  "current_password": "string",
  "new_password": "string (min 8 chars, strength-checked)",
  "confirm_new_password": "string (must equal new_password)",
  "refresh_token": "string (current session's opaque refresh token)"
}
```

### Responses

| Status | Condition | Body |
|--------|-----------|------|
| 200 OK | Success | `{access_token, refresh_token, token_type, expires_in}` |
| 400 Bad Request | `new_password !== confirm_new_password` | `{"error": {"code": "password_mismatch", "message": "…"}}` |
| 400 Bad Request | `new_password` fails strength check | `{"error": {"code": "password_too_weak", "message": "…"}}` |
| 401 Unauthorized | Missing or invalid access token | `{"error": {"code": "unauthorized", "message": "…"}}` |
| 401 Unauthorized | `current_password` incorrect | `{"error": {"code": "invalid_credentials", "message": "…"}}` |

### Side effects

1. `users.password_hash` updated for the authenticated user
2. All refresh tokens for the user are revoked **except** `refresh_token` in body — that one is rotated
3. New access token + refresh token pair returned (client must store the new pair)
4. Audit record: `auth.password.change`

---

## POST /v1/auth/forgot-password

Request a password reset email. Always returns HTTP 200 regardless of whether the email is registered.

**Auth**: None (public endpoint)

### Request body

```json
{
  "email": "string"
}
```

### Responses

| Status | Condition | Body |
|--------|-----------|------|
| 200 OK | Always | `{"message": "If that email is registered, you will receive a reset link shortly."}` |

### Side effects (only when email is registered AND rate limit not exceeded)

1. All prior unconsumed `password_reset_tokens` for the user are marked consumed
2. A new `PasswordResetToken` is inserted (expires in 60 minutes)
3. Reset email sent to the address with `{frontend_url}/reset-password?token={raw_token}`
4. Audit record: `auth.password.reset_requested`

**When rate limit exceeded**: returns 200 with same body; no email sent; no token created; no audit record for the blocked request.

**When email is not registered**: returns 200 with same body; dummy bcrypt call for timing equalisation; audit record with nil UUID and `{"found": false}`.

---

## POST /v1/auth/reset-password

Consume a reset token and set a new password.

**Auth**: None (public endpoint)

### Request body

```json
{
  "token": "string (raw opaque token from email link)",
  "new_password": "string (min 8 chars, strength-checked)",
  "confirm_new_password": "string (must equal new_password)"
}
```

### Responses

| Status | Condition | Body |
|--------|-----------|------|
| 204 No Content | Success | (empty) |
| 400 Bad Request | `new_password !== confirm_new_password` | `{"error": {"code": "password_mismatch", "message": "…"}}` |
| 400 Bad Request | `new_password` fails strength check | `{"error": {"code": "password_too_weak", "message": "…"}}` |
| 400 Bad Request | Token expired, consumed, or not found | `{"error": {"code": "invalid_or_expired_token", "message": "…"}}` |

**Security**: `invalid_or_expired_token` is used for expired, consumed, AND not-found tokens — no distinction exposed to the client.

### Side effects (on success)

1. `password_reset_tokens.consumed_at` set to `now()` for the submitted token
2. `users.password_hash` updated
3. All refresh tokens for the user are revoked (full session invalidation)
4. Audit record: `auth.password.reset_completed`

---

## New `EmailPort` method

Added to `packages/core/tessera_core/ports/providers.py`:

```python
@abstractmethod
async def send_password_reset(
    self,
    *,
    to: str,
    reset_url: str,
    expires_in_minutes: int,
) -> None:
    """Send password reset link email."""
```
