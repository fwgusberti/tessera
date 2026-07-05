# Contract: `POST /v1/spaces` (extended)

Existing endpoint in the spaces router (`apps/api/tessera_api/routers/spaces.py`).
This feature extends its request shape and internal orchestration; the route,
method, auth dependency (`CompanyContext`), and success status (`201`) are
unchanged, so the admin console's existing calls keep working unmodified.

## Request

```json
{ "name": "Marketing" }
```

or, from a space's folder view (sub-space creation):

```json
{ "name": "Q3 Campaigns", "parent_space_id": "8f0e...": }
```

or, the existing admin-console shape (unchanged, still fully supported):

```json
{
  "slug": "marketing",
  "name": "Marketing",
  "sector": "growth",
  "default_language": "pt-BR"
}
```

| Field | Type | Required | Change |
|-------|------|----------|--------|
| `name` | `string` | yes | unchanged |
| `slug` | `string \| null` | no (was required) | **relaxed** — auto-derived from `name` when omitted |
| `sector` | `string` | no, defaults to `"General"` (was required) | **relaxed** |
| `parent_space_id` | `UUID \| null` | no | **new** |
| `default_language` | `string` | no, defaults to `"pt-BR"` | unchanged |
| `retention_policy` | `object` | no, defaults to `{}` | unchanged |
| `confidence_threshold` | `number` | no, defaults to `0.7` | unchanged |

`company_id` is never accepted in the body — it always comes from the
authenticated `CompanyContext` (Tenant Isolation, FR-011).

## Resolution & authorization

1. Resolve `user_id`/`company_id` from `ctx` (unchanged).
2. Call `SpaceHierarchyService.create(actor_id=user_id, company_id=company_id,
   name=body.name, sector=body.sector, slug=body.slug,
   parent_space_id=body.parent_space_id, default_language=..., retention_policy=...,
   confidence_threshold=...)`.
3. Inside the service:
   - Validate `name.strip()` is non-empty and ≤255 chars — violation raises
     `ValueError("empty_name")` / `ValueError("name_too_long")` → router maps to
     `400 {"error": {"code": "invalid_name", "message": <reason>}}` (existing
     `_invalid_name` helper, same as `rename`).
   - If `parent_space_id` is set: resolve it via
     `get_by_id_for_company(parent_space_id, company_id)` (miss → `ValueError("cross_company")`),
     check the actor holds `SpaceRole.ADMIN` there (miss → `PermissionError`),
     and check `len(ancestor_chain) + 1 < _MAX_DEPTH` (violation →
     `ValueError("depth_limit")`). `ValueError`s map to
     `400 {"error": {"code": "invalid_parent", "message": <reason>}}` (existing
     `_invalid_parent` helper, same mapping `set_parent` already uses);
     `PermissionError` maps to `403 {"error": {"code": "forbidden", "message": "Access denied"}}`
     (existing `_forbidden` helper).
   - Resolve the slug: pass through if provided, else derive via `slugify(name)`
     and disambiguate against `SpaceRepository.slug_exists`.
   - Persist via `SpaceRepository.create(space)` (existing method, unchanged
     signature).
4. Router grants the creator's admin membership (unchanged 042 behavior:
   `SpaceMembership(space_id=created.id, user_id=actor_id, role=SpaceRole.ADMIN)`
   via `SqlSpaceMembershipRepository.add`).
5. Router writes two audit records: the new `space_created` entry, then the
   existing `member_invited` entry (see [data-model.md](../data-model.md)).

## Response 201

```json
{ "space": { "id": "uuid", "slug": "q3-campaigns", "name": "Q3 Campaigns", "sector": "General", "parent_space_id": "8f0e...", "...": "..." } }
```

Same shape as today (`_space_response(created)`) — the frontend `AddSpaceModal`
drops it straight into local state, the same way `RenameSpaceModal.onUpdated`
already does.

## Side effects

- `INSERT INTO spaces (...)` (existing statement, now possibly with
  `parent_space_id` set directly instead of via a follow-up `PATCH`).
- `INSERT INTO space_memberships (...)` for the creator's admin grant (unchanged).
- Two `INSERT INTO audit_records (...)` (one new, one existing — see data model).
- No Celery dispatch — creating an (initially empty) space has no search-index or
  downstream effect, same as rename.

## Not applicable / no change elsewhere

- `GET /v1/spaces`, `GET /v1/spaces/{id}/ancestors`, `GET /v1/spaces/{id}`:
  unchanged; a newly created space simply appears in these listings on the next
  fetch.
- `PATCH /spaces/{id}/parent`, `DELETE /spaces/{id}/parent`, `PATCH
  /spaces/{id}/name`: unchanged; still the only way to *change* an existing
  space's parent or name after creation.
