# Feature Specification: Human-Readable Member Identity in User Management

**Feature Branch**: `065-fix-member-display`

**Created**: 2026-07-12

**Status**: Draft

**Input**: User description: "user management page shows user is and email is empty. that way is not really human manageable. fix that"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Space members are identified by name and email (Priority: P1)

A space administrator opens the members panel of a space to see who has access. Today each row shows an opaque system identifier (a long random string) as the member's name, and the email line is missing entirely. The administrator cannot tell who anyone is. After this fix, every member row shows the person's display name with their email address beneath it — the same presentation already used on the company Users page.

**Why this priority**: This is the reported defect. A member list made of random identifiers is unusable for its core purpose — knowing who has access — and makes every management action (role change, removal) a guess.

**Independent Test**: Open any space's members panel as an admin and verify each row shows a human-readable name and email instead of a system identifier. Delivers immediate value on its own.

**Acceptance Scenarios**:

1. **Given** a space with members who have display names and emails on file, **When** an administrator views the space members list, **Then** each row shows the member's display name with their email address beneath it.
2. **Given** the same space members list, **When** any member row renders, **Then** no raw system identifier is displayed anywhere in the row.
3. **Given** a member whose display name is blank, **When** the list renders, **Then** that member's email address is shown as their primary label (never the system identifier).

---

### User Story 2 - Administrators can confidently act on the right person (Priority: P2)

An administrator needs to change a member's role or remove them from a space. Because each row now clearly identifies the person, the administrator can confirm they are acting on the intended member before a change takes effect.

**Why this priority**: Management actions are destructive or permission-changing; acting on an unidentifiable row risks removing or demoting the wrong person. This depends on Story 1 being in place.

**Independent Test**: As a space admin, change a member's role and remove a member, confirming in each case the row being acted on displays the person's name and email.

**Acceptance Scenarios**:

1. **Given** a space members list with readable identities, **When** an administrator changes a member's role, **Then** the row where the change is made displays that member's name and email throughout the interaction.
2. **Given** two members with the same display name, **When** the list renders, **Then** their distinct email addresses allow the administrator to tell them apart.

---

### User Story 3 - Member identity is consistent across all management surfaces (Priority: P3)

A user who manages people from different screens (company Users page, space members panel, member search when adding someone) sees the same identity presentation everywhere: display name as the primary label, email as the secondary line.

**Why this priority**: Consistency reduces confusion but the primary defect is already resolved by Stories 1–2; this story sweeps the remaining member-listing surfaces for the same problem.

**Independent Test**: Visit each surface that lists or references members and verify none of them ever shows a raw system identifier as a person's label.

**Acceptance Scenarios**:

1. **Given** any screen that lists members or references a person, **When** it renders, **Then** the person is labeled by display name (or email as fallback), never by a system identifier.

---

### Edge Cases

- Member with a blank display name: email is shown as the primary label.
- Member with both display name and email missing (data anomaly): a neutral placeholder label (e.g., "Unknown user") is shown rather than the raw identifier.
- Two members with identical display names: the email line disambiguates them.
- Very long names or emails: the row remains readable and does not break the table layout.
- A viewer-level member (non-admin) opening the members list sees the same readable identities (read-only).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The space members list MUST display each member's display name as the primary label and their email address as a secondary line.
- **FR-002**: The system MUST provide the display name and email of each member wherever a member list is served to the interface, so the interface never has to fall back to a system identifier.
- **FR-003**: When a member's display name is blank, the interface MUST show their email address as the primary label.
- **FR-004**: When both display name and email are unavailable, the interface MUST show a neutral placeholder label; raw system identifiers MUST never be rendered as a person's label.
- **FR-005**: Member management actions (role change, removal) MUST remain fully functional and continue to target the correct member after the identity display change.
- **FR-006**: All member-listing surfaces MUST present member identity consistently (name primary, email secondary).
- **FR-007**: Member identity data MUST only be revealed to users already authorized to view the member list in question; the fix MUST NOT widen who can see member information, and members of one company MUST never see another company's member identities.

### Key Entities

- **Member**: A person's participation in a space or company; carries a role and points to a user.
- **User identity**: The human-readable facts about a person — display name and email — that must accompany every member wherever members are listed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of rows in the space members list show a human-readable label (name or email); zero rows show a system identifier.
- **SC-002**: An administrator can identify a specific person in a members list of 20 people in under 5 seconds without leaving the page or cross-referencing identifiers.
- **SC-003**: Role changes and member removals performed from the members list succeed at the same rate as before the change (no regression in management actions).
- **SC-004**: Every member-listing surface in the product presents identity in the same name-plus-email format.

## Assumptions

- The reported page is the space members panel, where members currently render with a system identifier as the label and no email; the company Users page already shows name and email correctly and serves as the presentation reference.
- Every registered user has an email on file; display names may occasionally be blank, so email is an acceptable fallback label.
- No new permissions are introduced: whoever can view a members list today is already entitled to see those members' names and emails (as evidenced by the company Users page and member search, which already reveal them to the same audiences).
- Sorting the members list by display name (alphabetical) is the expected default ordering, matching the company Users page.
