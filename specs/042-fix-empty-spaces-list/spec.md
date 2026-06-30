# Feature Specification: Fix Empty Spaces List

**Feature Branch**: `042-fix-empty-spaces-list`

**Created**: 2026-06-30

**Status**: Draft

**Input**: User description: "Fix empty spaces list: users see zero spaces in the Spaces menu, space-filtered document search, and related views even when their company has spaces, because creating a space never grants the creator a SpaceMembership and no backfill exists for spaces created before the membership-based access model (feature 041) was introduced. Confirmed in the live dev database: every space in every company currently has zero space_membership rows, including the reporting user's own company-admin-owned spaces."

## Clarifications

### Session 2026-06-30

- Q: How should access to orphaned spaces (zero recorded members) be restored? → A: One-time data backfill — explicit Space Membership rows are inserted for each affected company's admin(s) on the spaces that currently have none. The access model stays exactly as introduced by feature 041 (always explicit, recorded membership); no implicit "admins always see everything" rule is introduced into the access-checking logic itself.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Creating a Space Grants Immediate Access (Priority: P1)

A user creates a new space for their organization. Immediately afterward, that space appears for them in the Spaces list, the space-filtered document search, and any other space-scoped view — they are never locked out of something they just created.

**Why this priority**: This is the source of the regression. Without it, every newly created space repeats today's bug, so no other fix can hold unless this is closed.

**Independent Test**: Create a new space as any authenticated company member, then immediately fetch the Spaces list and confirm the new space appears with the creator shown as its admin.

**Acceptance Scenarios**:

1. **Given** an authenticated company member, **When** they create a new space, **Then** they immediately see that space in their Spaces list with an admin-level role.
2. **Given** the creator of a space, **When** they open that space's members view, **Then** they appear listed as an admin member of it.

---

### User Story 2 - Previously Created Spaces Become Visible Again (Priority: P1)

A company that already had spaces before this fix — created by an admin, an owner, or any member, under the old rules where access didn't depend on individual membership records — has those spaces restored to visibility for the people who should reasonably have access to them, without anyone having to manually re-add every space one by one.

**Why this priority**: Existing organizations are blocked right now. Fixing only new space creation (User Story 1) leaves every organization that already has spaces — like the reporting user's — permanently locked out of work they already did.

**Independent Test**: Using a company with one or more spaces that currently show zero visible spaces for its admin, apply the fix and confirm the company's admin(s) can immediately see and manage all of that company's existing spaces.

**Acceptance Scenarios**:

1. **Given** a company whose existing spaces have no recorded members (today's broken state), **When** the fix is applied, **Then** the company's admin(s) see all of that company's spaces in their Spaces list.
2. **Given** a space that already had legitimate members recorded before the fix, **When** the fix is applied, **Then** those existing memberships and roles are left unchanged — the fix only restores access where none currently exists, it never overrides or duplicates existing access.

---

### User Story 3 - Space Visibility Is Consistent Everywhere (Priority: P2)

Wherever a user can interact with spaces — browsing the Spaces page, filtering documents by space, or any other space-aware view — they see the same consistent list of spaces they actually have access to. There's no view where spaces "exist" and another where they silently don't.

**Why this priority**: The report specifically calls out three different surfaces (Spaces menu, spaces list, document search filter) all going blank together. Confirming the fix holds consistently across all of them prevents a partial fix that only patches one screen.

**Independent Test**: As a user with confirmed access to spaces (per Story 1 or 2), visit the Spaces page, the document search/filter view, and any other space-scoped screen, and confirm the same set of spaces appears in all of them.

**Acceptance Scenarios**:

1. **Given** a user with access to spaces a, b, and d, **When** they visit the Spaces page, **Then** all three spaces appear.
2. **Given** the same user, **When** they open the document search/filter by space, **Then** the same three spaces are offered as filter options.

---

### Edge Cases

- A company with multiple admins: when restoring access to an orphaned space, every admin of that company should end up with access, not just one arbitrarily chosen admin.
- A space that has zero memberships AND whose company has no identifiable admin (should not occur under normal use, but the fix must not error or silently drop the space — it should be reported, not crash).
- A user who is a company member but not a company admin, and who is not personally tied to any orphaned space: this fix does not retroactively grant them access to spaces they were never part of — only people who already hold legitimate authority over the space's company (its admins) are restored to spaces that have no other recorded members.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Creating a space MUST grant the creator admin-level access to that space, recorded the same way any other space access is recorded, with no extra step required.
- **FR-002**: Any space that currently has no recorded members MUST have its company's admin(s) granted admin-level access to it, recorded as an explicit, ordinary space membership (the same kind FR-001 creates) — a one-time correction of missing records, not a standing rule that bypasses membership checks going forward.
- **FR-003**: Restoring access to a previously inaccessible space MUST NOT alter or duplicate any access that already legitimately exists on that space.
- **FR-004**: The Spaces list, the space-filtered document search, and every other space-aware view MUST reflect the same access rules consistently — a space visible in one MUST be visible in all of them, for the same user.
- **FR-005**: The fix MUST apply to spaces that already exist at the time of the fix, not only to spaces created afterward.
- **FR-006**: If a space has no recorded members and its company also has no identifiable admin to restore access to, the system MUST surface this as a reportable condition rather than fail silently or error out the whole operation.

### Key Entities *(include if feature involves data)*

- **Space**: A knowledge container belonging to a company. Already exists; this feature does not change what a space is, only who is recorded as having access to it.
- **Space Membership**: The record linking a person to a space with a role. This feature ensures one is always created when a space is created, and that none are missing for spaces that already existed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of spaces that exist today, across every company, are visible to at least one person who can act on them (their company's admin(s)) immediately after the fix is applied.
- **SC-002**: 100% of spaces created after the fix are immediately visible to their creator, with zero manual follow-up steps.
- **SC-003**: The Spaces list, document search space filter, and Spaces menu show identical space sets for the same user, with zero discrepancies.
- **SC-004**: Zero pre-existing, legitimate space memberships are altered or duplicated by the fix.

## Assumptions

- "Company admin" means a person holding the company-level admin role (as already used elsewhere in this system for permission decisions), not the space-level role.
- A space's "creator" is the authenticated user who performs the create-space action; spaces do not currently track a separate, distinct creator field for already-existing spaces, so the restoration in User Story 2 targets company admins rather than attempting to guess each space's original creator.
- This fix does not change who is allowed to create a space (any company member can, as today) — it only ensures that doing so results in working access, consistent with existing space-creation behavior.
- This is treated as a correction of an access-records gap, not a change to the underlying access model introduced by nested spaces (041) — that model (explicit membership, with downward inheritance through parent/child spaces) is assumed correct and is left intact.
