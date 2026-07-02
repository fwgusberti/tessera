# Feature Specification: Delete Document

**Feature Branch**: `048-delete-document`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "add delete button in document"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Owner removes an obsolete document (Priority: P1)

A user who created a document opens it and finds it is no longer needed (duplicate, wrong upload, outdated draft). They use a delete action on the document detail page to permanently remove it, after confirming the action.

**Why this priority**: This is the core capability being requested — without it, nothing else in this feature has value. It covers the most common case: a user cleaning up their own content.

**Independent Test**: Can be fully tested by logging in as the document's owner, opening the document detail page, triggering delete, confirming the prompt, and verifying the document no longer appears anywhere in the system.

**Acceptance Scenarios**:

1. **Given** the signed-in user is the owner of a document, **When** they view the document detail page, **Then** they see a delete action.
2. **Given** the owner clicks delete, **When** they confirm the action in the confirmation prompt, **Then** the document is permanently removed and the user is taken back to a page that still exists (e.g., the document's space).
3. **Given** the document has been deleted, **When** anyone tries to open its old detail page or search for it, **Then** it no longer appears and the system communicates that it can't be found.

---

### User Story 2 - Admin removes another user's document (Priority: P2)

A space admin or platform admin needs to remove a document they did not create — for example, content that violates policy, was uploaded to the wrong space, or belongs to a user who has left the company. They open the document and delete it using the same delete action available to owners.

**Why this priority**: Admins are responsible for keeping spaces clean and compliant even when they aren't the original author. Without this, cleanup work would require someone else's cooperation or a manual database fix.

**Independent Test**: Can be fully tested by logging in as a space admin (or platform admin) who is not the document's owner, opening a document owned by someone else, deleting it, and confirming it is removed.

**Acceptance Scenarios**:

1. **Given** the signed-in user is a space admin or platform admin but not the document's owner, **When** they view the document detail page, **Then** they see a delete action.
2. **Given** an admin deletes a document they don't own, **When** the deletion completes, **Then** the document is removed for all users, including the original owner.

---

### User Story 3 - User backs out of an accidental deletion (Priority: P3)

A user with permission to delete clicks the delete action by mistake, or has second thoughts, and needs a way to back out before the document is actually gone.

**Why this priority**: Deletion is destructive and irreversible; a confirmation safety net protects users from accidental data loss and builds trust in the delete action's presence on every document page.

**Independent Test**: Can be fully tested by clicking delete, then choosing "cancel" (or equivalent) in the confirmation prompt, and verifying the document is untouched and still fully accessible.

**Acceptance Scenarios**:

1. **Given** a user with delete permission clicks the delete action, **When** the confirmation prompt appears, **Then** the document is not yet deleted.
2. **Given** the confirmation prompt is open, **When** the user cancels or dismisses it, **Then** the document remains exactly as it was and no data is removed.

---

### Edge Cases

- A user who is not the document's owner, and not a space admin or platform admin (e.g., an editor or viewer), does not see the delete action, and a direct attempt to delete is rejected even if the request bypasses the UI.
- Two admins/owners open the same document and one deletes it; the second person's later attempt to delete (or edit) the same document is rejected gracefully with a clear "no longer exists" message rather than a crash.
- Deleting a document that is currently published removes it the same way as one that is only ingested or archived — state does not block deletion.
- Deleting a document removes all of its versions and draft content along with it; nothing is left behind that could still be found via search or listings.
- Deleting a document does not affect any other document, its own space, or sibling documents in the same space.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST show a delete action on the document detail page to the document's owner, space admins of the document's space, and platform admins.
- **FR-002**: System MUST hide the delete action from any user who is not the document's owner, a space admin of the document's space, or a platform admin.
- **FR-003**: System MUST require the user to explicitly confirm the deletion in a confirmation prompt before any data is removed, and MUST leave the document untouched if the user cancels.
- **FR-004**: Upon confirmed deletion, system MUST permanently remove the document, all of its versions, and any unpublished draft content associated with it.
- **FR-005**: System MUST remove a deleted document from search results and from its space's document listing immediately after deletion.
- **FR-006**: After a successful deletion, system MUST navigate the user away from the deleted document's page to a page that still exists (e.g., the document's former space).
- **FR-007**: System MUST reject deletion attempts from users who are not the document's owner, a space admin of the document's space, or a platform admin, regardless of how the request is made.
- **FR-008**: System MUST reject a deletion attempt for a document that no longer exists (already deleted) with a clear, non-crashing outcome.
- **FR-009**: System MUST clearly inform the user when a deletion attempt fails, distinguishing between a permission error and other failures.
- **FR-010**: System MUST record which user deleted a document and when, for audit purposes.

### Key Entities

- **Document**: The content record being removed. A deletion removes the document, its full version history, and any in-progress draft tied to it.
- **Deletion audit entry**: A record of who deleted a document and when, kept for accountability after the document itself is gone.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with permission can delete an unwanted document, from opening it to confirming removal, in under 15 seconds.
- **SC-002**: 100% of deletion attempts by users without permission are blocked, whether attempted through the interface or directly against the system.
- **SC-003**: 0% of confirmed deletions leave residual content (versions, drafts, or search entries) discoverable afterward.
- **SC-004**: 0% of accidental delete-action clicks result in data loss, because every deletion requires a separate explicit confirmation step.

## Assumptions

- Deletion is permanent (hard delete) — there is no "trash" or recovery mechanism to restore a deleted document after confirmation, matching the plain request for a delete button with no mention of recovery.
- Documents can be deleted regardless of their current state (ingested, published, or archived); no additional workflow (e.g., forced unpublish first) is required before deletion.
- "Space admin" refers to the existing space-level admin role already used elsewhere in the product (e.g., for space membership management); "platform admin" refers to the existing global admin flag on a user.
- The audit trail for deletions reuses the product's existing audit-record mechanism rather than introducing a new logging system.
