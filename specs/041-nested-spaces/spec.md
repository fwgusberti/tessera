# Feature Specification: Nested Spaces

**Feature Branch**: `041-nested-spaces`

**Created**: 2026-06-30

**Status**: Draft

**Input**: User description: "Create nested spaces feature. the child space inherits permission from parent space. Child space permission does not affect parent permission"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse Inherited Child Spaces (Priority: P1)

A user who is a member of a parent space can automatically access all child spaces under that parent without needing to be explicitly added to each one.

**Why this priority**: This is the core value proposition of nested spaces — reducing administrative overhead by propagating access downward through the hierarchy.

**Independent Test**: A user with parent space access opens a child space and can view its contents without any separate membership grant.

**Acceptance Scenarios**:

1. **Given** a user is a member of "Engineering" space, **When** "Frontend" is created as a child of "Engineering", **Then** the user can access "Frontend" without any additional membership action.
2. **Given** a user is a member of "Engineering" which has a child "Frontend" which has a child "React", **When** the user navigates to "React", **Then** access is granted through the inherited chain.
3. **Given** a user has no membership in "Engineering" or its children, **When** the user attempts to access "Frontend" (child of "Engineering"), **Then** access is denied.

---

### User Story 2 - One-Way Permission Isolation (Priority: P1)

A user who is explicitly added to a child space does not gain access to the parent space or any sibling spaces.

**Why this priority**: Without upward isolation, adding a contractor to a project sub-space would unintentionally expose all parent and sibling spaces — a significant security concern.

**Independent Test**: A user added only to a child space can access that child space but receives a denial when attempting to access the parent.

**Acceptance Scenarios**:

1. **Given** a user is a member of "Frontend" (child of "Engineering"), **When** the user attempts to access "Engineering" (the parent), **Then** access is denied.
2. **Given** a user is a member of "Frontend", **When** the user attempts to access "Backend" (a sibling child of "Engineering"), **Then** access is denied.
3. **Given** a user is a member of "Frontend", **When** viewing their space list, **Then** only "Frontend" appears — not "Engineering" or other spaces they were not added to.

---

### User Story 3 - Organize Spaces into a Hierarchy (Priority: P2)

A space administrator can designate any space as a child of another space within the same company, creating a meaningful organizational hierarchy.

**Why this priority**: The hierarchy must be constructible before permission inheritance has value. Setting up the structure is a prerequisite for the access model.

**Independent Test**: An admin sets a parent on a space and the system reflects the parent-child relationship immediately.

**Acceptance Scenarios**:

1. **Given** an admin with access to both "Engineering" and "Frontend" spaces, **When** the admin sets "Engineering" as the parent of "Frontend", **Then** the relationship is saved and "Frontend" appears nested under "Engineering".
2. **Given** an admin attempts to set a space as its own parent, **When** the action is submitted, **Then** the system rejects it with a clear explanation.
3. **Given** an admin attempts to create a circular chain (A → B → A), **When** the action is submitted, **Then** the system rejects it with a clear explanation.
4. **Given** an admin removes the parent from a child space, **When** the action is confirmed, **Then** the space becomes a root space and retains its direct members without change.

---

### User Story 4 - Navigate the Space Hierarchy (Priority: P3)

Users can browse the hierarchy of spaces they have access to, seeing parent and child relationships clearly in the interface.

**Why this priority**: Navigation is a usability enhancement on top of the core permission model — valuable but not blocking the primary access control value.

**Independent Test**: A user with mixed direct and inherited access sees correctly nested spaces in the space listing.

**Acceptance Scenarios**:

1. **Given** a user has access to "Engineering" (with children "Frontend" and "Backend"), **When** the user views the space list, **Then** "Frontend" and "Backend" appear nested under "Engineering".
2. **Given** a user has access to "Frontend" (child) but not "Engineering" (parent), **When** the user views the space list, **Then** "Frontend" appears at the root level of their visible spaces with a breadcrumb indicating its parent path.
3. **Given** a user has access to a space three levels deep, **When** viewing that space, **Then** the full ancestor breadcrumb trail is visible.

---

### Edge Cases

