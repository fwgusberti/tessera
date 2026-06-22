# Contract: POST /v1/companies

This contract documents the existing endpoint with the corrected CORS behaviour
after the fix in this feature.

## Request

```
POST /v1/companies
Origin: <frontend_url>                    ← required for CORS check
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "name": "Acme Corp",
  "industry": "Technology",
  "team_size": "11-50"
}
```

**Field constraints**:
- `name` (required): 1–255 characters
- `industry` (optional): up to 100 characters
- `team_size` (optional): one of `"1-10"`, `"11-50"`, `"51-200"`, `"201-1000"`, `"1000+"`

## CORS Preflight (OPTIONS)

Before the POST, the browser sends:

```
OPTIONS /v1/companies
Origin: http://localhost:3000
Access-Control-Request-Method: POST
Access-Control-Request-Headers: authorization, content-type
```

After the fix, the server responds:

```
HTTP/1.1 200 OK
Access-Control-Allow-Origin: http://localhost:3000   ← explicit origin (not *)
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH, OPTIONS
Access-Control-Allow-Headers: authorization, content-type, ...
Access-Control-Max-Age: 600
```

**Key requirement**: `Access-Control-Allow-Origin` MUST be the exact request origin,
never `*`, when `Access-Control-Allow-Credentials: true` is set.

## Responses

### 201 Created

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Acme Corp",
  "industry": "Technology",
  "team_size": "11-50",
  "role": "admin",
  "created_at": "2026-06-21T12:00:00+00:00"
}
```

### 401 Unauthorized

Missing or invalid JWT.

```json
{ "error": { "code": "invalid_token", "message": "Invalid or expired token" } }
```

### 422 Unprocessable Entity

Validation error (e.g., invalid `team_size`).

```json
{ "error": { "code": "invalid_team_size", "message": "team_size must be one of ..." } }
```

### Network failure (frontend)

If the server is unreachable, the frontend MUST display:

> "Could not reach the server. Please check your connection and try again."

Raw `TypeError: Failed to fetch` MUST NOT be shown to users.
