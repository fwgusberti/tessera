# Feature Specification: Add Space Membership (Frontend)

**Feature Branch**: `043-add-space-membership`

**Created**: 2026-06-30

**Status**: Draft

**Input**: User description: "Add front to add space membership"

## Clarifications

### Session 2026-06-30

- Q: Who should be allowed to call the new company-member search (the lookup the Add Member picker uses to find people by name/email)? → A: Scoped to the target space's admins — only callers who are already an admin of the specific space being modified can search the company directory for that add-member action, mirroring the existing rule that only space admins can call `POST /spaces/{id}/members`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add an Existing Company Member to a Space (Priority: P1)

A space admin is viewing the Space Members page and wants to grant a colleague access to the space. Instead of having to know and type that colleague's internal user ID, the admin searches for them by name or email from a list of people who already belong to the company, picks the right person, chooses a role, and confirms. The new member appears in the member list immediately with the assigned role.

**Why this priority**: This is the core gap today — the existing "Invite Member" control requires typing a raw user ID, which no admin realistically knows. Without a people-search, adding someone to a space is not practically usable. This story alone makes the feature deliver value.

**Independent Test**: As a space admin, open a space's Members page, open "Add Member", search for a company colleague who is not yet a member of the space by typing part of their name or email, select them, choose a role, submit, and confirm they appear in the member list with that role.

**Acceptance Scenarios**:

1. **Given** a space admin on the Space Members page, **When** they open "Add Member" and type part of a colleague's name or email, **Then** they see a list of matching company members who are not already in the space.
2. **Given** the admin has selected a matching colleague and a role, **When** they confirm the addition, **Then** the colleague is added to the space with the chosen role and appears in the member list without a page reload.
3. **Given** the admin types a search term that matches no company members, **When** results are shown, **Then** the system displays a clear "no matches" message instead of an empty silent list.
4. **Given** the admin types a search term that only matches people already in the space, **When** results are shown, **Then** those people are excluded from the results (they cannot be added twice).

---

### User Story 2 - Prevent and Explain Failed Additions (Priority: P2)

A space admin attempts to add a member but the action fails — the person was already added by someone else moments earlier, the admin's own permissions changed, or a network error occurs. The admin sees a clear, specific explanation rather than a silent failure or a generic error.

**Why this priority**: Without clear failure feedback, admins are left guessing why an action didn't take effect, leading to duplicate attempts or support requests. This depends on Story 1 existing first.

**Independent Test**: Trigger each failure path (duplicate add, insufficient permission, simulated network failure) against the Add Member flow and confirm a distinct, human-readable message is shown for each, and the form remains usable to retry.

**Acceptance Scenarios**:

1. **Given** the selected person was already added to the space by another admin in the meantime, **When** the current admin submits the form, **Then** they see a message indicating the person is already a member, and the member list refreshes to reflect reality.
2. **Given** a network or server error occurs while submitting, **When** the failure happens, **Then** the admin sees a retryable error message and the form keeps the admin's selections so they don't have to redo the search.
3. **Given** the signed-in user is not an admin of the space, **When** they view the Space Members page, **Then** no "Add Member" control is shown (consistent with existing role-based visibility on this page).

---

### Edge Cases

- What happens when the company has a very large number of members? The search MUST query incrementally (as the admin types) rather than loading the entire company roster into the browser at once.
- What happens if the admin searches before typing any characters? No results are fetched/shown until a minimum number of characters is entered, to avoid returning the entire company roster.
- What happens when a selected person leaves the company between selection and submission? The system MUST reject the addition with a clear "no longer eligible" message rather than silently succeeding or crashing.
- What happens when the admin closes the Add Member control mid-search? In-progress search state is discarded without side effects.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Space Members page MUST provide an "Add Member" control, visible only to admins of that space, replacing the existing raw-user-ID invite control.
- **FR-002**: The Add Member control MUST let the admin search for people by name or email, returning only members of the currently active company.
- **FR-002a**: The company-member search MUST be authorized server-side per target space: only a caller who is already an admin of that specific space (or a company admin) may query it for that space, matching the existing authorization rule for adding members. The restriction MUST NOT rely on UI-only hiding of the control.
- **FR-003**: Search results MUST exclude people who are already members of the current space.
- **FR-004**: The admin MUST be able to select exactly one searched person and assign them a role (admin, editor, or viewer) before confirming.
- **FR-005**: On confirmation, the system MUST add the selected person to the space with the chosen role and update the visible member list without requiring a page reload.
- **FR-006**: The system MUST show a distinct, human-readable error message for each known failure case: person already a member, insufficient permission, person no longer eligible (e.g., left the company), and generic/network failure.
- **FR-007**: The search MUST require a minimum of 2 characters typed before issuing a lookup, and MUST debounce input so a lookup is not fired on every keystroke.
- **FR-008**: When a search returns no eligible matches, the system MUST display a clear empty-results message distinguishing "no matches" from "not searched yet."
- **FR-009**: The Add Member control MUST NOT be shown to non-admin members of the space (consistent with current role-gated visibility of member-management actions).
- **FR-010**: After a failed submission, the form MUST retain the admin's current search term, selection, and role choice so the admin can retry without starting over.

### Key Entities *(include if feature involves data)*

- **Company Member**: A person who belongs to the active company, identified by name/email, searchable when adding them to a space. Backed by existing company membership data.
- **Space Membership**: The relationship between a person and a space, including their role (admin, editor, viewer) within that space. Already exists in the backend; this feature adds a discoverable way to create one.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A space admin can successfully add an existing company colleague to a space in under 30 seconds without needing to know or look up that colleague's internal identifier.
- **SC-002**: Search results for a partial name or email return within 1 second under normal conditions.
- **SC-003**: 100% of failure scenarios (duplicate member, permission denied, ineligible person, network error) produce a distinct message that correctly describes the cause — zero silent failures.
- **SC-004**: Zero instances of a person being added to a space twice through this flow.

## Assumptions

- "Company members" eligible to be added are people who already have a membership in the active company; inviting brand-new people who have never joined the company is out of scope for this feature (that is handled by the existing company invitation flow).
- The backend currently has no endpoint to search/list company members by name or email for this picker; this feature includes adding that lookup capability (scoped to the active company, returning only minimal identifying fields needed for selection: name, email, user id).
- The existing `POST /v1/spaces/{id}/members` endpoint and its permission rules (space admin or company admin required) are reused as-is for the actual add action; only the discovery/selection UX is new.
- Role choices remain the existing three space roles (admin, editor, viewer); no new roles are introduced.
- The current raw-user-ID "Invite Member" form is replaced by this flow rather than kept alongside it, since it is the actual user-facing entry point this feature targets.