- What happens when a parent space is deleted? Child spaces become root-level spaces; their direct memberships and contents are preserved without change.
- What happens when a child space is moved to a different parent? Access inherited from the old parent is revoked immediately; access inherited from the new parent is granted immediately — the transition is atomic.
- What happens when a space would exceed the maximum nesting depth of 10 levels? The system rejects the parent assignment with a clear message.
- What happens if a space from a different company is specified as a parent? The system rejects it — cross-company parent assignments are prohibited.
- How does the system handle a user whose parent-space membership is revoked? Access to all child spaces inherited through that parent is immediately revoked; only direct memberships to child spaces remain valid.
- What is the behavior for a space that is both directly joined and inherited? The more permissive result applies — the user retains access via either path.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A space MUST be able to designate at most one other space within the same company as its parent.
- **FR-002**: When a user has access to a space, they MUST automatically have access to every space in that space's descendant chain (children, grandchildren, and deeper), inheriting the same role level they hold in the ancestor space (e.g., an admin in the parent inherits admin in the child; a viewer inherits viewer).
- **FR-003**: A user's membership in a child space MUST NOT grant access to the parent space or any sibling spaces.
- **FR-004**: The system MUST prevent circular parent-child chains (e.g., A → B → A is rejected).
- **FR-005**: The system MUST prevent a space from being set as its own parent.
- **FR-006**: The system MUST enforce a maximum nesting depth of 10 levels.
- **FR-007**: Parent-child assignments MUST be confined to spaces within the same company; cross-company assignments are prohibited.
- **FR-008**: When a parent space is deleted, all child spaces MUST become root-level spaces and retain their existing direct memberships and contents.
- **FR-009**: The effective access check for any space MUST traverse the full ancestor chain and grant access if the requesting user holds membership in any ancestor.
- **FR-010**: To set, change, or remove a space's parent, the acting user MUST hold the space administrator role in BOTH the child space and the intended parent space. Removing a parent (making a space a root) requires admin in the child space only.
- **FR-011**: The space listing MUST reflect the hierarchical structure, showing child spaces nested under their parents for users who have access to both.
- **FR-012**: When a user can see a child space but not its parent, the UI MUST display the ancestor path as a breadcrumb for context without granting access to the parent.
- **FR-013**: Revoking a user's membership from a parent space MUST immediately revoke any access the user had to descendant spaces solely through that parent.

### Key Entities

- **Space**: An organizational container belonging to a company. Gains an optional `parent_space` reference pointing to another space within the same company. A space with no parent is a root space.
- **Space Hierarchy**: The tree formed by parent-child relationships among spaces in a company. A space may have many children but only one parent. Depth is bounded at 10 levels.
- **Effective Membership**: The combined set of spaces a user can access, derived from their direct memberships plus all descendant spaces of those memberships. The effective role in an inherited space matches the user's role in the nearest ancestor where they hold a direct membership.
- **Ancestor Chain**: The ordered path from a given space up through its parent, grandparent, and further ancestors until reaching a root space.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user gains access to a newly created child space instantly upon the parent-child relationship being established — no additional admin action required.
- **SC-002**: A user explicitly added only to a child space is denied access to the parent and sibling spaces 100% of the time.
- **SC-003**: Space hierarchies of up to 10 levels are supported and all access checks complete within the same response-time envelope as flat-space access checks.
- **SC-004**: Circular-chain and self-parent attempts are rejected 100% of the time with a user-understandable explanation.
- **SC-005**: Revoking a user's parent-space membership removes their inherited access to all child spaces within one request/response cycle. Reassigning a child space to a new parent also updates all inherited access atomically within the same cycle.
- **SC-006**: Admins can restructure the hierarchy (set, change, or remove a parent) without disrupting existing direct memberships or space contents.

## Clarifications

### Session 2026-06-30

- Q: When a user inherits access to a child space through their parent-space membership, what role level do they hold in the child? → A: Same role as in parent (admin stays admin, member stays member, viewer stays viewer).
- Q: When a child space is reassigned to a different parent, when does inherited access update? → A: Immediately — access via the old parent is revoked and access via the new parent is granted atomically at the moment the reassignment is saved.
- Q: To set space B as a child of space A, must the admin hold admin role in both spaces or only in space B? → A: Admin in both — must hold admin role in the child space AND the intended parent space.

## Assumptions

- Maximum nesting depth is set at 10 levels; this is sufficient for any realistic organizational hierarchy and limits query complexity.
- Setting or changing a space's parent requires admin role in both the child space and the target parent space. Removing a parent (promoting to root) requires admin in the child space only.
- When a parent space is deleted, children are promoted to root level rather than being cascade-deleted, to avoid unintended data loss.
- Mobile and API consumers will apply the same permission model; there is no separate mobile-only behavior.
- The existing `SpaceMembership` model and role system remain unchanged; the nested spaces feature adds inheritance on top of, not instead of, direct membership.
- A user who holds both a direct membership in a child space AND inherits access through a parent retains access via either path independently; revoking one does not revoke the other.
