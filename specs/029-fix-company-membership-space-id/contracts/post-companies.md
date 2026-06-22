# Contract: POST /v1/companies

## Request

```
POST /v1/companies
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "name": "Acme Corp",         // string, 1–255 chars, required
  "industry": "Technology",    // string, optional
  "team_size": "11-50"         // one of: "1-10","11-50","51-200","201-1000","1000+", optional
}
```

## Success Response — 201 Created

```json
{
  "id": "<uuid>",
  "name": "Acme Corp",
  "industry": "Technology",
  "team_size": "11-50",
  "role": "admin",
  "created_at": "<iso8601>"
}
```

The `role` field reflects the creator's `CompanyMembership.role`, which MUST be `"admin"`.

## Error Responses

| Status | `code` | Condition |
|---|---|---|
| 401 | — | Missing or invalid JWT |
| 422 | `invalid_team_size` | `team_size` not in allowed set |
| 500 | — | (Bug: was returned before this fix due to `_membership_from_model` name collision) |

## Invariants enforced post-fix

- The company membership record stored in `company_memberships` uses `company_id` — NOT `space_id`.
- The response `role` field is populated from `CompanyMembership.role` (a `CompanyRole` enum), not `SpaceMembership.role`.
