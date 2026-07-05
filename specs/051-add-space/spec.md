# Feature Specification: Add Space

**Feature Branch**: `051-add-space`

**Created**: 2026-07-03

**Status**: Draft

**Input**: User description: "create add space feature in spaces page"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a new top-level space from the Spaces page (Priority: P1)

A user browsing the top-level Spaces page (the folder grid) wants to create a brand-new space to organize documents for a team, project, or topic, without needing an administrator to set it up on their behalf.

**Why this priority**: This is the entire feature. Without it, spaces can only be created through an internal admin console, not by the people who actually organize their own work.

**Independent Test**: From the Spaces page, choose "Add Space", enter a name, and confirm. The new space appears as a tile in the folder grid immediately, and reloading the page shows it persisted. The creator can immediately open it, rename it, and manage its members.

**Acceptance Scenarios**:

1. **Given** a user with an active company is viewing the Spaces page folder grid, **When** they choose "Add Space", enter a valid name, and confirm, **Then** a new space tile appears in the folder grid immediately and the space still exists after a page reload.
2. **Given** the "Add Space" control is open, **When** the user submits an empty name or a name that is only whitespace, **Then** the system rejects the submission with a clear validation message and no space is created.
3. **Given** the "Add Space" control is open, **When** the user cancels without submitting, **Then** no space is created and no request is made.
4. **Given** a user creates a new space, **When** the name matches an existing space's name in the same company, **Then** creation still succeeds (names are not required to be unique) and both spaces are shown correctly.
5. **Given** a user successfully creates a space, **When** they open the new space right after creation, **Then** they have full administrative access to it (e.g., can rename it, manage its members, and set its parent) without any extra setup step.

---

### User Story 2 - Create a nested sub-space from within a space (Priority: P2)

A user browsing inside an existing space's folder view wants to create a new space that is automatically organized as a sub-space of the one they're currently viewing, so they don't have to create it separately and then move it into place.

**Why this priority**: Extends the core capability to the nested-space browsing experience users already rely on elsewhere in the Spaces menu; valuable, but the feature already delivers its main value via top-level creation (User Story 1) even without this.

**Independent Test**: Navigate into a space's folder view, choose "Add Space", enter a name, and confirm. The new space appears as a sub-space tile within that folder view immediately, and navigating to the top-level Spaces page confirms it is nested under the space it was created from.

**Acceptance Scenarios**:

1. **Given** a user is viewing a specific space's folder view, **When** they choose "Add Space" and submit a valid name, **Then** the new space is created as a sub-space nested under the space currently being viewed and appears in that folder view immediately.
2. **Given** a user creates a sub-space inside a space that is already at the maximum allowed nesting depth, **When** they submit the creation, **Then** the system rejects it with a clear message explaining the depth limit, and no space is created.

---

### User Story 3 - Clear feedback when creation fails (Priority: P3)

A user who attempts to create a space that fails (e.g., network error, server rejection) sees a clear error message and can retry, so it's never unclear whether the space was created.

**Why this priority**: Improves resilience and trust in the feature but is a refinement of the core creation flow rather than a separate capability.

**Independent Test**: Simulate a failed creation request and confirm the UI surfaces an error message, keeps the "Add Space" control open with the attempted name, and does not show a new tile in the folder grid.

**Acceptance Scenarios**:

1. **Given** a space creation request fails, **When** the failure response is received, **Then** the UI shows a clear error message, no new tile appears in the folder grid, and the attempted name remains available for editing.
2. **Given** a space creation request fails, **When** the user corrects the input and resubmits, **Then** the retry follows the same success/failure flow as the original attempt.

---

### Edge Cases

