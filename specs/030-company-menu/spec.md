# Feature Specification: Company Menu

**Feature Branch**: `030-company-menu`

**Created**: 2026-06-21

**Status**: Draft

**Input**: User description: "Create company menu"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Current Company and Switch Companies (Priority: P1)

An authenticated user who belongs to one or more companies can see which company they are currently operating within, and switch to a different company without leaving the application.

**Why this priority**: Users with multi-company membership need context on which company's data they are viewing. This is the primary interaction that anchors all other company-scoped features and is a prerequisite for meaningful navigation.

**Independent Test**: Can be fully tested by opening the navbar as an authenticated user, confirming the current company name is visible, and — if the user belongs to more than one company — selecting a different company and confirming the active company changes.

**Acceptance Scenarios**:

1. **Given** a user is authenticated and belongs to exactly one company, **When** the user views the navigation bar, **Then** the name of that company is displayed, and no switching option is shown.
2. **Given** a user is authenticated and belongs to multiple companies, **When** the user opens the company menu, **Then** a list of all their companies is shown with the current one clearly indicated.
3. **Given** a user has multiple companies and selects a different one from the menu, **When** the selection is confirmed, **Then** the active company switches and the interface reflects the new company context.

---

### User Story 2 - Create a New Company from the Menu (Priority: P2)

An authenticated user can initiate company creation directly from the company menu without navigating away to the onboarding flow.

**Why this priority**: Users who want to create a second (or additional) company should be able to do so in context, not via a separate onboarding journey. This reduces friction and makes the feature reachable.

**Independent Test**: Can be fully tested by opening the company menu and selecting "Create new company," filling in a company name, and confirming the new company appears in the company list and becomes the active company.

**Acceptance Scenarios**:

1. **Given** an authenticated user opens the company menu, **When** the user selects "Create new company," **Then** a form or modal appears requesting the new company's name (and optionally industry and team size).
2. **Given** the user submits a valid company name, **When** the creation succeeds, **Then** the new company is added to the user's company list and becomes the active company.
3. **Given** the user submits an empty or invalid company name, **When** the form is submitted, **Then** a clear error message is shown and no company is created.

---

### User Story 3 - Access Company Settings (Priority: P3)

A company admin can navigate to company settings directly from the company menu.

**Why this priority**: Admins need a discoverable path to manage company-level configuration (members, billing, etc.). The menu is the natural entry point for this.

**Independent Test**: Can be fully tested by opening the company menu as an admin, selecting "Company settings," and confirming navigation to the company settings page.

**Acceptance Scenarios**:

1. **Given** an authenticated user with the admin role opens the company menu, **When** the menu is displayed, **Then** a "Company settings" option is visible.
2. **Given** a non-admin user opens the company menu, **When** the menu is displayed, **Then** "Company settings" is either hidden or shown as disabled/inaccessible.
3. **Given** an admin selects "Company settings," **When** clicked, **Then** the user is navigated to the company settings section.

---

### Edge Cases

- What happens when a user belongs to no company? The company menu should prompt the user to create or join one.
- What happens if the user's membership in the current company is revoked while they are active? The UI should detect the loss of access and redirect the user appropriately.
- What happens if company creation fails due to a network error? An error message is shown and the user can retry without data loss.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The navigation bar MUST display a company menu element that shows the currently active company name at all times when the user is authenticated.
- **FR-002**: The company menu MUST expand to list all companies the authenticated user belongs to when opened.
- **FR-003**: The currently active company MUST be visually distinguished from other companies in the list.
- **FR-004**: Users MUST be able to switch their active company by selecting a different company from the menu.
- **FR-005**: The company menu MUST include an option to create a new company.
- **FR-006**: Creating a new company from the menu MUST require at minimum a company name and MUST make the new company immediately active upon successful creation.
- **FR-007**: The company menu MUST include a "Company settings" option that is only accessible (visible or enabled) to users with the admin role in the current company.
- **FR-008**: When a user belongs to no company, the company menu area MUST prompt the user to create or join a company.
- **FR-009**: The company menu MUST be accessible on both desktop and mobile viewports, consistent with the existing navigation bar behavior.

### Key Entities

- **Company**: Represents an organization a user belongs to; has a name, optional industry, and optional team size.
- **Company Membership**: Represents the relationship between a user and a company, including the user's role (e.g., admin, member).
- **Active Company**: The company currently selected as the user's operating context; determines which data and settings are displayed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can identify their current active company from the navigation bar in under 3 seconds without any scrolling or additional clicks.
- **SC-002**: Users with multiple company memberships can switch their active company in under 5 seconds from opening the menu.
- **SC-003**: Users can complete new company creation from the menu in under 2 minutes.
- **SC-004**: 95% of admin users can locate the "Company settings" option in the company menu on first attempt without assistance.
- **SC-005**: The company menu renders correctly and is fully usable on mobile screen widths (≤ 768 px), with no layout breakage or inaccessible tap targets.

## Assumptions

- Users may belong to zero, one, or more companies simultaneously; multi-company membership is supported by the existing data model.
- The active company selection is persisted in the user's session so that page refreshes do not reset it.
- Switching the active company does not navigate the user away from their current page but updates the company context in the background; page content that is company-scoped will refresh accordingly.
- The existing role system (admin, editor, viewer) from the Space Membership feature is analogous to company-level roles; admin role grants access to company settings.
- Mobile support follows the existing responsive NavBar pattern (hamburger menu on small screens).
- The onboarding flow for first-time company creation remains unchanged; the in-menu creation is a lighter, non-onboarding path for adding subsequent companies.
