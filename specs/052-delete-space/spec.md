# Feature Specification: Delete Space

**Feature Branch**: `052-delete-space`

**Created**: 2026-07-05

**Status**: Draft

**Input**: User description: "Add deletion of a space in spaces page. A Space deletion should delete ists content and also child spaces and documents. The space deletion should ask for user confirmation and autentication"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin permanently removes a space and everything in it (Priority: P1)

A user who administers a space (for example, a team lead cleaning up a finished project) wants to permanently remove that space along with all of its documents and any nested sub-spaces beneath it. They trigger a delete action from the spaces page, confirm they understand the scope of what will be removed, then re-enter their account password to verify their identity before the deletion actually happens.

**Why this priority**: This is the core capability being requested — without it, nothing else in this feature has value. It covers the primary case of an admin cleaning up a space they control.

**Independent Test**: Can be fully tested by logging in as a user with the ADMIN role on a space that has child spaces and documents, triggering delete, confirming the prompt, re-entering the correct password, and verifying the space, its descendants, and all their documents no longer appear anywhere in the system.

**Acceptance Scenarios**:

1. **Given** a signed-in user has the ADMIN role on a space, **When** they view the spaces page, **Then** they see a delete action for that space.
2. **Given** the admin clicks delete, **When** a confirmation prompt appears describing what will be permanently removed (child spaces and documents), and they confirm, **Then** they are prompted to re-enter their account password.
3. **Given** the admin enters their correct password after confirming, **When** they submit it, **Then** the space, all of its descendant spaces at every depth, and all documents contained anywhere in that subtree are permanently removed, and the user is taken to a page that still exists.
4. **Given** the deleted space had multiple child spaces and documents spread across them, **When** deletion completes, **Then** none of those spaces or documents can be found via search, listings, or direct navigation.

---

### User Story 2 - Incorrect password blocks the deletion (Priority: P2)

A user who triggers a space deletion and confirms intent does not remember their current password correctly, or wants to change their mind after seeing the scope of the deletion.

**Why this priority**: A destructive, cascading action like this needs a real safety net beyond a single click; verifying identity and allowing cancellation at any point protects against accidental or coerced data loss.

**Independent Test**: Can be fully tested by triggering delete, confirming the prompt, entering an incorrect password, and verifying nothing was deleted; then repeating and cancelling instead, and verifying the same.

**Acceptance Scenarios**:

1. **Given** the confirmation step has been accepted, **When** the user submits an incorrect password, **Then** the deletion does not occur, a clear error is shown, and the user may retry or cancel.
2. **Given** the user cancels at the confirmation step or at the password step, **When** they do so, **Then** the space and everything in it remain completely untouched and accessible as before.

---

### User Story 3 - Non-admins cannot delete a space (Priority: P3)

A user with EDITOR or VIEWER access to a space, or a user with no relationship to it at all, must not be able to delete it, whether through the interface or by attempting the underlying request directly.

**Why this priority**: Enforcing this boundary protects every other space in the system from unauthorized destruction; it's what makes the delete capability safe to ship at all.

**Independent Test**: Can be fully tested by logging in as a user with EDITOR or VIEWER access (not ADMIN) on a space, verifying no delete action is visible, and confirming a direct deletion request for that space is rejected.

**Acceptance Scenarios**:

1. **Given** a signed-in user has EDITOR or VIEWER access (not ADMIN) on a space, **When** they view the spaces page, **Then** no delete action is shown for that space.
2. **Given** a user without ADMIN access on a space attempts a deletion request directly, **When** the request is processed, **Then** it is rejected and nothing is deleted.

---

### Edge Cases

