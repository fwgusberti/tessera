# Feature Specification: Frontend Spaces Page

**Feature Branch**: `040-frontend-spaces-page`

**Created**: 2026-06-30

**Status**: Draft

**Input**: User description: "add spaces page in front-end"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse Available Spaces (Priority: P1)

A logged-in user navigates to the Spaces section of the application and sees a list of all spaces they have access to within their active company. Each space is displayed as a card showing its name, sector, and a link to manage its members.

**Why this priority**: This is the core deliverable — without a spaces listing, users have no way to discover or navigate to spaces. All other stories depend on this foundation.

**Independent Test**: Accessible end-to-end by logging in, visiting `/spaces`, and confirming that the list of spaces belonging to the current company is displayed correctly.

**Acceptance Scenarios**:

1. **Given** a logged-in user with access to two or more spaces in the active company, **When** they navigate to `/spaces`, **Then** they see a card for each space showing the space name, sector, and the user's role in that space.
2. **Given** a logged-in user with no spaces in the active company, **When** they navigate to `/spaces`, **Then** they see a clear empty-state message explaining that no spaces are available.
3. **Given** a logged-in user, **When** they navigate to `/spaces`, **Then** only spaces belonging to the currently active company are shown — spaces from other companies the user belongs to must not appear.

---

### User Story 2 - Navigate to Space Members (Priority: P2)

From the Spaces listing, a user clicks an action on a space card and is taken to either the members management page or the documents page filtered by that space.

**Why this priority**: Direct navigation to a space's content (documents) and membership are the two primary reasons a user would look up a space. Surfacing both from the listing makes the Spaces page immediately useful.

**Independent Test**: Navigate to `/spaces`, click the "Documents" link on any space card, and confirm arrival at `/documents?space=[id]` pre-filtered to that space. Separately, click the "Members" link and confirm arrival at `/spaces/[id]/members`.

**Acceptance Scenarios**:

1. **Given** the Spaces listing is showing at least one space, **When** the user clicks the "Members" action on a space card, **Then** they are navigated to the members page for that specific space.
2. **Given** the Spaces listing is showing at least one space, **When** the user clicks the "Documents" action on a space card, **Then** they are navigated to the documents page pre-filtered to that space.
3. **Given** the user is on a space's members page, **When** they use the browser back button or a breadcrumb link, **Then** they return to the Spaces listing.

---

### User Story 3 - Access Spaces from Navigation (Priority: P3)

A logged-in user can reach the Spaces page from the top navigation bar without having to know the URL, just as they can reach Documents or Search.

**Why this priority**: Discoverability is important for adoption, but the listing itself (P1) delivers value even if only accessed by direct URL initially.

**Independent Test**: Verify that a "Spaces" link appears in the NavBar for authenticated users and clicking it navigates to `/spaces`.

**Acceptance Scenarios**:

1. **Given** a logged-in user on any page, **When** they look at the navigation bar, **Then** they see a "Spaces" link.
2. **Given** a logged-in user on the Spaces page, **When** the navigation bar renders, **Then** the "Spaces" link is visually highlighted as the active section.
3. **Given** a logged-out user, **When** they look at the navigation bar, **Then** no "Spaces" link is shown (consistent with other authenticated-only links).

---

### Edge Cases

- What happens when the API request to load spaces fails or times out? The page must show a clear error message rather than a blank screen.
- What happens when the active company changes mid-session? The spaces list must reflect the newly active company without requiring a page reload.
- What if a space's name is very long? Cards must not overflow or break the layout.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a `/spaces` page that lists all spaces accessible to the authenticated user within their active company, sorted alphabetically by space name (A → Z).
- **FR-002**: Each space in the listing MUST display the space name, sector, and the authenticated user's role within that space (admin, editor, or viewer).
- **FR-003**: Each space card MUST include two navigable action links: one to the space's members page (`/spaces/[id]/members`) and one to the documents page pre-filtered to that space (`/documents?space=[id]`). Both links MUST be available to all authenticated users regardless of their role in the space.
- **FR-003a**: The user's role MUST be displayed as a visual badge on the space card (consistent with the role badge already used on the members page).
- **FR-004**: The spaces listing MUST only show spaces belonging to the currently active company — cross-company spaces MUST NOT appear.
- **FR-005**: The page MUST display a meaningful empty-state message when no spaces are available for the active company.
- **FR-006**: The page MUST display a meaningful error message when the spaces data cannot be loaded.
- **FR-007**: The navigation bar MUST include a "Spaces" link visible to authenticated users, following the same pattern as existing nav links (Documents, Search, etc.).
- **FR-008**: The "Spaces" navigation link MUST be visually distinguished (active state) when the user is on any `/spaces/*` route.
- **FR-009**: The page MUST require authentication — unauthenticated users attempting to visit `/spaces` must be redirected to the login page.

### Key Entities *(include if feature involves data)*

- **Space**: A knowledge container belonging to a company. Key attributes visible on the listing: name, sector, and unique identifier used for navigation. Already exists in the backend.
- **Company (Tenant)**: The organizational boundary that scopes which spaces are shown. The active company is established from the authenticated session.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A logged-in user can find and land on the Spaces page within 2 navigation interactions from any authenticated page.
- **SC-002**: The Spaces page fully loads and displays spaces in under 2 seconds on a standard connection.
- **SC-003**: 100% of spaces belonging to the active company are shown on the page — no spaces are missing and no spaces from other companies appear.
- **SC-004**: Every space card links correctly to both its members page and its filtered documents page; zero broken navigation links.
- **SC-005**: The empty state and error state render without visual breakage when triggered.

## Assumptions

- The backend `GET /v1/spaces` endpoint already exists and returns spaces scoped to the authenticated company; no backend changes are required.
- The members page (`/spaces/[id]/members`) already exists; this feature links to it but does not modify it.
- The documents page already supports space filtering via `?space=[id]` query parameter (built in spec 020); no changes to the documents page are required by this feature.
- The page is desktop-first but should follow the existing responsive patterns already used in the app (mobile hamburger menu already handles "Spaces" link inclusion).
- No pagination is required for the initial release; the number of spaces per company is expected to be small.
- Space creation is an admin-only backend operation; this page is read-only and does not include a "Create Space" action.

## Clarifications

### Session 2026-06-30

- Q: Should the Spaces listing page show role-based differences in what a user sees or can do per space card? → A: Show the user's role badge on each card (admin/editor/viewer); same links and actions for all roles — no action gating at the listing level.
- Q: What order should spaces appear in the listing? → A: Alphabetical by space name (A → Z).
- Q: Should each space card also link to the documents page filtered by that space? → A: Yes — include both a "Members" link and a "Documents" link on each card.
