# Research: Space Rename

No open `NEEDS CLARIFICATION` items — the feature reuses established patterns.
This file records the decisions made while grounding the plan in the existing
codebase.

## 1. Endpoint shape: dedicated `PATCH .../name` vs. generic `PATCH /spaces/{id}`

**Decision**: `PATCH /v1/spaces/{space_id}/name` with body `{"name": str}`.

**Rationale**: The existing spaces router already uses narrow, action-scoped PATCH/
DELETE routes for single-field mutations — `PATCH /spaces/{id}/parent` and
`DELETE /spaces/{id}/parent` — rather than one generic partial-update endpoint.
Following that convention keeps validation and permission logic scoped to exactly
one field, avoids accidentally exposing other mutable fields (e.g. `sector`,
`retention_policy`) through a generic PATCH before they have their own reviewed
rules, and matches what a frontend `RenameSpaceModal` needs to call.

**Alternatives considered**: A generic `PATCH /spaces/{space_id}` accepting a
partial `Space` body — rejected because it would silently widen the endpoint's
surface area (e.g. letting a caller also change `sector` or `retention_policy`)
without those fields having been specified, reviewed, or tested here.

## 2. Where the admin check lives

**Decision**: `SpaceHierarchyService.rename(actor_id, space_id, name, company_id)`
performs the admin check itself (`space_memberships` lookup, role must be
`ADMIN`), raising `PermissionError`, exactly like `set_parent`/`remove_parent`.

**Rationale**: Keeps all space-mutation authorization in one domain service
(Principle I — Domain-Driven Architecture) instead of splitting it between the
router and the service. The router already has an established
`except PermissionError: raise _forbidden()` mapping for this service.

**Alternatives considered**: Using the `CompanyAdminContext` FastAPI dependency
(used by `create_permission`) — rejected because that dependency checks
*company*-level admin, not *space*-level admin. Space rename must be gated on the
same space-scoped admin role as reparenting, not company-wide admin.

## 3. Validation placement (empty/too-long name)

**Decision**: Validate non-empty (post-trim) and ≤255 chars in the domain service
method, raising `ValueError` with a short reason string (`"empty_name"` /
`"name_too_long"`), mapped by the router to `400` via the existing
`_invalid_parent`-style helper pattern (renamed/generalized to a shared
`_invalid_request(reason)` helper or a new `_invalid_name(reason)` helper —
implementation detail for Phase 2).

**Rationale**: Mirrors exactly how `set_parent` validates (`self_parent`, `cycle`,
`depth_limit` as `ValueError` → `400`). Keeps the 255-char ceiling in one place
(matching `SpaceModel.name`'s `String(255)` column) rather than duplicating it
in both the router's Pydantic model and the service.

**Alternatives considered**: Enforcing max length only via a Pydantic
`Field(max_length=255)` on the request body — rejected as the sole mechanism
because it would produce FastAPI's generic 422 validation-error shape instead of
the domain-level `400` + reason shape already used for other space-mutation
rejections, breaking consistency with `set_parent`'s error contract. A `Field`
constraint MAY still be added as a defense-in-depth request-shape check, but the
domain service remains the source of truth for the rule.

## 4. Frontend integration point

**Decision**: Add a `RenameSpaceModal` component (new file, structurally mirroring
`SetParentModal`) and a "Rename" action rendered in `FolderTile` next to the
existing "Set parent" admin-only action. Both `apps/web/app/spaces/page.tsx` and
`apps/web/app/spaces/[id]/page.tsx` already hold `managingSpace` state and an
`onSetParent` callback threaded through `FolderGrid` → `FolderTile`; the same
threading pattern (`renamingSpace` state + `onRename` callback) is reused rather
than introducing a new state-management approach.

**Rationale**: Both pages already share `FolderGrid`/`FolderTile` and already
handle a modal-driven admin action (`SetParentModal`) with an `onUpdated` callback
that patches the space into local state (`handleSpaceUpdated`). Renaming needs the
identical optimistic-update shape (`Space` returned from the API replaces the
matching entry in `accesses`), so no new state pattern is needed.

**Alternatives considered**: Inline-editable name (click-to-edit text field
directly on the tile) — rejected for this iteration because it doesn't match the
existing "open a small modal for an admin action" convention already established
by `SetParentModal`, and a modal gives an explicit Cancel/Save affordance called
for by FR-003.
