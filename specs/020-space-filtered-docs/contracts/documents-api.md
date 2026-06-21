# API Contract: GET /v1/documents

This document describes the updated contract for the `GET /v1/documents` endpoint after this feature.

## Endpoint

```
GET /v1/documents
```

**Authentication**: Required — Bearer token (JWT) or session cookie.

## Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `space_id` | UUID | No | When present, restricts results to the given space. When absent, returns documents from all spaces the authenticated user has access to. |
| `state` | string | No | Lifecycle state filter (`ingested`, `published`, `archived`, etc.). Applied on top of space filtering. |

## Behaviour

### No `space_id` (new default behaviour)
1. Load the authenticated user from the database using the JWT `sub` claim.
2. If `user.is_admin`: fetch documents from all spaces.
3. Otherwise: find all spaces where `role_permissions.idp_group ∈ user.groups` (SQL JOIN). Fetch documents from those spaces.
4. Apply `state` filter if present.
5. Return the union of all matching documents.

### With `space_id` (unchanged behaviour)
Fetch documents for the given space, filtered by `state` if present. Access control on the space is not enforced at this endpoint (relies on the space existing and the caller being authenticated).

## Response

```json
{
  "documents": [
    {
      "id": "uuid",
      "space_id": "uuid",
      "title": "string",
      "language": "string",
      "confidentiality": "public_internal | internal | confidential | restricted",
      "tags": ["string"],
      "validity_until": "date | null",
      "state": "ingested | no_owner | published | outdated | expired | archived",
      "current_version_id": "uuid | null",
      "owner_user_id": "uuid | null",
      "created_at": "datetime | null",
      "updated_at": "datetime | null"
    }
  ]
}
```

`documents` is an empty array when the user has no accessible spaces or no documents exist.

## Error Responses

| Status | Condition |
|--------|-----------|
| 401 | Missing or invalid authentication |
| 422 | `space_id` or `state` parameter cannot be parsed |

## Access Boundary Invariant

Documents from spaces for which the authenticated user has no `role_permissions` record (via their groups) MUST NOT appear in the response when `space_id` is omitted. This is enforced by the server-side JOIN query.

Admin users (`is_admin = True`) receive documents from all spaces.
