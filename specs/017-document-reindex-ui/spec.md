# Feature Specification: Document Reindex UI

**Feature Branch**: `017-document-reindex-ui`

**Created**: 2026-06-20

**Status**: Draft

**Input**: User description: "Add ui to /v1/documents/{document_id}/reindex"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Owner Triggers Reindex (Priority: P1)

A document owner views a published document and notices search results are stale or missing. They click a "Reindex" button on the document detail page to trigger re-indexing of the document so it appears correctly in search results.

**Why this priority**: This is the core action the feature enables. The reindex endpoint already exists; this story closes the gap between the API capability and user access.

**Independent Test**: Can be fully tested by loading a published document as its owner and clicking the Reindex button — the button dispatches the task, shows a success message, and the document becomes searchable.

**Acceptance Scenarios**:

1. **Given** a user is authenticated as the document owner and the document is in "published" state, **When** they view the document detail page, **Then** a "Reindex" button is visible in the document header actions area.
2. **Given** the user clicks the "Reindex" button, **When** the request succeeds, **Then** the button shows a loading state during the call and a success confirmation ("Reindex queued") replaces or accompanies it afterward.
3. **Given** the user clicks the "Reindex" button, **When** the request fails, **Then** an inline error message is displayed and the button returns to its clickable state.

---

### User Story 2 - Admin Triggers Reindex on Any Document (Priority: P2)

An administrator views any published document (not necessarily their own) and can reindex it to repair search indexing without needing to own the document.

**Why this priority**: Admins need the same control as owners; the API endpoint already grants admin access. This story simply ensures the button is visible to admins under the same conditions.

**Independent Test**: Can be fully tested by logging in as an admin, opening a published document owned by another user, and verifying the Reindex button is visible and functional.

**Acceptance Scenarios**:

1. **Given** a user with admin role views any published document, **When** they view the document detail page, **Then** the "Reindex" button is visible regardless of document ownership.
2. **Given** the admin clicks the "Reindex" button, **When** the request succeeds, **Then** the same success confirmation shown to owners is displayed.

---

### User Story 3 - Non-Owner Non-Admin Cannot Reindex (Priority: P2)

A regular user viewing a document they do not own sees no reindex control, preventing unauthorized access to the reindex action.

**Why this priority**: The API already enforces the 403 at the server but the UI should not surface an action the user cannot perform.

**Independent Test**: Can be fully tested by logging in as a non-owner, non-admin user, viewing a published document, and confirming no Reindex button is shown.

**Acceptance Scenarios**:

1. **Given** an authenticated user who is neither the document owner nor an admin views a published document, **When** the document detail page loads, **Then** no "Reindex" button is visible.

---

### User Story 4 - Reindex Unavailable for Non-Published Documents (Priority: P3)

A user viewing an ingested or archived document does not see a reindex button, since only published documents can be reindexed.

**Why this priority**: The API returns a 400 for non-published documents; hiding the button prevents a confusing, always-failing action from being presented.

**Independent Test**: Can be tested by viewing an ingested document as its owner and confirming the Reindex button is absent.

**Acceptance Scenarios**:

1. **Given** the document is in "ingested" or "archived" state, **When** the document detail page loads, **Then** no "Reindex" button is visible regardless of user role.

---

### Edge Cases

- What happens when the reindex button is clicked twice quickly? The button should be disabled while the request is in-flight to prevent duplicate submissions.
- What if the user's session expires mid-reindex call? The existing auth refresh mechanism handles this transparently; if it fails, the error state is shown.
- What if the document transitions state between page load and button click? The server returns a 400; the UI should surface that error message to the user.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The document detail page MUST display a "Reindex" button for published documents when the current user is the document owner or has admin role.
- **FR-002**: The "Reindex" button MUST NOT be visible for documents in "ingested" or "archived" state.
- **FR-003**: The "Reindex" button MUST NOT be visible to authenticated users who are neither the document owner nor an admin.
- **FR-004**: When clicked, the "Reindex" button MUST call `POST /v1/documents/{document_id}/reindex` and disable itself during the in-flight request.
- **FR-005**: On a successful response, the system MUST show an inline confirmation message ("Reindex queued") near the button, auto-dismiss it after approximately 3 seconds, and re-enable the button so the user may trigger reindexing again in the same session.
- **FR-006**: On a failed response, the system MUST display the error message returned by the server inline and re-enable the button.
- **FR-007**: The reindex action MUST NOT trigger a full page reload; the document state displayed should remain unchanged after reindexing.

### Key Entities

- **Document**: The target entity with `id`, `state`, `owner_user_id`, and `current_version_id` attributes relevant to this feature.
- **AuthUser**: The currently authenticated user, identified by `id` and `isAdmin` flag, used to determine button visibility.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The "Reindex" button is visible to document owners and admins on published documents within the current page load — no additional navigation required.
- **SC-002**: A user can trigger reindexing in under 3 clicks from the document detail page (one click on the button).
- **SC-003**: The button provides visual feedback (loading state) within 100 ms of being clicked, so users never see a frozen UI.
- **SC-004**: The success or error outcome is communicated to the user within 5 seconds of clicking (bounded by network latency to the server).
- **SC-005**: Zero cases where a non-owner, non-admin user can click a Reindex button (button never rendered for unauthorized users).

## Clarifications

### Session 2026-06-20

- Q: After a successful reindex call, should the "Reindex queued" success message auto-dismiss and re-enable the button, or lock the button permanently until page refresh? → A: Show "Reindex queued" for ~3 seconds, then auto-dismiss and re-enable the button (Option B).

## Assumptions

- The document detail page (`/documents/[id]`) is the correct location for the Reindex button; no new page or route is required.
- The currently authenticated user's `id` and `isAdmin` status are available from the existing auth context without additional API calls.
- The `owner_user_id` field is present in the document payload already returned by the existing `GET /v1/documents/{id}` endpoint.
- The reindex operation is asynchronous; the UI does not need to poll for completion — the "queued" confirmation is sufficient.
- Mobile-specific layout is out of scope; the button follows the same responsive patterns as the existing "Publish" button.
