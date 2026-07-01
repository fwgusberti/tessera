# Contracts: Reused Endpoints

This feature adds **no new backend endpoints**. It is a frontend-only
(`apps/web`) redesign that consumes existing, already-tenant-scoped API
endpoints. This document records the exact shapes the new UI code depends on,
as implemented today in `apps/api/tessera_api/routers/spaces.py` and
`apps/api/tessera_api/routers/documents.py`.

## `GET /v1/spaces`

Returns the caller's full accessible set, flat (no pagination), each item
carrying `parent_space_id`. Used to compute both the root grid and every
folder's direct sub-folders (client-side filter, see `data-model.md`).

Response:
```json
{
  "spaces": [
    {
      "id": "uuid", "slug": "...", "name": "...", "sector": "...",
      "parent_space_id": "uuid | null",
      "default_language": "...", "confidence_threshold": 0.7,
      "retention_policy": {},
      "effective_role": "admin | editor | viewer",
      "is_direct": true
    }
  ]
}
```

## `GET /v1/spaces/{id}/ancestors`

Returns the ordered ancestor chain (root-most first) for the breadcrumb.
404 if the caller has no access to `id`. Used unchanged from the existing
`SpaceBreadcrumb.tsx` implementation, extended to also serve as the
drop-target list for drag-and-drop reparenting.

Response:
```json
{ "ancestors": [{ "id": "uuid", "name": "...", "slug": "..." }] }
```

## `GET /v1/documents?space_id={id}`

Returns documents whose `space_id` matches `{id}` exactly — confirmed
non-recursive (`doc_repo.list_by_space`). Used to populate a folder's
`documents` list (FR-003).

Response:
```json
{ "documents": [{ "id": "uuid", "space_id": "uuid", "title": "...", "state": "...", "confidentiality": "...", "...": "..." }] }
```

## `PATCH /v1/spaces/{id}/parent`

Body: `{ "parent_space_id": "uuid" }`. Sets `id`'s parent. Server-side
(`SpaceHierarchyService.set_parent`) enforces: self-parent rejection,
same-company target, admin role required on **both** `id` and the target
parent, cycle rejection, max depth 10. Used by both the existing
`SetParentModal` and the new drag-and-drop drop handler.

Success: `{ "space": { ...updated Space... } }`
Errors: `400 { "error": { "code": "invalid_parent", "message": "self_parent | cross_company | cycle | depth_limit" } }`, `403 { "error": { "code": "forbidden", ... } }`

## `DELETE /v1/spaces/{id}/parent`

Removes `id`'s parent (promotes to root). Requires admin role on `id`. Used
when a folder tile is dropped on the "Root" breadcrumb crumb.

Success: `{ "space": { ...updated Space... } }`
Errors: `403 { "error": { "code": "forbidden", ... } }`
