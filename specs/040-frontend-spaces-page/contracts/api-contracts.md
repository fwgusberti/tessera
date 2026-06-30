# API Contracts: Frontend Spaces Page

All endpoints are existing backend contracts. This feature consumes them; it does not define new ones.

---

## GET /v1/spaces

**Purpose**: Retrieve all spaces accessible to the authenticated user within their active company.

**Auth**: Bearer token required. Company context is derived server-side from the JWT.

**Response** `200 OK`:
```json
{
  "spaces": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "slug": "engineering",
      "name": "Engineering",
      "sector": "Technology",
      "default_language": "en",
      "confidence_threshold": 0.7,
      "retention_policy": {}
    }
  ]
}
```

**Errors**:
- `401 Unauthorized` — invalid or expired token; handled by `api.get()` with auto-refresh

**Tenant guarantee**: Only spaces belonging to the authenticated company are returned.

---

## GET /v1/spaces/{space_id}/members/me

**Purpose**: Retrieve the current user's membership (and role) within a specific space.

**Auth**: Bearer token required.

**Path param**: `space_id` — UUID of the space.

**Response** `200 OK`:
```json
{
  "membership": {
    "space_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "660e8400-e29b-41d4-a716-446655440001",
    "role": "editor",
    "created_at": "2026-01-15T10:00:00Z"
  }
}
```

**Errors**:
- `404 Not Found` — user is not a member of this space, or the space does not belong to the active company (indistinguishable by design — cross-tenant 404 masking)
- `401 Unauthorized` — invalid or expired token

**Handling on the frontend**: A 404 results in `role: null` for that space card. The card still renders with no role badge (graceful degradation).

---

## Existing Routes Linked From Space Cards

These routes already exist; the Spaces page simply links to them.

| Link | Destination |
|------|-------------|
| Members | `/spaces/{id}/members` — existing page (`app/spaces/[id]/members/page.tsx`) |
| Documents | `/documents?space={id}` — existing page with space filter (`app/documents/page.tsx`) |
