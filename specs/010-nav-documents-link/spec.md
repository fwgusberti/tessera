# Feature Specification: Documents Navigation Link

**Feature Branch**: `010-nav-documents-link`

**Created**: 2026-06-19

**Status**: Draft

**Input**: User description: "Cant access document page as a user. I have to type /documents in url"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Navigate to Documents via Nav (Priority: P1)

A logged-in user wants to view their documents list. Currently, they must manually type `/documents` in the browser address bar because the navigation bar has no link to that page. After this fix, a "Documents" link in the nav bar takes them there in one click.

**Why this priority**: Core discoverability problem — the documents page exists but is completely unreachable through the UI, making the feature effectively hidden from users.

**Independent Test**: Log in, look at the nav bar, click "Documents" link — documents list page loads. This can be fully tested independently and delivers the entire value of this feature.

**Acceptance Scenarios**:

1. **Given** a logged-in user is on any page, **When** they look at the navigation bar, **Then** they see a "Documents" link alongside Search, Proposals, Metrics, and Admin.
2. **Given** a logged-in user is on any page, **When** they click the "Documents" nav link, **Then** they are taken to the documents list page.
3. **Given** a user is not logged in, **When** they click the "Documents" nav link, **Then** they are redirected to the login page (existing auth guard behavior).

---

### Edge Cases

- Nav link is visible on all pages that include the NavBar (app layout).
- Active/current route styling (if any exists in the nav) should be applied when on `/documents`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The navigation bar MUST include a "Documents" link that navigates to `/documents`.
- **FR-002**: The "Documents" link MUST be visible to all users (authentication is enforced by the page's existing auth guard, not by hiding the link).
- **FR-003**: The "Documents" link MUST follow the same visual style as the existing nav links (Search, Proposals, Metrics, Admin).
- **FR-004**: Clicking the "Documents" link MUST navigate the user to the `/documents` page without a full page reload.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can reach the documents page in one click from any page that displays the navigation bar.
- **SC-002**: The "Documents" link is visually consistent with all other navigation links.
- **SC-003**: 100% of existing navigation tests continue to pass after the change.

## Assumptions

- The existing `NavBar` component (`apps/web/components/NavBar.tsx`) is the single source of navigation; adding the link there is sufficient.
- No role-based visibility rules apply to the Documents link — all authenticated users can see and use documents.
- The `/documents` page already exists and is functional; this feature only adds discoverability via the nav.
- Active-route highlighting is not currently implemented in the nav bar, so no active-state logic needs to be added.
