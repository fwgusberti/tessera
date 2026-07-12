# Feature Specification: Add Document Button in Space

**Feature Branch**: `061-add-document-button`

**Created**: 2026-07-11

**Status**: Draft

**Input**: User description: "create add document button in space"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a document from within a space (Priority: P1)

A user browsing a space (folder) page wants to add a new document to that space without leaving it. Today the space page only offers "Add Space"; to create a document the user must navigate to the global Documents page and manually pick the space from a list. With this feature, an "Add Document" button on the space page opens the document creation dialog with the current space already selected. After saving, the new document appears in the space's content grid immediately.

**Why this priority**: This is the core value of the feature — it removes the navigation detour and the error-prone manual space selection. Without it, nothing else in this spec matters.

**Independent Test**: Can be fully tested by opening any space the user can edit, clicking "Add Document", filling in a title, and saving — then verifying the document appears in that space's grid without a page reload or navigation.

**Acceptance Scenarios**:

1. **Given** a user with edit rights viewing a space page, **When** they click the "Add Document" button, **Then** a document creation dialog opens with the current space preselected as the destination.
2. **Given** the creation dialog is open from a space page, **When** the user enters a valid title and saves, **Then** the document is created in that space and appears in the space's content grid without a full page reload.
3. **Given** the creation dialog is open, **When** the user cancels or dismisses it, **Then** no document is created and the space page is unchanged.
4. **Given** the creation dialog is open, **When** the user submits without a title, **Then** a validation message is shown and nothing is created.
5. **Given** a space page whose space is empty (no sub-folders, no documents), **When** the user creates a document via the button, **Then** the empty-state message is replaced by the grid showing the new document.

---

### User Story 2 - Permission-aware visibility (Priority: P2)

A user whose role in the space only allows viewing should not be offered a document creation action that would fail. The "Add Document" button is shown only to users whose role in the space permits creating documents (editors and admins).

**Why this priority**: Prevents a confusing dead-end (button that always errors) and keeps the space page consistent with the platform's role model, but the P1 flow is still valuable on its own for permitted users.

**Independent Test**: Can be tested by viewing the same space page as an editor (button visible) and as a viewer (button absent).

**Acceptance Scenarios**:

1. **Given** a user with an editor or admin role in the space, **When** they view the space page, **Then** the "Add Document" button is visible.
2. **Given** a user with a viewer role in the space, **When** they view the space page, **Then** the "Add Document" button is not shown.
3. **Given** a viewer-role user who triggers creation anyway (e.g., stale page after a role change), **When** the save is rejected, **Then** a clear error message is shown in the dialog and no document appears.

---

### Edge Cases

- Space is deleted (or the user loses access) while the dialog is open: saving fails with a clear error message; no document is created.
- Creation request fails (network or server error): the dialog stays open, shows the error, and preserves the user's entered content so nothing is lost.
- The user changes the destination space inside the dialog to a different space: the document is created in the chosen space; it appears in the current space's grid only if the current space was chosen.
- Double-click on save: only one document is created (save is disabled while submitting).
- Very long titles or content: same validation rules as the existing document creation flow apply — this feature introduces no new rules.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The space (folder) page MUST display an "Add Document" button alongside the existing "Add Space" action for users whose role in the space allows document creation (editor or admin).
- **FR-002**: Clicking the button MUST open the document creation dialog with the currently viewed space preselected as the destination space.
- **FR-003**: The dialog opened from a space page MUST offer the same capabilities as the existing document creation flow (title, language, confidentiality, content, and AI draft assistance where the user's role permits it).
- **FR-004**: On successful creation, the new document MUST appear in the space page's content grid immediately, without a full page reload; if the space was previously empty, the empty-state message MUST be replaced by the grid.
- **FR-005**: The button MUST NOT be shown to users whose role in the space is viewer-only.
- **FR-006**: If creation fails for any reason (validation, permissions, server error), the dialog MUST show a clear error message and MUST NOT discard the user's entered content.
- **FR-007**: The existing document creation entry point on the global Documents page MUST continue to work unchanged.

### Key Entities

- **Document**: A titled content item that lives in exactly one space; created here with title, language, confidentiality, and optional initial content.
- **Space**: A folder-like container for documents and sub-spaces; the page the button lives on identifies the destination space.
- **Space role**: The user's effective role in a space (viewer, editor, admin); determines whether the creation action is offered.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user on a space page can create a document in that space in under 1 minute without navigating to any other page.
- **SC-002**: 100% of documents created via the space-page button land in the space that was preselected (unless the user explicitly changed the destination).
- **SC-003**: The newly created document is visible in the space's content grid within 2 seconds of saving, with no manual refresh.
- **SC-004**: Viewer-role users are never shown the creation action (0 occurrences in role-based UI checks).

## Assumptions

- The destination space is preselected to the currently viewed space, but the user may still change it inside the dialog (matching the existing dialog's behavior); creating in another space is allowed and simply doesn't add the document to the current grid.
- "Allows document creation" maps to the platform's existing space roles: editor and admin can create; viewer cannot. No new roles or permissions are introduced.
- The existing document creation dialog (fields, validation, AI assistance) is reused as-is; this feature only adds a new entry point and preselection — no changes to document fields or creation rules.
- Server-side permission enforcement for document creation already exists and is unchanged; this feature only adjusts what the user is offered in the interface.
- Mobile/responsive behavior follows the existing space page and dialog patterns; no new layout requirements.
