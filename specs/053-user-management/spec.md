# Feature Specification: Company User Management Page

**Feature Branch**: `053-user-management`

**Created**: 2026-07-05

**Status**: Draft

**Input**: User description: "create an user management page for company admins. Need to have a list of users in the company and its role. Nothing more, for now"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin views the company's users and their roles (Priority: P1)

A company administrator opens a dedicated user management page and sees every person who belongs to their company, along with the role each person holds in that company (administrator or member). This gives the admin a single, authoritative view of who has access to the company and at what level.

**Why this priority**: This is the entire feature. Without it there is no way for an admin to see the roster of their company at a glance. It is independently valuable and delivers the complete requested capability on its own.

**Independent Test**: Sign in as a company admin, open the user management page, and confirm the page lists exactly the members of that company, each shown with their name/identifier and their company role. No further action is required to demonstrate value.

**Acceptance Scenarios**:

1. **Given** an admin of a company that has several members with mixed roles, **When** they open the user management page, **Then** every member of that company is listed, each with their role shown as either administrator or member.
2. **Given** an admin whose company has exactly one member (themselves), **When** they open the page, **Then** they see a single entry — themselves — marked as administrator.
3. **Given** an admin viewing the page, **When** the list is displayed, **Then** each entry clearly identifies the person (e.g., name and/or email) so the admin can tell members apart.

---

### User Story 2 - Access is restricted to company administrators (Priority: P1)

Only administrators of a company may view its user management page. A non-admin member who attempts to reach the page is prevented from seeing the roster.

**Why this priority**: The page exposes the full membership of a company, which is administrative information. Allowing ordinary members or outsiders to view it would be an access-control and privacy problem, so the restriction is as critical as the listing itself.

**Independent Test**: Attempt to open the user management page while signed in as a non-admin member of the company and confirm access is refused; then repeat as an admin and confirm access is granted.

**Acceptance Scenarios**:

1. **Given** a user who is a non-admin member of a company, **When** they attempt to open the user management page, **Then** they are denied access and do not see the member roster.
2. **Given** an unauthenticated visitor, **When** they attempt to open the user management page, **Then** they are not shown any company membership data.

---

### User Story 3 - The list is scoped to the admin's own company (Priority: P1)

An admin only ever sees the users of the company they are currently acting within. Members of other companies never appear, even if the admin belongs to more than one company.

**Why this priority**: Tessera is multi-tenant, and showing one company's members to another company is a cross-tenant data leak. Correct scoping is a non-negotiable security property of this page.

**Independent Test**: As an admin of Company A whose account also exists in Company B, open the user management page with Company A active and confirm only Company A's members appear; switch the active company to Company B and confirm only Company B's members appear.

**Acceptance Scenarios**:

1. **Given** an admin whose account is associated with two different companies, **When** they view the user management page with one company active, **Then** only that active company's members are listed.
2. **Given** an admin of Company A, **When** the page loads, **Then** no member belonging solely to any other company is ever displayed.

---

### Edge Cases

- **Company with a single member**: The page still renders and shows the sole member (the admin) rather than appearing empty or broken.
- **Member with missing display information**: If a user has no display name, the page falls back to a stable identifier (e.g., email) so no row is blank or unidentifiable.
- **Non-admin or unauthenticated access attempt**: The page never partially reveals the roster; access is refused cleanly.
- **Large membership**: A company with many members remains readable and usable (the list does not become unnavigable). Exact handling of very large lists is out of scope for this first version beyond remaining functional.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a dedicated user management page reachable by a company administrator.
- **FR-002**: The page MUST display a list of all users who are members of the administrator's active company.
- **FR-003**: Each listed user MUST show their role within the company, expressed as either "administrator" or "member".
- **FR-004**: Each listed user MUST show enough identifying information to distinguish them from other users (at minimum a name and/or email address).
- **FR-005**: The system MUST restrict access to the page to users who hold the administrator role in the active company; non-admin members and unauthenticated visitors MUST be denied access.
- **FR-006**: The list MUST include only members of the active company and MUST NOT include any user from another company.
- **FR-007**: The page MUST correctly handle a company with a single member by displaying that one member.
- **FR-008**: The page MUST present a read-only view; it MUST NOT provide any capability to add, remove, or change users or roles in this first version.

### Key Entities *(include if feature involves data)*

- **Company**: The tenant boundary. Every user shown on the page belongs to the one active company; the page never crosses this boundary.
- **User**: A person with an account. On this page a user is represented by identifying information (name and/or email).
- **Company Membership / Role**: The association between a user and a company, carrying the user's role in that company — either administrator or member. This role is what the page displays for each listed user.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A company admin can open the user management page and see the complete, correct list of their company's members with each member's role in a single view, with no additional navigation required.
- **SC-002**: 100% of listed users belong to the active company; in no scenario does a member of another company appear.
- **SC-003**: 100% of non-admin access attempts (member or unauthenticated) are denied and reveal no membership data.
- **SC-004**: Every listed member displays a role of exactly "administrator" or "member" — no entry is shown without a role.
- **SC-005**: An admin can locate a specific known member in the list within seconds for a company of typical size.

## Assumptions

- **Roles displayed are company-level roles**: The role shown is the company membership role (administrator or member) established by existing company enrollment and admin features, not per-space roles.
- **"Users in the company" means active company members**: The list reflects users who currently hold a membership in the company. Pending invitations or partially enrolled users are out of scope unless they already count as members today.
- **Reuses existing authentication and company context**: The page relies on the existing sign-in and active-company mechanisms to determine who the viewer is and which company is active.
- **Read-only first version**: Per "nothing more, for now," this version only lists users and roles. Inviting, removing, or changing roles are explicitly out of scope and reserved for later features.
- **Access model reuses existing admin scoping**: Admin authority is confined to the viewer's active company, consistent with the platform's existing company-scoped admin behavior.
