# Feature Specification: Add User on the Company User Management Page

**Feature Branch**: `054-add-company-user`

**Created**: 2026-07-05

**Status**: Draft

**Input**: User description: "create add user on user page."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin invites a new person to the company by email (Priority: P1)

From the company user management page, a company administrator adds a person who does not yet have a way into the company by entering that person's email address. The system sends them an invitation, and once they accept it they become a member of the company and appear in the roster. This lets an admin grow their company without the person needing an account beforehand.

**Why this priority**: This is the primary requested capability — turning the read-only roster from feature 053 into a page where an admin can actually bring people in. Inviting by email is the broadest path because it works even for people who have never registered, so it is the most valuable single slice.

**Independent Test**: Sign in as a company admin, open the user management page, enter a valid email that is not yet in the company, and confirm the system reports the invitation was sent. Then accept the invitation as that person and confirm they now appear in the company roster.

**Acceptance Scenarios**:

1. **Given** an admin on the user management page, **When** they enter a valid email address for a person not already in the company and choose to invite them, **Then** the system records a pending invitation for that email in the active company and confirms the invitation was sent.
2. **Given** an invitation has been sent to an email, **When** the invited person accepts it, **Then** they become a member of that company and appear in the roster with the role that was assigned to them.
3. **Given** an admin enters an email that already belongs to a current member of the company, **When** they try to invite it, **Then** the system prevents a duplicate and tells the admin that person is already a member.
4. **Given** an admin enters a malformed email address, **When** they try to invite, **Then** the system rejects the input with a clear validation message and sends nothing.

---

### User Story 2 - Admin adds an already-registered user to the company immediately (Priority: P1)

From the same page, an administrator adds a person who already has an account by selecting that existing user. The user is added to the company right away as a member, with no invitation or acceptance step, and appears in the roster immediately.

**Why this priority**: Many people being added already have accounts (for example, they belong to another company or were previously registered). Adding them directly avoids an unnecessary invite-and-accept round trip and gives the admin an immediate result. It is equally core to the "add user" request as inviting by email.

**Independent Test**: Sign in as a company admin, open the user management page, select an existing registered user who is not yet in the company, add them, and confirm they appear in the roster immediately without any acceptance step.

**Acceptance Scenarios**:

1. **Given** an admin on the user management page, **When** they select an existing registered user who is not already a member and add them, **Then** that user immediately becomes a member of the active company and appears in the roster without an invitation being sent.
2. **Given** an admin tries to add an existing user who is already a member of the company, **When** they attempt the add, **Then** the system prevents the duplicate and informs the admin the person is already a member.
3. **Given** an admin is choosing an existing user to add, **When** they search, **Then** they can identify the correct person by name and/or email before adding them.

---

### User Story 3 - Admin chooses the added user's company role (Priority: P2)

When adding a user by either method, the administrator chooses whether that person joins as an administrator or as a member. The chosen role is what the person holds once they are in the company.

**Why this priority**: Choosing the role at add time saves a separate follow-up step and lets an admin bring in a co-administrator directly. It builds on the two add methods above, so it is valuable but secondary to the ability to add someone at all.

**Independent Test**: As an admin, add a user (by either method) with the "administrator" role selected, then confirm on the roster that the new person is shown as an administrator; repeat with "member" and confirm they are shown as a member.

**Acceptance Scenarios**:

1. **Given** an admin is adding a user, **When** they select the "administrator" role and complete the add, **Then** the resulting membership carries the administrator role and the roster shows that person as an administrator.
2. **Given** an admin is adding a user, **When** they select the "member" role (or leave the default) and complete the add, **Then** the resulting membership carries the member role.
3. **Given** an admin is adding a user, **When** the add form is presented, **Then** a role is preselected to "member" so the admin is never forced to make a choice for the common case.

---

### User Story 4 - Only company administrators can add users, scoped to their own company (Priority: P1)

The ability to add users is available only to administrators of the active company, and any user added — whether invited or added directly — is added only to the admin's own active company. Non-admin members and unauthenticated visitors cannot add users.

**Why this priority**: Adding users changes who has access to a company and at what level. Tessera is multi-tenant, so allowing a non-admin to add people, or allowing an admin to add someone into a different company, would be an access-control and cross-tenant integrity problem. This restriction is as critical as the add capability itself.

**Independent Test**: Attempt to add a user while signed in as a non-admin member and confirm the action is refused; repeat as an admin and confirm it succeeds and the person lands in that admin's active company only.

**Acceptance Scenarios**:

1. **Given** a non-admin member of a company, **When** they attempt to add a user, **Then** the action is denied and no invitation is sent and no membership is created.
2. **Given** an unauthenticated visitor, **When** they attempt to add a user, **Then** the action is denied and no data is changed.
3. **Given** an admin whose account is associated with more than one company, **When** they add a user with one company active, **Then** the invitation or membership is created only in that active company and never in any other company.

---

### Edge Cases