- What happens when the submitted name exceeds the maximum allowed length? The system rejects the creation with a validation message and no space is created.
- What happens when a user without an active company (e.g., not yet part of any company, or a company that is inactive/suspended) attempts to create a space? The "Add Space" control is unavailable, and any direct request is rejected.
- What happens if the user double-submits (e.g., clicks "Create" twice quickly)? Only one space is created; the duplicate submission is ignored or produces the same resulting space, not two.
- What happens when the user creates a space and then immediately navigates away before the confirmation appears? The space creation still completes in the background and the space is visible the next time the Spaces page is loaded.
- What happens when creating a sub-space inside a space the user does not have access to (e.g., a stale/expired view)? The system rejects the request as if the parent space were not found.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Spaces page top-level folder grid MUST provide an "Add Space" control that lets a user belonging to an active company create a new top-level space.
- **FR-002**: The "Add Space" control MUST let the user enter a name for the new space and MUST provide explicit "Create" and "Cancel" actions.
- **FR-003**: The system MUST validate that the submitted name is non-empty (after trimming whitespace) and within the same length constraints already enforced for space names elsewhere in the product.
- **FR-004**: On successful creation, the system MUST persist the new space, grant the creator full administrative access to it, and reflect it immediately in the Spaces page folder grid without requiring a full page reload.
- **FR-005**: A space's folder view MUST also provide an "Add Space" control that creates the new space as a sub-space nested under the space currently being viewed.
- **FR-006**: The system MUST reject a sub-space creation that would exceed the maximum nesting depth already enforced for the space hierarchy, with a clear message, regardless of whether the request originates from the UI or is made directly.
- **FR-007**: The system MUST reject space creation requests from users who do not belong to an active company, regardless of whether the request originates from the UI or is made directly.
- **FR-008**: On failed creation (validation error, permission error, or server/network error), the system MUST NOT create a partial or orphaned space and MUST present a clear error message to the user.
- **FR-009**: The system MUST allow duplicate space names within a company (name uniqueness is not required), consistent with existing space-management behavior.
- **FR-010**: The system MUST record a space-creation action (actor, timestamp, created space, and parent space if applicable) in the platform's audit trail.
- **FR-011**: The system MUST ensure every newly created space belongs to the creating user's own company; a user MUST NOT be able to create a space under another company.

### Key Entities

- **Space**: An existing entity representing a folder-like container of documents and sub-spaces, scoped to a company and optionally nested under a parent space. This feature adds a user-facing way to create new instances of it; no new entity or attribute is introduced.
- **Space Membership**: An existing entity linking a user to a space with a role. This feature relies on the existing behavior that the creator of a space is automatically granted the administrative role on it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can create a new space and see it appear in the Spaces page folder grid in under 5 seconds, without navigating away from the page.
- **SC-002**: 100% of empty, whitespace-only, or over-length name submissions are rejected without creating a space.
- **SC-003**: 100% of users who successfully create a space have full administrative control over it (rename, manage members, set parent) immediately, with no additional setup step.
- **SC-004**: 100% of sub-space creation attempts that would exceed the maximum nesting depth are rejected, and the existing hierarchy is left unchanged.
- **SC-005**: Users report no ambiguity about whether a creation attempt succeeded or failed (validated via clear inline success/error feedback on every attempt).

## Assumptions

- "Spaces page" refers to both the top-level Spaces page (folder grid) and the folder view shown when navigating into a space, consistent with how other space-management actions (e.g., rename) are already scoped across both surfaces.
- Any authenticated user who belongs to an active company can create a space, consistent with the existing permission model for space creation; this feature does not introduce a stricter creator-permission tier (e.g., company-admin-only).
- The creation form only asks the user for a space name. Any other technical attributes a space requires internally (e.g., an internal identifier derived from the name, or a default classification) are assigned automatically by the system and are not surfaced to the user at creation time; they can be adjusted later through existing space-management features if needed.
- Space names are not required to be unique within a company today, so creation does not introduce a uniqueness constraint.
- Creating a space from within a space's folder view nests the new space directly under the space being viewed, reusing the existing nested-space hierarchy rules (including maximum depth) rather than introducing new ones.
- No real-time push of newly created spaces to other users' already-open sessions is required; the next data fetch (navigation or reload) is sufficient for other users to see the new space.
