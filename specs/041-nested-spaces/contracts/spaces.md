# API Contract: Spaces (Nested Spaces additions)

**Feature**: 041-nested-spaces | **Date**: 2026-06-30

All endpoints require `Authorization: Bearer <access_token>` and are prefixed `/v1`.

---

## Modified Endpoints

### GET /v1/spaces

Returns all spaces the authenticated user can access within their active company (direct memberships + inherited via parent chain).

**Breaking change**: previously returned all company spaces regardless of user membership; now returns only accessible spaces.

**Response** `200 OK`:
```json
{
  "spaces": [
    {
      "id": "uuid",
      "slug": "engineering",
      "name": "Engineering",
      "sector": "tech",
      "parent_space_id": null,
      "default_language": "pt-BR",
      "confidence_threshold": 0.7,
      "retention_policy": {},
      "effective_role": "admin",
      "is_direct": true
    },
    {
      "id": "uuid",
      "slug": "frontend",
      "name": "Frontend",
      "sector": "tech",
      "parent_space_id": "<engineering-uuid>",
      "default_language": "pt-BR",
      "confidence_threshold": 0.7,
      "retention_policy": {},
      "effective_role": "admin",
      "is_direct": false
    }
  ]
}
```

**New fields on each space object**:
- `parent_space_id` — UUID of parent space, or `null` for root spaces
- `effective_role` — `"admin" | "editor" | "viewer"` — most-permissive role from any membership path
- `is_direct` — `true` if user has a direct `SpaceMembership` row; `false` if access is entirely inherited

---

### GET /v1/spaces/{space_id}

Access check now includes effective membership: a user who inherits access to this space through an ancestor's membership is granted access (same response as if direct member).

**Response** `200 OK`: same shape as before plus `parent_space_id` field.

**Response** `404 Not Found`: if space does not exist OR user has no effective access (direct or inherited) to the space.

---

## New Endpoints

### PATCH /v1/spaces/{space_id}/parent

Set or change the parent of a space. Actor must have `admin` role in both the child space and the intended parent space.

**Request body**:
```json
{
  "parent_space_id": "uuid"
}
```

**Response** `200 OK`:
```json
{
  "space": { ...full space object with updated parent_space_id... }
}
```

**Errors**:
- `400 Bad Request` — self-parent, cycle, depth limit exceeded, or cross-company parent
  ```json
  { "error": { "code": "invalid_parent", "message": "..." } }
  ```
- `403 Forbidden` — actor lacks admin in child or parent space
  ```json
  { "error": { "code": "forbidden", "message": "Access denied" } }
  ```
- `404 Not Found` — space or proposed parent not found in actor's company

---

### DELETE /v1/spaces/{space_id}/parent

Remove the parent from a space (promote to root). Actor must have `admin` role in the child space only.

**Response** `200 OK`:
```json
{
  "space": { ...full space object with parent_space_id: null... }
}
```

**Errors**:
- `403 Forbidden` — actor lacks admin in child space
- `404 Not Found` — space not found in actor's company

---

### GET /v1/spaces/{space_id}/ancestors

Returns the ordered ancestor chain from immediate parent to root, for breadcrumb display. Does NOT grant access to ancestors — only returns their names and IDs. Available to any user with effective access to `space_id`.

**Response** `200 OK`:
```json
{
  "ancestors": [
    { "id": "uuid", "name": "Engineering", "slug": "engineering" },
    { "id": "uuid", "name": "Tech", "slug": "tech" }
  ]
}
```
`ancestors[0]` is the immediate parent; last element is the root. Empty array if space is a root.

**Errors**:
- `404 Not Found` — space not found or user has no effective access to the child space

---

## Error Shapes

All errors use the existing envelope:
```json
{ "error": { "code": "<machine_code>", "message": "<human_readable>" } }
```

New error codes introduced:
| Code | HTTP | Condition |
|---|---|---|
| `invalid_parent` | 400 | self-parent, cycle, depth limit, or cross-company |
| `forbidden` | 403 | actor lacks required role |
| `not_found` | 404 | space not found or not accessible (indistinguishable) |
