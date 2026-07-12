# Feature Specification: Company Page

**Feature Branch**: `060-company-page`

**Created**: 2026-07-11

**Status**: Draft

**Input**: User description: "create company page. It must show company info and allow edition"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View company information (Priority: P1)

Any signed-in member of a company can open a dedicated company page and see the company's profile information: its name, industry, team size, and when it was created. This gives every member a single place to confirm which organization they are working in and what its basic details are.

**Why this priority**: Viewing is the foundation of the page — without it there is nothing to edit. It delivers immediate standalone value: members can verify their organization's details, which matters especially for users who belong to more than one company.

**Independent Test**: Can be fully tested by signing in as a member of a company, navigating to the company page, and confirming that the company's name, industry, team size, and creation date are displayed accurately.

**Acceptance Scenarios**:

1. **Given** a signed-in user who belongs to a company, **When** they navigate to the company page, **Then** they see the company's name, industry, team size, and creation date.
2. **Given** a company whose optional details (industry, team size) were never filled in, **When** a member views the company page, **Then** those fields display a clear "not provided" indication rather than appearing broken or blank.
3. **Given** a signed-in user, **When** they view the company page, **Then** they see only the company they are currently signed into — never another organization's information.

---

### User Story 2 - Edit company information (Priority: P2)

A company administrator can edit the company's profile information (name, industry, team size) directly from the company page, save the changes, and see the updated values reflected immediately.

**Why this priority**: Editing is the second half of the requested feature. It depends on the view existing first (P1), but it is the capability that lets organizations keep their details current — for example after a rebrand or team growth.

**Independent Test**: Can be fully tested by signing in as a company administrator, changing the company name on the company page, saving, and confirming the new name is displayed on the page and anywhere else the company name appears.

**Acceptance Scenarios**:

1. **Given** a signed-in administrator on the company page, **When** they edit the company name and save, **Then** the page shows the updated name and the change persists across sessions.
2. **Given** a signed-in administrator editing company details, **When** they attempt to save an empty company name, **Then** the save is rejected with a clear message and the existing name is preserved.
3. **Given** a signed-in administrator who has started editing, **When** they cancel the edit, **Then** no changes are saved and the original values remain displayed.
4. **Given** an administrator's save succeeds, **Then** a record is kept of who made the change and when.

---

### User Story 3 - Non-administrators cannot edit (Priority: P3)

A regular (non-administrator) member sees the company information in read-only form. Editing controls are not available to them, and any attempt to submit a change through other means is rejected.

**Why this priority**: This protects data integrity and matches how other administrative capabilities in the product are gated, but the page is already useful without it being separately demonstrated — it constrains rather than adds behavior.

**Independent Test**: Can be fully tested by signing in as a non-administrator member, opening the company page, and confirming that no editing controls are offered and that a directly submitted change is refused.

**Acceptance Scenarios**:

1. **Given** a signed-in non-administrator member, **When** they open the company page, **Then** company details are shown read-only and no edit controls are available.
2. **Given** a non-administrator member, **When** they attempt to submit a company detail change by bypassing the page controls, **Then** the change is refused and the company data is unchanged.

---

### Edge Cases

- What happens when a user who belongs to no company attempts to open the company page? They must be directed through the normal "no company" flow (e.g., onboarding), not shown an error page.
- What happens when a user belongs to multiple companies? The page must show the company for the currently active session only.
- What happens when two administrators edit at the same time? The last successful save wins; the page must never show a mix of two edits.
- What happens if an administrator enters an excessively long company name? The save is rejected with a clear message about the allowed length.
- What happens if saving fails (e.g., temporary outage)? The user sees a clear failure message and their entered values are not lost from the form.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated company page accessible to signed-in members of a company.
- **FR-002**: The company page MUST display the company's name, industry, team size, and creation date.
- **FR-003**: Optional fields without a value (industry, team size) MUST be displayed with an explicit "not provided" indication.
- **FR-004**: Company administrators MUST be able to edit the company's name, industry, and team size from the company page.
- **FR-005**: System MUST require a non-empty company name and reject saves that violate this, preserving the current stored value.
- **FR-006**: System MUST allow an in-progress edit to be cancelled, discarding all unsaved changes.
- **FR-007**: Saved changes MUST be persisted and reflected immediately on the page and anywhere else the company's details appear.
- **FR-008**: Non-administrator members MUST see the page read-only; edit controls MUST NOT be offered to them and any submitted change from a non-administrator MUST be refused.
- **FR-009**: A user MUST only ever see and edit the company of their currently active session; access to any other organization's information MUST be impossible.
- **FR-010**: Every successful company detail change MUST be recorded with the acting user, the time of the change, and the affected company.
- **FR-011**: Users who are not signed in MUST NOT be able to view or change company information.

### Key Entities

- **Company**: The organization profile shown and edited on this page. Key attributes: name (required), industry (optional), team size (optional), creation date. Owned by exactly one tenant; associated with the members who belong to it.
- **Company Member**: A user's association with a company, carrying a role (administrator or member) that determines whether they can edit or only view the company's details.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A signed-in member can locate and open the company page and read all company details in under 30 seconds without assistance.
- **SC-002**: An administrator can complete an edit of company details (open, change, save, see confirmation) in under 1 minute.
- **SC-003**: 100% of attempted edits by non-administrators are refused, and 100% of attempts to view or edit another organization's details are blocked.
- **SC-004**: 100% of successful company detail changes have a corresponding record of who changed what and when.
- **SC-005**: After a save, the updated details are visible to the editing user immediately and to other members of the same company on their next page load.

## Assumptions

- Editing is restricted to company administrators, consistent with how other company administration capabilities (such as the user roster) are already gated; regular members get read-only access.
- Editable fields are limited to the company's descriptive profile: name, industry, and team size. Changing company ownership, transferring the administrator role, or deleting the company are out of scope for this feature.
- The company's creation date is displayed for reference but is never editable.
- The existing sign-in and company-session mechanism is reused; this feature adds no new authentication behavior.
- Industry and team size follow the same set of accepted values used when the company was originally created during onboarding.
- Concurrent edits are resolved by last-successful-save-wins; explicit edit locking is out of scope.
