# Contract: `PATCH /v1/spaces/{space_id}/name`

New endpoint added to the existing spaces router
(`apps/api/tessera_api/routers/spaces.py`), following the same auth,
tenant-scoping, and error-shape conventions already used by
`PATCH /spaces/{space_id}/parent`.

## Request

Requires `CompanyContext` (same dependency used by `set_space_parent`), so
`company_id` and the caller's user info are available.

```json
{ "name": "New Space Name" }
```

`name` is a required string. Client-side trimming is expected but the server is
authoritative for validation (see below).

## Resolution & authorization

1. Resolve `user_id` from `ctx` (same as `set_space_parent`).
2. Call `SpaceHierarchyService.rename(actor_id=user_id, space_id=space_id, name=body.name, company_id=company_id)`.
3. Inside the service:
   - Resolve the space via `SpaceRepository.get_by_id_for_company(space_id, company_id)`.
     A miss raises a not-found condition → router maps to the generic
     `404 {"error": {"code": "not_found", "message": "Not found"}}`, matching the
     existing indistinguishable-404 convention used elsewhere in this router
     (cross-tenant space IDs look identical to absent ones).
   - Check the actor's `SpaceMembership` role on `space_id` is `ADMIN` — mirrors
     `set_parent`'s child-admin check. Not-admin (or no membership) raises
     `PermissionError` → router maps to `403 {"error": {"code": "forbidden", "message": "Access denied"}}`,
     same helper (`_forbidden()`) already used by `set_space_parent`.
   - Validate `name.strip()` is non-empty and ≤ 255 chars. Violation raises
     `ValueError("empty_name")` or `ValueError("name_too_long")` → router maps to
     `400 {"error": {"code": "invalid_name", "message": <reason>}}`, mirroring the
     existing `_invalid_parent(reason)` helper pattern used for `set_parent`'s
     `ValueError`s (`self_parent`, `cycle`, `depth_limit`, `cross_company`).
   - Persist via `SpaceRepository.rename(space_id, name.strip())`.

## Response 200

```json
{ "space": { "id": "uuid", "name": "New Space Name", "...": "..." } }
```

Same shape as `set_space_parent`'s response — the full updated `Space`
(`_space_response(updated)`), so the frontend can drop it straight into local
state exactly like `SetParentModal.onUpdated` already does.

## Side effects

- `UPDATE spaces SET name = :name WHERE id = :space_id` (single statement,
  mirrors `set_parent`'s `UPDATE ... SET parent_space_id = ...`). `updated_at`
  refreshes via the existing `onupdate=func.now()` column default — no code
  change needed for that.
- One audit record: `action="space_renamed"`, `entity_type="space"`,
  `entity_id=space_id`, `metadata={"new_name": <new name>}`.
- No Celery dispatch — renaming a space has no search-index or downstream
  effect (unlike document publish/reindex).

## Not applicable / no change elsewhere

- `GET /v1/spaces`, `GET /v1/spaces/{id}/ancestors`: unchanged. They read
  `spaces.name` directly, so a rename is visible on the next fetch with no
  extra code — matches the spec's "no live push required" assumption.
- `slug`, `parent_space_id`, and all other `Space` fields: untouched by this
  endpoint. A future generic space-update endpoint (if ever added) is out of
  scope here — see [research.md §1](../research.md#1-endpoint-shape-dedicated-patch-name-vs-generic-patch-spacesid).
