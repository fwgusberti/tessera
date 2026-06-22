# Contract: GET /v1/companies/me

## Endpoint

`GET /v1/companies/me`

## Authentication

Requires a valid JWT Bearer token in the `Authorization` header.

Session cookies are accepted as an alternative credential **only if** the session dict contains a valid `sub` field (user identity). Incomplete session cookies (e.g., those created before fix 033 that contain only `active_company_id`) fall through to JWT Bearer auth.

## Access

Accessible to **any authenticated user** regardless of onboarding status. Returns an empty list for users with no company memberships — never a 4xx error due to onboarding state.

## Response: 200 OK

```json
{
  "companies": [
    {
      "id": "uuid-string",
      "name": "Company Name",
      "role": "admin"
    }
  ]
}
```

`role` is `"admin"` or `"member"`. The list is sorted alphabetically by `name`. Returns `{"companies": []}` when the user has no memberships.

## Error Responses

| Status | Code | When |
|--------|------|------|
| 401 | `invalid_token` | JWT is present but invalid or expired |
| 401 | `Not authenticated` | No credentials provided |
| 401 | `invalid_session` | Session cookie present but missing `sub` AND no JWT Bearer provided |

## What Changed in This Fix

- **Before**: A stale session cookie (missing `sub`) caused 401 even when a valid JWT was present
- **After**: `require_user` validates session completeness (`sub` presence) before using it; falls through to JWT on incomplete session
- **Before**: Mid-onboarding users got 403 on this endpoint
- **After**: This endpoint is exempt from the onboarding gate; mid-onboarding users get 200 with empty list
