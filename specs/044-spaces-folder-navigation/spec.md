# Feature Specification: Spaces as Drive-Style Folders (UI)

**Feature Branch**: `044-spaces-folder-navigation`

**Created**: 2026-06-30

**Status**: Draft

**Input**: User description: "make spaces like google drive folders in ui"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse spaces by drilling into folders (Priority: P1)

A user opens the Spaces page and sees their top-level spaces displayed as folder tiles in a grid, the same way Google Drive shows folders. Opening a folder tile navigates into that space, replacing the grid with that space's own contents, while a breadcrumb trail at the top shows the path taken so far. Clicking any breadcrumb segment jumps straight back to that ancestor.

**Why this priority**: This is the core interaction the feature exists to deliver. Without drill-down navigation and breadcrumbs, none of the other capabilities (mixed contents, drag-and-drop) have anywhere to live. It replaces the current flat, fully-expanded, indentation-based list, which becomes unreadable once a company has more than a handful of nested spaces.

**Independent Test**: Can be fully tested by loading the Spaces page, opening a folder with at least one sub-folder, confirming the view updates to show only that folder's contents, and confirming the breadcrumb accurately reflects the path — delivers a usable hierarchy-navigation experience on its own, even before mixed contents or drag-and-drop exist.

**Acceptance Scenarios**:

1. **Given** a user with access to three top-level spaces and no folder currently open, **When** they load the Spaces page, **Then** they see exactly those three spaces rendered as folder tiles in a grid, with no sub-folders shown.
2. **Given** a user viewing the top-level grid, **When** they open a folder tile for a space that has sub-folders, **Then** the view updates to show that space's direct sub-folders, and a breadcrumb appears showing "Root › [opened space name]".
3. **Given** a user two levels deep in the hierarchy, **When** they click the first breadcrumb segment, **Then** they return to the top-level grid view.
4. **Given** a user navigates directly to a URL for a specific space they have access to, **When** the page loads, **Then** it opens directly into that space's folder view (not the top-level grid), with the correct breadcrumb path.

---

### User Story 2 - See sub-folders and documents together inside a folder (Priority: P2)

When a user opens a folder, they see both its direct sub-folders and the documents that belong directly to it in one combined view, visually distinguished by folder vs. document icons — matching how Google Drive shows folders and files side by side inside a folder.

**Why this priority**: This is what makes the experience feel like Drive rather than just a re-skinned tree view. It depends on P1's drill-down navigation existing first, but delivers the actual "folder full of things" payoff once it does.

**Independent Test**: Can be fully tested by opening a space that has both sub-spaces and documents assigned directly to it, and confirming both appear together in the same view with distinguishable iconography — delivers value independent of whether drag-and-drop (P3) is implemented.

**Acceptance Scenarios**:

1. **Given** a folder with two sub-folders and three documents assigned directly to it, **When** the user opens that folder, **Then** all five items appear in the same view, with folders and documents visually distinguishable from each other.
2. **Given** a folder with sub-folders but no documents assigned directly to it, **When** the user opens that folder, **Then** only the sub-folders are shown (no document items, no error).
3. **Given** a folder with no sub-folders and no documents, **When** the user opens that folder, **Then** an empty-state message is shown indicating the folder has no contents.
4. **Given** a user opens a document tile inside a folder, **When** they select it, **Then** they are taken to that document, consistent with existing document-opening behavior elsewhere in the app.

---

### User Story 3 - Reorganize the hierarchy by dragging folders (Priority: P3)

A user with permission to manage a space's hierarchy drags a folder tile and drops it onto another folder tile (or onto a breadcrumb segment) to move it there, mirroring Google Drive's drag-and-drop move gesture. The moved folder immediately disappears from its old location and appears under its new parent.

**Why this priority**: This is a productivity enhancement on top of the browsing experience delivered by P1 and P2. Reorganizing spaces is a less frequent action than browsing them, so it can ship after the core navigation and content-viewing experience is solid. The existing explicit "move" action remains as a fallback, so this story is additive rather than blocking.

**Independent Test**: Can be fully tested by dragging a folder tile onto another folder tile and confirming the space's parent is updated and reflected in the view — delivers value independent of P1/P2 implementation details, as long as folder tiles exist to drag.

**Acceptance Scenarios**:

1. **Given** a user with permission to modify a space's hierarchy, **When** they drag a folder tile and drop it onto another folder tile they also have permission to modify, **Then** the dragged space's parent is updated to the drop target and the view reflects the change immediately.
2. **Given** a user drags a folder tile, **When** they drop it onto itself or onto one of its own descendant folders, **Then** the move is rejected and the user sees clear feedback explaining why.
3. **Given** a user without permission to modify a space's hierarchy, **When** they attempt to drag that space's folder tile, **Then** the drag either does not start or the drop is rejected with a clear permission message — the hierarchy is not changed.
4. **Given** a user who cannot perform drag gestures (e.g., keyboard-only or touch-only without drag support), **When** they need to move a space, **Then** they can still do so through the existing explicit move action, which remains available.

---

### Edge Cases

