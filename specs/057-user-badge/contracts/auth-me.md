# Contract: `GET /v1/auth/me`

Returns the identity of the **currently authenticated principal**, derived solely
from the verified access token's subject. Used by the user badge to obtain the
display name (email is already available client-side from the decoded token).

## Request

```
GET /v1/auth/me
Authorization: Bearer <access_token>
```

No path, query, or body parameters. No user-supplied identity is accepted — the
subject is taken from the token established at the request boundary.

## Responses

### 200 OK
```json
{
  "id": "3f2a…",
  "email": "person@example.com",
  "display_name": "Ada Lovelace",
  "is_admin": false
}
```
- `display_name` is `null` when the user has not set one.
- `id` and `email` always equal the token subject's identity.

### 401 Unauthorized
Missing, malformed, or expired bearer token. Standard auth-error envelope.

### 404 Not Found (defensive)
Token subject references a user row that no longer exists. Returns the standard
error envelope; not expected in normal operation.

## Behavior / invariants

- **Tenant isolation**: reads only the caller's own `users` row via
  `SqlUserRepository.get_by_id(UUID(sub))`. No `company_id`-scoped table is
  queried; no cross-account data is reachable.
- **Read-only**: no state change, so no audit-log entry is required (audit logging
  applies to state-changing actions per the constitution).
- **Idempotent & cacheable per session**: repeated calls for the same token
  return the same identity.

## Tests (write first — TDD)

1. **Happy path**: authenticated request returns `id`/`email` matching the token
   and the user's stored `display_name`.
2. **Null name**: user with no `display_name` → `display_name: null`, `email`
   present.
3. **Unauthenticated**: no token → 401.
4. **Isolation (SC-004)**: user A (company 1) and user B (company 2) each call
   `/auth/me`; each response's `id`/`email` is their own and never the other's.
5. **No identity substitution**: response `email` equals the token's `email`
   claim / subject's stored email.
