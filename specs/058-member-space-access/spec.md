# Feature Specification: Space Access Management for Company Members

**Feature Branch**: `058-member-space-access`

**Created**: 2026-07-10

**Status**: Draft

**Input**: User description: "I added and use felipe+1@gusba.dev to gusba.dev corp. This user cant see any space and i have no menu to scope it. Create means to do it and fix any bug related"

## Overview

When a person is added to a company — whether directly by an administrator, through an invitation, or automatically by matching their email domain — they become a company member but have access to **no spaces**. This is intentional least-privilege behavior, but today it is a dead end for everyone involved:

- The new member opens the spaces area and is told "No spaces available in your company", which reads as if the company has no spaces at all. They have no idea access must be granted, or by whom.
- The administrator has no obvious place to grant that access. The user management area, where the admin just added the person, offers no way to give them access to spaces. The only existing path is a small "Members" link on each individual space's card — and an administrator can only see the cards of spaces they personally belong to, so spaces created by other people are entirely unreachable for administration.

This feature gives administrators a clear, discoverable way to manage which spaces each company member can access (and with what role), makes the "no access yet" situation understandable to the member, and closes the gaps that make some spaces or some members unmanageable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin grants a member access to spaces from user management (Priority: P1)

A company administrator adds a person to the company, then — from the same user management area — opens that person's space access, sees which spaces the member can and cannot access, and grants access to one or more spaces with a chosen role. The member can then see and use those spaces.

**Why this priority**: This is the reported gap. Without it, adding someone to a company produces a member who cannot do anything, and the administrator has no discoverable way to fix that. It completes the "add a user" journey shipped in previous features.

**Independent Test**: As a company admin, add a fresh user to the company, open their space access management from the user management area, grant them access to an existing space, then log in as that user and confirm the space and its documents are visible.

**Acceptance Scenarios**:

1. **Given** a company admin viewing the company's user management area, **When** they select a member, **Then** they can see which of the company's spaces that member has access to, and with what role.
2. **Given** a company admin viewing a member's space access, **When** they grant access to a space with a role, **Then** the member gains access to that space and the change is visible immediately in the member's access list.
3. **Given** a member who was just granted access to a space, **When** they open the spaces area, **Then** the space appears (along with any nested spaces covered by access inheritance) and its documents are reachable.
4. **Given** a company admin viewing a member's space access, **When** they change the member's role on a space or revoke access, **Then** the member's effective access reflects the change on their next page load, without re-login.
5. **Given** a non-admin company member, **When** they look for space access management for another member, **Then** no such controls are offered and any direct attempt is refused.

---

### User Story 2 - Company admin can administer every space in the company (Priority: P2)

A company administrator can see and administer all spaces belonging to the company — including spaces they are not personally a member of — so that no space is orphaned from administration.

**Why this priority**: Even with a per-member access menu, administration is broken if an admin cannot see a space that exists. Today an admin only sees spaces they personally belong to, so a space created by someone else can become invisible and unmanageable, and members can never be granted access to it.

**Independent Test**: Have one user create a space without adding the company admin as a member; confirm the company admin can still find that space in administrative contexts and grant another member access to it.

**Acceptance Scenarios**:

1. **Given** a company admin and a space they are not a member of, **When** they manage a member's space access, **Then** that space is listed among the spaces access can be granted to.
2. **Given** a company admin, **When** they view the company's spaces for administration, **Then** every space of the company is visible to them, and none from any other company.
3. **Given** a regular (non-admin) member, **When** they view spaces, **Then** they continue to see only the spaces they have access to — this story widens visibility for company admins only.

---

### User Story 3 - A member with no space access understands their situation (Priority: P3)

A company member who has not yet been granted access to any space sees a clear explanation that their account is active but no space has been shared with them yet, and that a company administrator can grant access — instead of a message implying the company has no spaces.

**Why this priority**: The misleading "No spaces available in your company" message is what made the reported situation look like a bug and left the member stranded with no next step. Fixing the message removes confusion and support load, but the P1/P2 stories deliver the actual capability.

**Independent Test**: Log in as a company member with no space access and confirm the spaces area explains that access must be granted by an administrator, rather than stating no spaces exist.

**Acceptance Scenarios**:

1. **Given** a member of a company that has spaces, none shared with them, **When** they open the spaces area, **Then** the message explains no spaces have been shared with them yet and that an administrator can grant access.
2. **Given** a member who is later granted access to a space, **When** they revisit the spaces area, **Then** the explanatory message is gone and the space is shown.

---

### User Story 4 - Every path into the company produces a manageable member (Priority: P3)

Regardless of how a person became a company member — self-created company, invitation, direct add by an admin, or automatic email-domain matching at sign-up — they appear in the administrator's member listings and search, and can be granted space access like anyone else.

**Why this priority**: The reported account joined via one of the newer paths (direct add / domain matching). If any join path produces members that are missing from search or ineligible for access grants, the P1 capability silently fails for exactly the people who need it. This is the "fix any bug related" sweep.

