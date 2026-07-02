# Feature Specification: Space Rename

**Feature Branch**: `049-space-rename`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "add space rename feature in spaces menu"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rename a space from the Spaces browser (Priority: P1)

A space administrator browsing the Spaces menu (the folder grid on the Spaces page and inside any space's folder view) wants to correct or update a space's display name without leaving the page — for example, fixing a typo or updating a name after a team reorg.

**Why this priority**: This is the entire feature. Without it, there is no rename capability at all.

**Independent Test**: From the Spaces page, open the actions for a space the user administers, choose "Rename", enter a new name, and confirm. The tile updates to show the new name immediately, and reloading the page shows the new name persisted.

**Acceptance Scenarios**:

1. **Given** a space admin is viewing the Spaces page folder grid, **When** they choose "Rename" on a space tile they administer and submit a valid new name, **Then** the tile's displayed name updates immediately and the change persists after a page reload.
2. **Given** a space admin opens the rename control, **When** they submit an empty name or a name that is only whitespace, **Then** the system rejects the change with a clear validation message and the space's name is unchanged.
3. **Given** a space admin opens the rename control, **When** they cancel without submitting, **Then** the space's name remains unchanged and no request is made.
4. **Given** a space admin renames a space, **When** the new name matches another space's name in the same company, **Then** the rename is still allowed (names are not required to be unique) and both spaces display their (possibly identical) names correctly.

---

### User Story 2 - Rename restricted to authorized users (Priority: P2)

A non-admin member (viewer or editor role on a space) browsing the Spaces menu should not be able to rename spaces they do not administer, preventing accidental or unauthorized changes to shared space names.

**Why this priority**: Protects data integrity and matches the existing permission model used for other space-management actions (e.g., "Set parent" is admin-only today), but the feature still delivers value even before this restriction is polished, since P1 already scopes the control to admins in the UI.

**Independent Test**: Log in as a user with viewer or editor access to a space and confirm no rename control is shown for that space; attempting the underlying rename request directly against the API for that space is rejected.

**Acceptance Scenarios**:

1. **Given** a user has viewer or editor (non-admin) access to a space, **When** they view that space's tile in the Spaces menu, **Then** no rename control is available for that space.
2. **Given** a user without admin access to a space attempts to rename it directly (bypassing the UI), **When** the request is processed, **Then** it is rejected and the space's name is unchanged.

---

### User Story 3 - Feedback on rename failure (Priority: P3)

A space admin who attempts a rename that fails (e.g., network error, server rejection) sees a clear error message and can retry, so the space name is never left in an inconsistent or unclear state.

**Why this priority**: Improves resilience and trust in the feature but is a refinement of the core P1 flow rather than a separate capability.

**Independent Test**: Simulate a failed rename request and confirm the UI surfaces an error message, keeps the rename control open with the attempted value, and leaves the original name displayed until the retry succeeds.

**Acceptance Scenarios**:

1. **Given** a rename request fails, **When** the failure response is received, **Then** the UI shows a clear error message and the space tile continues to display the original (pre-rename) name.
2. **Given** a rename request fails, **When** the admin corrects the input and resubmits, **Then** the retry follows the same success/failure flow as the original attempt.

---

### Edge Cases

- What happens when the new name exceeds the maximum allowed length? The system rejects the change with a validation message and the name is unchanged.
- What happens when two admins rename the same space at nearly the same time? The last successful write wins; each admin sees their own submission's outcome (success or failure) reflected in their session.
- What happens when a space is renamed while another user is viewing that space's folder page or breadcrumb? On their next data refresh (e.g., navigation or reload), they see the updated name; no requirement to push live updates to other open sessions.
- What happens if the admin submits the exact same name as the current one? The system accepts it as a no-op success (no error).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Spaces menu (Spaces page folder grid and space folder view) MUST provide a "Rename" control on each space tile that the current user administers.
- **FR-002**: The system MUST NOT display or otherwise expose the rename control for spaces the current user does not administer.
- **FR-003**: The rename control MUST let the user enter a new name pre-filled with the space's current name, and MUST provide explicit "Save" and "Cancel" actions.
- **FR-004**: The system MUST validate that the submitted name is non-empty (after trimming whitespace) and within the same length constraints already enforced when a space is created.
- **FR-005**: The system MUST reject rename attempts made by users without admin access to the target space, independent of whether the request originated from the UI.
- **FR-006**: On successful rename, the system MUST persist the new name and reflect it immediately in the Spaces menu without requiring a full page reload.
- **FR-007**: On failed rename (validation error, permission error, or server/network error), the system MUST leave the space's stored name unchanged and MUST present a clear error message to the user.
- **FR-008**: The system MUST allow duplicate space names within a company (name uniqueness is not required), consistent with existing space-creation behavior.
- **FR-009**: The system MUST record a rename action (actor, timestamp, affected space) in the platform's audit trail, as required for every state-changing administrative action.

### Key Entities

- **Space**: An existing entity representing a folder-like container of documents and sub-spaces; this feature adds the ability to change its display `name` attribute. No new entity is introduced.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A space admin can rename a space and see the updated name reflected in the Spaces menu in under 5 seconds, without navigating away from the page.
- **SC-002**: 100% of rename attempts by users without admin access to the target space are rejected.
- **SC-003**: 100% of rejected or failed rename attempts leave the original space name fully intact and visible to all users.
- **SC-004**: Users report no ambiguity about whether a rename succeeded or failed (validated via clear inline success/error feedback on every attempt).

## Assumptions

- "Spaces menu" refers to the existing Spaces browsing surfaces: the top-level Spaces page (folder grid) and the folder view shown when navigating into a space, both of which already render space tiles with admin-only actions (e.g., "Set parent").
- Rename authorization reuses the existing space-admin permission model already enforced for other space-management actions (e.g., setting a parent space), rather than introducing a new permission tier.
- Space name validation (non-empty, max length) reuses the same constraints already applied to the `name` field at space-creation time; no new validation rules are introduced.
- Space names are not required to be unique within a company today (creation does not enforce this), so rename does not introduce a uniqueness constraint either.
- Renaming does not affect a space's `slug`, hierarchy (`parent_space_id`), documents, or permissions — only the display `name` changes.
- No real-time push of renamed names to other users' already-open sessions is required; the next data fetch (navigation/reload) is sufficient.