- **Email already invited but not yet accepted**: If an admin invites an email that already has a pending invitation for the same company, the system does not create a conflicting duplicate; it tells the admin an invitation is already outstanding for that email.
- **Adding a person who is already a member**: Both add paths reject the attempt cleanly and explain the person is already a member, rather than creating a duplicate membership.
- **Direct-add target does not exist**: If the admin tries to directly add an existing user who cannot be found (e.g., no account matches), the system reports that no such user exists rather than silently doing nothing.
- **Email delivery failure**: If the invitation cannot be sent (e.g., email delivery fails), the admin is told the invitation was not delivered rather than being led to believe it succeeded.
- **Concurrent adds**: If two admins add or invite the same person at nearly the same time, the person still ends up with exactly one membership in the company, not two.
- **Newly added user visibility**: After a successful direct add, the roster reflects the new member without the admin needing to reload from scratch; after a successful invite, the roster reflects the pending state in a way consistent with how the company tracks invitations.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The company user management page MUST provide an admin-only control to add a user to the active company.
- **FR-002**: The system MUST allow an administrator to add a user by entering an email address, which creates a pending invitation for that email in the active company and sends that person an invitation.
- **FR-003**: The system MUST allow an administrator to add an already-registered user by selecting that user, which makes them a member of the active company immediately with no acceptance step.
- **FR-004**: When adding a user by either method, the system MUST let the administrator choose the user's company role as either "administrator" or "member", defaulting to "member".
- **FR-005**: For the direct-add method, the administrator MUST be able to find and identify the intended existing user by name and/or email before adding them.
- **FR-006**: The system MUST validate email input for the invite method and reject malformed addresses without sending anything.
- **FR-007**: The system MUST prevent adding a user who is already a member of the active company via either method, and MUST inform the administrator that the person is already a member.
- **FR-008**: The system MUST prevent creating a second, conflicting pending invitation for an email that already has an outstanding invitation in the active company.
- **FR-009**: The system MUST restrict the add capability to administrators of the active company; non-admin members and unauthenticated visitors MUST be denied and MUST cause no invitation or membership to be created.
- **FR-010**: The system MUST create the invitation or membership only in the administrator's active company and MUST NOT affect any other company.
- **FR-011**: An invited person who accepts their invitation MUST become a member of the company with the role that was assigned at invite time.
- **FR-012**: The system MUST give the administrator clear feedback on the outcome of each add attempt — success, "already a member", validation error, "no such user", or delivery failure.
- **FR-013**: After a successful add, the user management roster MUST reflect the result (a new immediate member, or the pending-invitation state) consistent with how the company roster is presented.

### Key Entities *(include if feature involves data)*

- **Company**: The tenant boundary. Every invitation created and every membership added by this feature belongs to the one active company; the feature never crosses this boundary.
- **User**: A person with an account. For the direct-add method the target is an existing user identified by name and/or email; for the invite method the target may not yet have an account and is identified only by email.
- **Company Membership / Role**: The association between a user and a company carrying the user's company role — administrator or member. This feature creates memberships (directly or upon invitation acceptance) with the role chosen by the admin.
- **Invitation**: A pending record tying an email address to the active company until it is accepted, expires, or is otherwise resolved. Created by the invite-by-email method; carries the role to be granted on acceptance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A company admin can add a person to their company from the user management page by email in a single, self-contained action, with clear confirmation that the invitation was sent.
- **SC-002**: A company admin can add an existing registered user to their company directly and see them appear in the roster immediately, with no acceptance step.
- **SC-003**: 100% of add actions result in the person being placed only in the admin's active company; in no scenario is a user added to another company.
- **SC-004**: 100% of add attempts by non-admins (members or unauthenticated) are denied and create no invitation and no membership.
- **SC-005**: 100% of attempts to add someone who is already a member are prevented, with no duplicate membership created.
- **SC-006**: Every user added — whether immediately or upon invitation acceptance — holds exactly the role the admin selected ("administrator" or "member").
- **SC-007**: For every add attempt, the admin receives an unambiguous outcome message (success, already-a-member, invalid input, no-such-user, or delivery failure) so they never have to guess whether the action worked.

## Assumptions

- **Builds on the feature 053 user management page**: This feature adds an "add user" capability to the existing company user management page rather than creating a new page. The read-only roster from 053 remains and is extended.
- **Reuses the existing company invitation mechanism**: The invite-by-email path relies on the platform's existing company invitation flow (pending invitation created for an email, invitation delivered, membership granted on acceptance) rather than inventing a new one.
- **Reuses existing authentication, active-company context, and admin scoping**: Who the viewer is, which company is active, and whether the viewer is an admin are all determined by existing platform mechanisms, consistent with the company-scoped admin behavior used elsewhere.
- **Company-level roles**: The role chosen when adding ("administrator" or "member") is the company membership role, not a per-space role.
- **Direct add applies to already-registered users only**: The direct, immediate-add path targets users who already have an account. People without an account are brought in via the invite-by-email path.
- **Role default is "member"**: When the admin does not explicitly choose a role, the added user joins as a member, consistent with how enrollment currently grants roles to joiners.
- **Managing existing users is out of scope**: Removing users, changing the role of someone already in the company, and revoking or resending invitations are not part of this feature and are reserved for later work. This feature only covers adding users.
