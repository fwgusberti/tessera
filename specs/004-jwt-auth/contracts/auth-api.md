# API Contracts: Authentication

**Feature**: 004-jwt-auth  
**Base URL**: `/v1/auth`  
**Date**: 2026-06-15

All request and response bodies are `application/json`. Error responses follow the project convention: `{"error": {"code": "...", "message": "..."}}`.

---

## POST /v1/auth/register

Create a new local-credential user.

### Request

```json
{
  "email": "user@example.com",
  "password": "S3cur3P@ssword",
  "display_name": "Alice"
}
```

| Field | Type | Constraints |
|---|---|---|
| `email` | string | valid email, unique |
| `password` | string | min 8 characters |
| `display_name` | string | 1–100 characters |

### Response `201 Created`

```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "display_name": "Alice",
    "is_admin": false,
    "created_at": "2026-06-15T10:00:00Z"
  }
}
```

### Error Responses

| Status | Code | Condition |
|---|---|---|
| 409 | `email_already_registered` | Email already exists |
| 422 | `validation_error` | Invalid email or password too short |

---

## POST /v1/auth/login

Authenticate with email and password; receive JWT tokens.

### Request

```json
{
  "email": "user@example.com",
  "password": "S3cur3P@ssword"
}
```

### Response `200 OK`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "dGhpcyBpcyBhIHJhbmRvbSByZWZyZXNoIHRva2Vu...",
  "token_type": "bearer",
  "expires_in": 900
}
```

| Field | Type | Notes |
|---|---|---|
| `access_token` | string | HS256-signed JWT; expires in `expires_in` seconds |
| `refresh_token` | string | opaque random token; single-use; 7-day TTL |
| `token_type` | string | always `"bearer"` |
| `expires_in` | integer | seconds until access token expires (default 900) |

**JWT payload claims**:
```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "is_admin": false,
  "iat": 1749985200,
  "exp": 1749986100,
  "jti": "unique-token-id"
}
```

### Error Responses

| Status | Code | Condition |
|---|---|---|
| 401 | `invalid_credentials` | Email not found or password wrong (same message for both) |
| 403 | `account_inactive` | User account is suspended |

---

## POST /v1/auth/refresh

Exchange a valid refresh token for a new access token (and new refresh token).

### Request

```json
{
  "refresh_token": "dGhpcyBpcyBhIHJhbmRvbSByZWZyZXNoIHRva2Vu..."
}
```

### Response `200 OK`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "bmV3IHJhbmRvbSByZWZyZXNoIHRva2Vu...",
  "token_type": "bearer",
  "expires_in": 900
}
```

Old refresh token is invalidated on success (single-use rotation).

### Error Responses

| Status | Code | Condition |
|---|---|---|
| 401 | `invalid_refresh_token` | Token not found, already used, or expired |

---

## POST /v1/auth/logout

Invalidate the current session's refresh token.

### Request Headers

```
Authorization: Bearer <access_token>
```

### Request Body

```json
{
  "refresh_token": "dGhpcyBpcyBhIHJhbmRvbSByZWZyZXNoIHRva2Vu..."
}
```

### Response `204 No Content`

### Error Responses

| Status | Code | Condition |
|---|---|---|
| 401 | `unauthorized` | Missing or invalid access token |

---

## Protected Endpoints (existing, updated)

All existing endpoints that call `require_user()` will additionally accept a JWT bearer token. The dependency checks session cookie first (backward compatibility during transition), then falls back to JWT Bearer.

### Required Header

```
Authorization: Bearer <access_token>
```

### Error Response

| Status | Code | Condition |
|---|---|---|
| 401 | `token_expired` | Access token past its `exp` claim |
| 401 | `invalid_token` | Malformed, invalid signature, or missing token |
| 401 | `unauthorized` | No credentials provided at all |
