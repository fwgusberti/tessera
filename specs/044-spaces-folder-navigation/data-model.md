# Data Model: Spaces as Drive-Style Folders (UI)

This feature introduces no new persisted entities and no schema change. It
re-presents existing entities (`Space`, `Document`) through a new client-side
view model.

## Existing entities (unchanged)

### Space (`apps/web/lib/types.ts`)
Already defined: `id`, `slug`, `name`, `sector`, `parent_space_id`,
`default_language`, `confidence_threshold`, `retention_policy`. Rendered as a
`FolderTile` in this feature instead of the current indented `SpaceCard`.

### SpaceAccess (`apps/web/lib/types.ts`)
Already defined: `{ space: Space, effective_role: SpaceRole, is_direct: boolean }`.
`effective_role` continues to drive the role badge and whether drag-and-drop /
"Set parent" is offered on a given tile (admin-only, enforced server-side
regardless).

### Document (`apps/web/lib/types.ts`)
Already defined: `id`, `space_id`, `title`, `language`, `confidentiality`,
`tags`, `state`, `current_version_id`, `owner_user_id`, `created_at`,
`updated_at`. Rendered as a `DocumentTile` inside the folder view of the space
matching `space_id`.

## New client-side view types (not persisted)

### Ancestor
Promote the interface currently declared locally inside
`SpaceBreadcrumb.tsx` into `apps/web/lib/types.ts` so it can be shared by the
breadcrumb and the new drop-target logic:

```ts
interface Ancestor {
  id: string;
  name: string;
  slug: string;
}
```

Sourced from the existing `GET /v1/spaces/{id}/ancestors` response, unchanged.

### FolderContents (derived, not fetched as a single shape)
Represents what a single opened folder — or the root — displays. Computed
client-side from the already-fetched `SpaceAccess[]` (from `GET /v1/spaces`)
and `Document[]` (from `GET /v1/documents?space_id=`), not a new API response
shape:

```ts
interface FolderContents {
  folder: Space | null;       // null when viewing the root/top level
  ancestors: Ancestor[];      // [] at root; breadcrumb + drop-target list otherwise
  subfolders: SpaceAccess[];  // direct children only (parent_space_id === folder.id)
  documents: Document[];      // documents with space_id === folder.id
}
```

**Derivation rules**:
- Root (`folder: null`): `subfolders` = every `SpaceAccess` whose `parent_space_id`
  is `null` or whose parent is not present in the user's accessible set (same
  rule `SpaceHierarchyView.buildTree` already applies today for root
  detection). `documents` = `[]` (root has no directly-assigned documents).
- Non-root: `subfolders` = every `SpaceAccess` whose `parent_space_id` equals
  `folder.id`. `documents` = the result of `GET /v1/documents?space_id={folder.id}`.

No state transitions apply — this is a read/render model, not a persisted
entity with a lifecycle. The one mutation this feature performs
(reparenting) already exists as `PATCH`/`DELETE /v1/spaces/{id}/parent` and
is documented in `contracts/reused-endpoints.md`, not introduced here.
