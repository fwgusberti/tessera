# Feature Specification: Enrollment Admin Role Assignment

**Feature Branch**: `032-enrollment-admin-role`

**Created**: 2026-06-22

**Status**: Draft

**Input**: User description: "When a user completes a company enrollment this user must become company admin"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Company Creator Receives Admin Role on Enrollment Completion (Priority: P1)

A user who goes through the company enrollment flow and creates a new company is automatically designated as the company's administrator the moment enrollment completes. No manual step, invitation, or separate role assignment is needed — the system recognizes the creator and elevates their access without any additional action.

**Why this priority**: Without this behavior, the company creator has no administrative control over their own organization immediately after setup. Every company must have at least one admin, and the creator is the natural, unambiguous candidate.

**Independent Test**: Can be fully tested by creating a new user account, completing enrollment with a new company, then verifying that the user's access level within that company is "admin" before any other action is taken.

**Acceptance Scenarios**:

1. **Given** a user completes the full company enrollment flow by creating a new company, **When** enrollment finishes, **Then** the user is automatically assigned the company admin role with no additional step required.
2. **Given** the user has just completed enrollment, **When** they access any company management area, **Then** all administrative capabilities are immediately available to them.
3. **Given** a second user later completes enrollment by joining an existing company via invitation, **When** enrollment finishes, **Then** the joining user is NOT granted admin privileges — they receive the standard member role.
4. **Given** enrollment is interrupted before completion (e.g., browser closed mid-flow), **When** the user returns and completes enrollment, **Then** the admin role is still assigned upon final completion.

---

### User Story 2 - Company Has At Least One Admin After Enrollment (Priority: P1)

Every company created through enrollment must immediately have exactly one administrator: its creator. The system must enforce that no newly created company exists in an admin-less state, even briefly.

**Why this priority**: An admin-less company cannot be managed, cannot approve new members, and cannot configure workspace settings. Ensuring the invariant holds at creation time prevents orphaned companies that require manual operator intervention.

**Independent Test**: Can be fully tested by creating a company via enrollment and immediately querying the company's member list to confirm exactly one member with admin role exists before any other action.

**Acceptance Scenarios**:

1. **Given** a company is created via enrollment, **When** the enrollment transaction completes, **Then** the company's member list contains exactly one member with the admin role (the creator).
2. **Given** any newly created company, **When** querying its member roles, **Then** the result always contains at least one admin — never zero.

---

### Edge Cases

- What happens when an enrollment is partially completed across sessions? The admin role must still be assigned upon the final completion step, regardless of how many sessions enrollment spans.
- What if the same user accidentally triggers enrollment twice (e.g., double-submit)? The system must be idempotent — the admin role is assigned once; duplicate enrollment attempts are rejected or no-op.
- What if the company creation step succeeds but role assignment fails? The system must treat these as a single atomic operation: if role assignment fails, the company creation must also be rolled back (or the error surfaced and the user retried) so no company exists without an admin.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST automatically assign the company admin role to the user who creates a company during the enrollment flow, at the moment enrollment is marked complete.
- **FR-002**: Role assignment and company creation MUST be treated as a single atomic operation — both succeed or both fail together.
- **FR-003**: The admin role assignment MUST require no manual action from the user or any operator; it MUST happen entirely in the background as part of enrollment completion.
- **FR-004**: The system MUST NOT assign the admin role to users who complete enrollment by joining an existing company (via invitation or domain match); those users MUST receive the standard member role.
- **FR-005**: The system MUST enforce that every company has at least one admin at all times, starting from the moment it is created.
- **FR-006**: Admin role assignment during enrollment MUST be idempotent — if enrollment completion is triggered more than once for the same user and company, the role assignment MUST NOT be duplicated or cause an error.
- **FR-007**: The system MUST make the admin role effective immediately upon enrollment completion, with no propagation delay before the user can exercise admin capabilities.

### Key Entities

- **Company**: An organization created during enrollment; has one or more members, each with a role.
- **Company Member**: The association between a user and a company, carrying a role (admin or member).
- **Enrollment**: The end-to-end flow a user goes through to set up their account and join or create a company; has a completion event that triggers role assignment.
- **Role**: The access level of a company member; "admin" grants full management control; "member" grants standard access.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of users who complete enrollment by creating a new company are immediately assigned the admin role — zero cases of a company creator left without admin access.
- **SC-002**: Every newly created company has exactly one admin at the moment of creation, with no window of time where the company has zero admins.
- **SC-003**: Admin capabilities are accessible to the creator within the same session that completes enrollment, with no page refresh or re-login required.
- **SC-004**: No user who joins an existing company through enrollment is erroneously granted admin access.
- **SC-005**: Duplicate enrollment completion attempts for the same user-company pair are handled without errors and without creating duplicate role records.

## Assumptions

- The enrollment flow already captures whether a user is creating a new company versus joining an existing one; this distinction is used to determine whether admin assignment applies.
- The system already has a concept of company membership and roles (admin vs. member) as established in the user roles feature.
- The admin role assigned during enrollment is the same company admin role already defined in the platform — no new role type is introduced.
- Users joining an existing company via invitation during enrollment follow the existing invitation-acceptance role assignment logic (not modified by this feature).
- Enrollment completion is a discrete, identifiable event in the system that can be extended to trigger the admin role assignment.