**Independent Test**: Create one member through each join path, then as company admin confirm each one appears in user management and in member search for a space, and that granting each one access works end-to-end.

**Acceptance Scenarios**:

1. **Given** members who joined via direct add, invitation acceptance, and email-domain matching, **When** an admin searches for them while granting space access, **Then** all of them are found and can be granted access.
2. **Given** any such member granted access to a space, **When** they log in, **Then** they see the space and its documents with the granted role's capabilities.

---

### Edge Cases

- Granting a member access to a space they already have access to must not create a duplicate — the existing access is shown and the admin can adjust the role instead.
- Granting access to a nested space follows the existing inheritance rules: access to a parent that implies visibility of children must be reflected consistently in what the member sees.
- If a member is removed from the company, their space access within that company must no longer grant them anything.
- An admin managing their own space access is allowed, but they cannot demote or remove protections in a way that existing role rules forbid (existing role-change rules apply unchanged).
- A member of another company must never appear as a grantable person, and spaces of another company must never appear as grantable targets (tenant isolation).
- If two admins modify the same member's access at nearly the same time, the last change wins and the resulting state is what both see on refresh — no corrupted or partial access records.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Company administrators MUST be able to view, for any member of their company, the list of company spaces the member has access to, including the member's role on each space.
- **FR-002**: Company administrators MUST be able to grant a member access to any space in their company, choosing the member's role on that space, from the member-centric management view.
- **FR-003**: Company administrators MUST be able to change a member's role on a space and to revoke a member's access to a space from the same view.
- **FR-004**: The member-centric access management MUST be reachable from the company's user management area — an administrator who just added a member must be able to grant space access without leaving that context to hunt for another page.
- **FR-005**: Company administrators MUST be able to see and administer every space belonging to their company, including spaces they are not personally a member of; visibility for non-admin members remains limited to spaces they have access to.
- **FR-006**: Members who joined the company by any supported path (company creation, invitation, direct add, email-domain matching) MUST be equally visible in member listings/search and equally eligible for space access grants.
- **FR-007**: A member with no space access MUST see an accurate explanation that no spaces have been shared with them and that a company administrator can grant access — never a message implying the company has no spaces.
- **FR-008**: Access changes MUST take effect without requiring the affected member to log out and back in; the member sees the updated space list on their next page load.
- **FR-009**: Only company administrators (or, for a given space, that space's admins under existing rules) MUST be able to grant, change, or revoke space access; all other members are refused.
- **FR-010**: Every grant, role change, and revocation MUST be recorded with who did it, to whom, and for which space, for accountability.
- **FR-011**: The existing per-space member management (from a space's own members view) MUST continue to work, and both views MUST reflect the same underlying access — a change made in one is visible in the other.
- **FR-012**: All member and space listings involved MUST be scoped to the administrator's active company; no person or space from another company may ever be shown or targetable (tenant isolation).

### Key Entities

- **Company member**: A person belonging to a company, with a company-level role (admin or member). The subject whose space access is being managed.
- **Space**: A named container of documents within a company, possibly nested under a parent space. The target of access grants.
- **Space access (membership)**: The link between a member and a space, carrying a space-level role (admin, editor, or viewer). Created, modified, and revoked by this feature; already exists as a concept and is reused, not reinvented.
- **Access change record**: An accountability record of who granted/changed/revoked which member's access to which space, and when.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A company administrator can take a newly added member from "no access" to "can open a space's documents" in under one minute, starting from the user management area.
- **SC-002**: 100% of members, regardless of join path (created company, invited, directly added, domain-matched), can be found and granted space access by an administrator.
- **SC-003**: 100% of a company's spaces are reachable for administration by a company administrator, including spaces the administrator does not belong to.
- **SC-004**: After access is granted, the member sees the space and its documents on their next page load, with no re-login, in 100% of cases.
- **SC-005**: No member is ever shown a message stating or implying the company has no spaces when spaces exist but are simply not shared with them.
- **SC-006**: Zero cross-company exposure: in all new views and flows, people and spaces from other companies never appear.

## Assumptions

- Least-privilege stays the default: being added to a company grants access to **no** spaces automatically; access is always an explicit administrative act. (If auto-granting a default space is desired later, it is a separate feature.)
- The existing three space roles (admin, editor, viewer) are sufficient; this feature reuses them and defaults new grants to the least-powerful role unless the administrator picks another.
- The existing per-space "Members" management and its rules (who may manage, role-change constraints) remain the authoritative access rules; this feature adds a member-centric way to drive the same access, not a parallel permission system.
- Company-admin-wide space visibility (FR-005) applies to administrative listing and access management; it does not silently change what non-admin members can see.
- People with a pending invitation who have not yet joined the company are out of scope — space access is managed for actual members only.
- The reported account (felipe+1@gusba.dev in the gusba.dev company) is a real instance of this situation and serves as the primary verification case: after this feature, an admin can grant it space access and the account can see and use those spaces.