- Deleting a space with nested sub-spaces cascades through every descendant at any depth, not just direct children.
- Deleting a space removes every document contained in it and in all of its descendants, including each document's version history and any in-progress drafts, matching how a single document delete already behaves.
- Deleting a space also removes all membership grants tied to that space and to each of its descendants.
- An admin of the top-level space being deleted does not need a separate ADMIN grant on each individual descendant space in order for the cascade to proceed — administering the subtree root is sufficient.
- Two admins attempt to delete the same space at nearly the same time; whichever request completes first succeeds, and the second request fails gracefully with a "no longer exists" outcome rather than an error or partial deletion.
- Deleting the last remaining space in a company is allowed; the company is simply left with no spaces until a new one is created.
- A deletion request that passes confirmation but fails password verification leaves the space and all of its content completely intact.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST show a delete action for a space, on the spaces page, only to users who hold the ADMIN role on that specific space (or an existing platform admin).
- **FR-002**: System MUST hide the delete action from any user who does not hold the ADMIN role on that space and is not a platform admin.
- **FR-003**: System MUST require the user to explicitly confirm the deletion in a prompt that communicates the destructive, cascading scope (that child spaces and documents will also be removed) before proceeding.
- **FR-004**: After the user confirms intent, system MUST require them to re-enter their current account password and verify it server-side before the deletion is executed.
- **FR-005**: If password verification fails, system MUST NOT delete anything, MUST show a clear error, and MUST allow the user to retry or cancel.
- **FR-006**: Upon successful confirmation and password verification, system MUST permanently delete the target space, every descendant space at every depth beneath it, and every document (with all versions and drafts) contained anywhere in that subtree.
- **FR-007**: System MUST remove all space membership records tied to the deleted space and to each of its deleted descendants.
- **FR-008**: System MUST remove all deleted documents from search results and from any space's document listing immediately after deletion.
- **FR-009**: After a successful deletion, system MUST navigate the user to a page that still exists (e.g., the deleted space's former parent, or the top-level spaces page if it was a root space).
- **FR-010**: System MUST reject deletion attempts from any user who does not hold the ADMIN role on the target space and is not a platform admin, regardless of how the request is made.
- **FR-011**: System MUST reject a deletion attempt for a space that no longer exists (already deleted) with a clear, non-crashing outcome.
- **FR-012**: System MUST record an audit entry capturing who deleted the space, when, and the scope of what was removed (at minimum, the number of descendant spaces and documents deleted).
- **FR-013**: If the user cancels at the confirmation step or at the password step, system MUST leave the space and all of its content completely untouched.

### Key Entities

- **Space**: The hierarchy node being removed, along with every descendant space beneath it in the nesting tree.
- **Document**: Content records living inside the deleted space or any of its descendants; each is removed along with its full version history and any unpublished drafts.
- **Space Membership**: Access grants tied to the deleted space or its descendants; removed as part of the cascade so no dangling access records remain.
- **Deletion audit entry**: A record of who deleted a space, when, and how much content (descendant spaces and documents) was removed, kept for accountability after the space itself is gone.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An admin who knows their password can delete a space, from opening the action to completion, in under 30 seconds.
- **SC-002**: 100% of deletion attempts by users without ADMIN access on the target space are blocked, whether attempted through the interface or directly against the system.
- **SC-003**: 0% of confirmed deletions leave residual spaces, documents, versions, drafts, memberships, or search entries discoverable afterward.
- **SC-004**: 0% of deletions complete without a correct password verification immediately preceding them.
- **SC-005**: 0% of single accidental clicks on the delete action result in data loss, because every deletion requires both an explicit confirmation and a successful password re-entry.

## Assumptions

- "Authentication" in the request is interpreted as requiring the acting user to re-enter their current account password, verified against their stored credentials, as a distinct step performed after the confirmation prompt — reflecting the request's explicit mention of both "confirmation" and "authentication" as two separate safeguards for this irreversible, cascading action.
- Deletion is a hard delete with no trash or recovery mechanism, consistent with the existing document deletion feature.
- "Content" of a space means all documents directly in it (with their versions and drafts); deleting a space cascades to remove every descendant sub-space at any depth and everything contained within them, recursively.
- Only a user holding the ADMIN space-role on the space being deleted, or an existing platform admin, may delete it; that admin grant on the subtree root is sufficient to authorize removing all of its descendants, without requiring separate ADMIN grants on each one individually.
- There is no minimum-space requirement for a company — it may end up with zero spaces after a deletion, and a new space can be created afterward.
- Deleted content is removed from search indexes immediately, matching existing document-deletion behavior.