- What happens when the user has no accessible spaces at all? The top-level view shows an empty-state message instead of an empty grid.
- What happens when an opened folder has sub-folders but no documents, or documents but no sub-folders? Only the items that exist are shown; no placeholder or error appears for the missing category.
- What happens when a folder is completely empty (no sub-folders, no documents)? An empty-state message specific to that folder is shown.
- What happens when a user navigates to a deeply nested folder (many ancestor levels)? The breadcrumb trail reflects the full path; very long paths remain usable (e.g., via wrapping, scrolling, or truncation of middle segments).
- What happens when a user drags a folder and drops it somewhere that is not a valid folder or breadcrumb target (e.g., empty canvas space)? The drop is a no-op — the hierarchy is unchanged.
- What happens when a user tries to drop a folder onto itself or one of its own descendants? The move is rejected with clear feedback; no circular hierarchy is created.
- What happens when a user has access to a space but not to one of its ancestors? The folder view and breadcrumb degrade gracefully (consistent with existing ancestor-visibility handling) rather than exposing details of spaces the user cannot access.
- What happens when two users move the same space concurrently? The last successful move wins, consistent with existing reparenting behavior; the view reflects the current server state after the action completes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display the user's top-level accessible spaces (spaces with no accessible parent) as folder tiles in a grid when the Spaces page loads with no folder selected.
- **FR-002**: Users MUST be able to open a folder tile to navigate into that space, replacing the current view with that space's own contents.
- **FR-003**: When a folder is opened, system MUST display both its direct sub-folders and the documents assigned directly to it (not documents belonging to deeper descendants) in a single combined view.
- **FR-004**: System MUST visually distinguish folder tiles from document tiles within the combined view.
- **FR-005**: System MUST display a breadcrumb trail showing the full path from the top level down to the currently opened folder, updating as the user navigates.
- **FR-006**: Users MUST be able to click any breadcrumb segment to navigate directly back to that ancestor folder.
- **FR-007**: System MUST display an empty-state message when an opened folder has no sub-folders and no documents.
- **FR-008**: System MUST display an empty-state message at the top level when the user has no accessible spaces.
- **FR-009**: Navigating directly to a URL for a specific accessible space MUST open that space's folder view directly, with the correct breadcrumb path, rather than requiring the user to browse there from the top level.
- **FR-010**: Users with permission to modify a space's hierarchy MUST be able to move that space to a new parent by dragging its folder tile and dropping it onto another folder tile or breadcrumb segment they also have permission to modify.
- **FR-011**: System MUST reject and prevent a folder from being moved onto itself or onto one of its own descendant folders, with clear feedback to the user when this is attempted.
- **FR-012**: System MUST reflect a successful drag-and-drop move immediately in the current view.
- **FR-013**: System MUST NOT permit a drag-and-drop move for a user who lacks permission to modify the relevant space's hierarchy; the drag MUST NOT be available, or the drop MUST fail with a clear permission message, and the hierarchy MUST remain unchanged.
- **FR-014**: System MUST provide a non-drag alternative for moving a space to a new parent (e.g., retaining the existing explicit move action), so the capability remains available to users who cannot perform drag gestures.
- **FR-015**: Each folder tile MUST indicate the current user's role/access level for that space, consistent with existing role-badge behavior.
- **FR-016**: Each folder tile MUST provide access to the space's existing per-space actions (e.g., Members) without requiring the user to drill into it first.

### Key Entities

- **Space (Folder)**: Existing entity representing a space, now presented as a folder tile in this UI. Key attributes already exist: name, sector, parent space reference, and the user's effective role for it. This feature changes how spaces are *displayed and navigated*, not the underlying data model.
- **Document (as folder content)**: Existing document entity, now additionally rendered inline as an item within the folder view of the space it belongs to, alongside that space's sub-folders.
- **Breadcrumb Path**: The ordered sequence of ancestor spaces from the top level down to the currently opened folder. Used both for display (navigation trail) and as valid drop targets for drag-and-drop moves.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can navigate from the top-level Spaces view to any folder up to three levels deep in three clicks or fewer.
- **SC-002**: Users can tell, at a glance and without clicking, whether an item inside an opened folder is a sub-folder or a document.
- **SC-003**: Users can move a space to a new parent in a single drag-and-drop action, without opening a separate dialog, in under 10 seconds.
- **SC-004**: In usability testing, at least 90% of first-time users successfully locate a document nested two folders deep without external guidance.
- **SC-005**: Attempting an invalid move (onto self or a descendant) produces feedback the user understands as "not allowed" without needing to consult documentation or support.

## Assumptions

- The existing nested-spaces hierarchy data and ancestor-lookup capability (introduced for feature 041) already provide everything needed to compute top-level spaces, direct sub-folders, and breadcrumb ancestors — no new backend hierarchy concept is required.
- "Documents assigned directly to it" means documents whose space matches the currently opened folder exactly, not documents belonging to any descendant folder — matching Google Drive's non-recursive folder listing (a sub-folder's contents are only visible after opening that sub-folder).
- The data needed to list a space's documents already exists (used today by the separate filtered documents view) and can be reused to render documents inline within a folder.
- Creating new spaces (folders) remains on the existing admin creation flow; adding folder creation directly from this drill-down view is out of scope for this feature.
- A grid of folder tiles is the only supported layout for this feature; a list-view toggle is out of scope.
- Drag-and-drop reparenting reuses the same authorization rules already enforced for moving a space to a new parent; this feature changes how the action is triggered, not who is allowed to perform it.
- Per-space actions carried over from the current design (e.g., Members) remain available from the folder tile; only navigation and layout change.
