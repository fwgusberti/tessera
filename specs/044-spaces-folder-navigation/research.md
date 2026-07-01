# Research: Spaces as Drive-Style Folders (UI)

## 1. Drag-and-drop implementation

**Decision**: Use the browser's native HTML5 Drag and Drop API (`draggable`, `onDragStart`/`onDragOver`/`onDrop`) directly on `FolderTile` and breadcrumb segments. No new npm dependency.

**Rationale**: `apps/web/package.json` has zero drag-and-drop libraries today (no `@dnd-kit/*`, no `react-dnd`). The interaction needed is simple — pick up one folder tile, drop it on one other tile or breadcrumb crumb — well within what the native API handles without a state-management layer. Adding a dependency for this would be disproportionate to the need and out of step with the project's otherwise minimal dependency footprint (`next`, `react`, `react-dom` are the only runtime deps).

**Alternatives considered**:
- `@dnd-kit/core`: better accessibility primitives and sortable-list support, but pulls in a library for a single drag-target-onto-target gesture; deferred unless native DnD proves insufficient during implementation.
- `react-dnd`: heavier abstraction (backends, HTML5Backend/TouchBackend split) than this single-gesture use case warrants.

## 2. Deep-linking / routing for the drill-down view

**Decision**: Add `apps/web/app/spaces/[id]/page.tsx` as a new Next.js App Router route rendering the folder-contents view for a given space id. `apps/web/app/spaces/page.tsx` remains the entry point and becomes the top-level (root) folder grid.

**Rationale**: The project already uses this exact pattern — `apps/web/app/spaces/[id]/members/page.tsx` is a sibling dynamic route. Using the router (not client-side-only state) gets FR-009 (direct URL deep-linking) for free via Next.js's built-in routing, and keeps browser back/forward behavior correct without custom history handling.

**Alternatives considered**:
- Single page with client-side `useState` for "current folder" and no URL change: rejected — fails FR-009 (deep link to a specific folder) and breaks the browser back button.

## 3. Fetching folder contents (sub-folders + documents)

**Decision**: Reuse `GET /v1/spaces` (already returns the user's full accessible flat list with `parent_space_id` on each item, fetched once) and `GET /v1/documents?space_id={id}` (already filters to documents whose `space_id` matches exactly — confirmed non-recursive via `doc_repo.list_by_space(space_id, ...)` in `apps/api/tessera_api/routers/documents.py`). Compute "top-level spaces" and "direct children of folder X" client-side by filtering the already-fetched flat list, the same way `SpaceHierarchyView.buildTree` already does today (`apps/web/components/spaces/SpaceHierarchyView.tsx`).

**Rationale**: Both endpoints already exist, are already tenant-scoped server-side, and already return exactly the data shape this feature needs. No backend change is required. `SpaceHierarchyView.buildTree`'s existing rule — a space is a root if its `parent_space_id` is null *or* its parent isn't in the accessible set — already correctly implements FR-001's "top-level = spaces with no accessible parent," including the case where a user can see a child space but not its (inaccessible) ancestor.

**Alternatives considered**:
- New backend endpoint `GET /v1/spaces/{id}/children`: rejected as unnecessary — the full accessible list is already small enough (no pagination on `GET /v1/spaces` today) to filter client-side, and a new endpoint would duplicate logic that already exists in `list_accessible_by_user`.

## 4. Reparenting authorization, cycle prevention, depth limit

**Decision**: Drag-and-drop calls the exact same `PATCH /v1/spaces/{id}/parent` (and `DELETE /v1/spaces/{id}/parent` for dropping onto the root breadcrumb crumb) already used by `SetParentModal.tsx`. No new endpoint, no client-side reimplementation of validation.

**Rationale**: `SpaceHierarchyService.set_parent` (`packages/core/tessera_core/services/space_hierarchy.py`) already enforces, server-side: self-parent rejection, same-company parent (`cross_company` on cross-tenant target), admin-in-child AND admin-in-parent permission, cycle detection via ancestor-chain lookup, and a max-depth-10 limit. This fully covers FR-011 (reject self/descendant drop) and FR-013 (no unauthorized reparent) without the UI needing to duplicate any of that logic — the UI's job is only to trigger the call and surface the resulting error (`self_parent` / `cross_company` / `cycle` / `depth_limit` / 403 `forbidden`) as user-facing feedback.

**Alternatives considered**:
- Pre-validating cycles client-side before calling the API: rejected — the accessible-spaces list the client holds may not include every space needed to compute the full ancestor chain (e.g., spaces the user can't see), so client-side cycle detection could be wrong; the server is the source of truth and already does this correctly.

## 5. Breadcrumb as a drop target

**Decision**: Extend `SpaceBreadcrumb` so each rendered crumb (including a new leading "Root" crumb representing the top level) is a valid drop target: dropping a folder tile on an ancestor crumb calls `PATCH /v1/spaces/{id}/parent` with that crumb's id; dropping on "Root" calls `DELETE /v1/spaces/{id}/parent`.

**Rationale**: Matches Google Drive's behavior, where breadcrumb segments accept dropped items to move them to a shallower level without navigating there first. Reuses the same two existing endpoints from research item 4 — no new backend surface.

## 6. Non-drag accessible fallback

**Decision**: Keep `SetParentModal.tsx` and its trigger unchanged, available from each folder tile, alongside the new drag-and-drop gesture.

**Rationale**: Native HTML5 drag-and-drop has no built-in keyboard or touch-without-drag equivalent. Removing the existing explicit "Set parent" action would regress accessibility for keyboard-only and some touch users, which FR-014 explicitly requires not to happen. This is the lowest-risk way to satisfy FR-014: nothing existing is removed, drag-and-drop is purely additive.
