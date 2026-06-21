# Feature Specification: User Roles

**Feature Branch**: `024-user-roles`

**Created**: 2026-06-21

**Status**: Draft

**Input**: User description: "user roles"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administrators Manage Space Membership and Roles (Priority: P1)

A space administrator needs to control who can access a space and what they can do within it. They can invite existing registered users to a space, assign them a role (Admin, Editor, or Viewer), change roles, or remove members.

**Why this priority**: Without role-based access control at the space level, all authenticated users have equal power over every space, which undermines multi-tenant document governance and is the foundational capability for all other role scenarios.

**Independent Test**: Can be fully tested by inviting a user to a space with a specific role and verifying that user's capabilities match the assigned role — no other role story is required to validate this flow.

**Acceptance Scenarios**:

1. **Given** I am a space Admin and a registered user is not yet a member of my space, **When** I invite them by username or email and assign them a role, **Then** they appear in the space's member list with the correct role.
2. **Given** I am a space Admin and a member has the Viewer role, **When** I change their role to Editor, **Then** they immediately gain Editor capabilities within the space.
3. **Given** I am a space Admin, **When** I remove a member from the space, **Then** they lose all access to that space's documents.
4. **Given** I am a space member with the Editor or Viewer role (not Admin), **When** I attempt to change another member's role, **Then** the system rejects my action with a clear permission error.

---

### User Story 2 - Editors Create and Modify Documents (Priority: P2)

A user assigned the Editor role in a space can create, edit, and delete documents within that space. A Viewer in the same space can read those documents but cannot modify them.

**Why this priority**: Role differentiation between read-only and read-write access is the primary value proposition of the roles feature for end users; it must exist before fine-grained admin controls are needed.

**Independent Test**: Can be fully tested by creating two users in a space — one Editor, one Viewer — and verifying the Editor can create/edit/delete while the Viewer cannot, without needing global admin scenarios.

**Acceptance Scenarios**:

1. **Given** I have the Editor role in a space, **When** I create a new document in that space, **Then** it is saved and visible to all space members.
2. **Given** I have the Editor role in a space, **When** I edit or delete an existing document, **Then** the change is persisted and reflected immediately.
3. **Given** I have the Viewer role in a space, **When** I attempt to create, edit, or delete a document, **Then** the system prevents the action and displays a clear explanation that I lack edit permissions.
4. **Given** I have the Viewer role in a space, **When** I browse or search documents in that space, **Then** I can read all published documents normally.

---

### User Story 3 - Global Admins Govern the Platform (Priority: P3)

A platform-level Administrator can oversee all spaces and users: create or delete spaces, promote/demote other users to platform Admin, and intervene in any space regardless of space-level membership.

**Why this priority**: A global governance layer is necessary for platform operations and emergency access but is not needed for day-to-day document collaboration to function.

**Independent Test**: Can be tested by logging in as a global Admin, accessing a space the account was never explicitly invited to, and performing an administrative action (e.g., modifying a member list), verifying the action succeeds.

**Acceptance Scenarios**:

1. **Given** I am a global Admin, **When** I view any space, **Then** I can see and manage its member list even if I was not explicitly invited.
2. **Given** I am a global Admin, **When** I promote a regular user to global Admin, **Then** that user gains platform-wide administrative capabilities.
3. **Given** I am a regular user, **When** I attempt to access global admin controls, **Then** the system denies access and shows a permission error.
4. **Given** I am a global Admin, **When** I create a new space, **Then** I am automatically assigned as that space's Admin.

---

### Edge Cases

- What happens when the last Admin of a space tries to leave or be demoted? The system must prevent removing the final Admin from a space unless another Admin exists or the space is being deleted.
- What happens when a user is removed from a space while they have a document open for editing? Their next save attempt should fail with a clear error explaining they no longer have access.
- What happens when a user has both a global Admin role and a space-level Viewer role? The higher privilege (global Admin) governs — they retain full access.
- How are roles displayed to the user themselves? Members should be able to see their own role in any space they belong to.
- What happens to a user's space memberships when their account is deactivated? All active sessions must terminate and they must immediately lose access to all spaces.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST define three space-level roles: **Viewer** (read-only), **Editor** (create, edit, delete documents), and **Admin** (all Editor capabilities plus member management).
- **FR-002**: The system MUST define a **Global Admin** platform role that grants oversight of all spaces and the ability to manage platform-level settings and users.
- **FR-003**: A space Admin MUST be able to invite registered users to their space and assign them a role at invitation time.
- **FR-004**: A space Admin MUST be able to change any member's role within their space.
- **FR-005**: A space Admin MUST be able to remove any member (other than themselves, if they are the sole Admin) from their space.
- **FR-006**: The system MUST prevent all write and administrative actions on space content and membership by users who do not hold the required role.
- **FR-007**: The system MUST prevent a space from having zero Admins; attempts to demote or remove the last Admin without first designating a replacement MUST be rejected with a clear error message.
- **FR-008**: Every role-assignment or role-change action MUST be recorded in the audit log with the actor, target user, affected space, previous role, and new role.
- **FR-009**: Users MUST be able to view their own role in any space they belong to.
- **FR-010**: Global Admins MUST be able to act as implicit space Admins in any space on the platform.
- **FR-011**: When a user's account is deactivated, their access to all spaces MUST be revoked immediately without requiring manual removal from each space.

### Key Entities

- **Role** (space-level): An enumeration of `VIEWER`, `EDITOR`, `ADMIN` governing what a member can do within a specific space.
- **Platform Role**: An enumeration of `USER` (default) and `ADMIN` governing platform-wide capabilities independent of any single space.
- **Space Membership**: The association between a user and a space, carrying exactly one space-level role. A user can hold different space-level roles in different spaces.
- **Audit Log Entry**: A record of who changed what role for whom, in which space, and when.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All role-restricted actions (create, edit, delete, manage members) are correctly enforced 100% of the time — no unauthorized action succeeds.
- **SC-002**: A space Admin can complete the full invite-and-assign-role flow in under 60 seconds from opening the member management panel.
- **SC-003**: Role changes take effect immediately; a user whose role was changed does not need to log out and back in to experience their new permissions.
- **SC-004**: 100% of role-change events appear in the audit log within 5 seconds of the action completing.
- **SC-005**: The system correctly prevents the last-Admin-removal edge case in all code paths, with zero instances of a space being left without an Admin.
- **SC-006**: Users can identify their own role in any space in at most 2 navigation steps from the space home.

## Assumptions

- Tessera's existing JWT-based authentication system is already in place; this feature extends authorization on top of it.
- A user must be registered and have an active account before they can be invited to a space; inviting non-registered emails (pending invitations) is out of scope for this feature.
- The initial member of a space (its creator) is automatically assigned the space Admin role; this behavior was already defined in the spaces feature.
- A single user can be a member of multiple spaces with different roles in each.
- Role display and management will be accessible through the existing space settings or a dedicated "Members" section within each space — the exact navigation placement is a UX decision for planning.
- Soft-delete / deactivation of user accounts is assumed to be an existing or upcoming capability; this spec assumes the mechanism exists but specifies the role-revocation side-effect.
