# Feature Specification: UI Compliance with Implemented Functionality

**Feature Branch**: `003-fix-ui-compliance`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "It seems UI is not compliant with functionalities already done check that and specify fix"

## Context

The Tessera backend API has a fully implemented set of features across eight functional domains — spaces, documents, search, assistant, proposals, connectors, metrics, and admin. The web application currently exposes only a subset of these features through its UI, and even that subset has notable gaps. The home page still displays the default Next.js boilerplate content instead of a Tessera dashboard. Several backend capabilities (document browsing and management, space creation, connector management, document publishing workflow, version history) have no corresponding UI pages at all. One existing page (Metrics) exists but is not accessible from the navigation bar. This specification covers the work needed to bring the web UI into full parity with what the backend already delivers.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Platform Home Dashboard (Priority: P1)

A user lands on the Tessera home page and immediately sees a meaningful summary of the platform state: how many spaces exist, total documents, and quick navigation shortcuts to the main sections (Search, Proposals, Admin). Instead of the current Next.js boilerplate, the home page presents a real welcome dashboard.

**Why this priority**: Every user arrives at the home page first. A placeholder page breaks trust and provides no orientation.

**Independent Test**: Navigate to `/` — should display at minimum a count of spaces, a count of documents, and working navigation links to all major sections.

**Acceptance Scenarios**:

1. **Given** a logged-in user, **When** they visit the root URL, **Then** they see a Tessera-branded dashboard — not Next.js boilerplate — with summary statistics fetched from the API.
2. **Given** the API is reachable, **When** the page loads, **Then** the space count and total query count are displayed accurately.
3. **Given** the API is unreachable, **When** the page loads, **Then** the dashboard shows a graceful degraded state (e.g., "–" values) rather than crashing.

---

### User Story 2 — Document Browsing and Detail (Priority: P2)

A user can navigate to a Documents section, select a space to filter by, see a list of documents within that space, and open a document to read its current content, see its lifecycle state, and view its version history.

**Why this priority**: Documents are the core asset of the platform. Users can not browse, read, or trace the history of any document through the current UI.

**Independent Test**: Navigate to `/documents`, select a space, and open a document — the current version content and a version history list should both be visible.

**Acceptance Scenarios**:

1. **Given** a user on the documents page, **When** they select a space from a dropdown, **Then** only documents belonging to that space are displayed.
2. **Given** a document in the list, **When** the user clicks it, **Then** they see the document title, lifecycle state (e.g., ingested, published), current content, and a list of past versions.
3. **Given** a document with multiple versions, **When** the user views the detail page, **Then** all version entries are listed in order with their version number and approval date.
4. **Given** a document in the `ingested` state with an owner assigned, **When** the user clicks "Publish," **Then** the document transitions to `published` state and the UI reflects the new state without a full page reload.

---

### User Story 3 — Space and Permission Management (Priority: P2)

An admin can create a new space by filling in a form in the UI. Optionally, the admin can also add role-based permissions to any space through a form, without having to issue raw API calls.

**Why this priority**: Space creation is the prerequisite for all other content operations. Currently the admin UI shows a read-only list of spaces with no way to create new ones.

**Independent Test**: Log in as admin, open the Admin page, fill in the "Create Space" form, and submit — the new space must appear in the spaces list immediately.

**Acceptance Scenarios**:

1. **Given** an admin on the Admin page, **When** they fill in slug, name, and sector and submit the form, **Then** a new space is created and immediately visible in the spaces list.
2. **Given** validation rules (slug required, name required), **When** the admin submits an empty form, **Then** form validation errors are shown inline and no API call is made.
3. **Given** an existing space, **When** the admin assigns a role permission (group, role, max confidentiality) through a form, **Then** the permission is saved and the form resets.

---

### User Story 4 — Connector Management (Priority: P3)

An admin can create a new connector for a space, specifying its type and configuration. The admin can also trigger a manual sync of any existing connector and see a confirmation that the job was submitted.

**Why this priority**: Connectors are the ingestion entry points. Without a UI, admins must use raw API calls, which is error-prone and impractical for recurring operations.

**Independent Test**: Navigate to a space's connector section, create a connector of type "confluence", trigger a sync — a job confirmation message appears.

**Acceptance Scenarios**:

1. **Given** an admin on the connector management page, **When** they provide a type and JSON config and submit, **Then** the connector is created and appears in the connector list.
2. **Given** an existing connector, **When** the admin clicks "Sync Now," **Then** a sync job is submitted and the UI displays the resulting job ID or a success message.
3. **Given** a non-admin user, **When** they attempt to access connector management, **Then** they are denied with a clear message.

---

### User Story 5 — Metrics Page Accessible via Navigation (Priority: P1)

The Metrics page at `/metrics` is reachable via a link in the global navigation bar, so admin users can access it without knowing the direct URL.

**Why this priority**: The page already exists and is fully functional, but is orphaned — no user can discover it through the UI without knowing the URL.

**Independent Test**: The navigation bar must include a "Metrics" link that routes to `/metrics`.

**Acceptance Scenarios**:

1. **Given** any user, **When** they look at the navigation bar, **Then** they see a "Metrics" link.
2. **Given** a user who clicks the Metrics link, **When** the page loads, **Then** all metric cards are rendered correctly (same as accessing `/metrics` directly).

---

### Edge Cases

- What happens when a user navigates to `/documents` with no spaces available? The page should display an empty-state message rather than a broken dropdown or error.
- What happens if a document has no current version (version not yet assigned)? The document detail should show the document metadata and indicate no content is available.
- What happens when an admin submits a space creation form with a slug that already exists? The API error should be surfaced as a user-readable inline message, not a generic crash.
- What happens when a connector sync is triggered and the worker is unavailable? The UI should display the error from the API response rather than silently failing.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The home page MUST display a Tessera dashboard with summary statistics (space count, total query count) fetched from the API, replacing the current Next.js boilerplate.
- **FR-002**: The global navigation bar MUST include a "Metrics" link pointing to `/metrics`.
- **FR-003**: The web application MUST provide a `/documents` page listing documents filtered by space, showing document title and lifecycle state for each.
- **FR-004**: Each document in the list MUST be clickable and open a detail view that displays: current version content, lifecycle state, confidentiality level, and version history list.
- **FR-005**: The document detail view MUST expose a "Publish" action for documents in the `ingested` state, calling the publish endpoint and updating the displayed state on success.
- **FR-006**: The Admin page MUST include a "Create Space" form with fields for slug, name, sector, and default language; submission MUST call the create-space endpoint and add the result to the spaces list.
- **FR-007**: The Admin page MUST validate that slug and name fields are non-empty before submitting the form.
- **FR-008**: The Admin page MUST provide a "Add Permission" form for a selected space, capturing IDP group, role, and max confidentiality, calling the permissions endpoint on submit.
- **FR-009**: The web application MUST provide a connector management section (within Admin or a dedicated `/connectors` page) where admins can create connectors for a space.
- **FR-010**: Each listed connector MUST have a "Sync Now" button that triggers a manual sync and displays the returned job ID or a success/error message.
- **FR-011**: All pages with data-fetching MUST show a loading state while the request is in flight and a graceful error state if the request fails.

### Key Entities

- **Space**: A knowledge domain that groups related documents; identified by slug and name.
- **Document**: A versioned living document within a space, with a lifecycle state (ingested, published, archived).
- **DocumentVersion**: A snapshot of a document's content at a point in time; includes version number and optional approver.
- **Proposal**: A suggested change to a document awaiting review; can be approved or rejected.
- **Connector**: A configured data source linked to a space; can be triggered to ingest content.
- **Metrics**: Aggregate statistics about platform usage (query count, drift rate, approval times).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every backend capability exposed by the API has a corresponding user interface path — zero API endpoints are reachable only via direct HTTP calls by end users.
- **SC-002**: Users can complete the full document lifecycle (browse → view → publish) in under 5 clicks from the home page.
- **SC-003**: Admins can create a new space and add a permission without leaving the browser, without consulting API documentation.
- **SC-004**: The Metrics page is discoverable via the navigation bar within 1 second of any page loading — no URL knowledge required.
- **SC-005**: All pages display a loading indicator within 300ms of navigation and an error state within 5 seconds if the API fails to respond.
- **SC-006**: 100% of UI pages that interact with the API use the existing `api` client (no new fetch/axios calls bypass it).

## Assumptions

- All backend API endpoints are already implemented and functional; this feature adds UI only, not backend changes.
- Authentication is handled transparently by the existing session middleware and `require_user` calls on the backend; the web UI does not need to implement a login page in this iteration.
- The web app is a Next.js application using Tailwind CSS; new pages and components should follow the existing styling conventions already present in `search/page.tsx` and `proposals/page.tsx`.
- The "Metrics" and connector management sections are restricted to admin users on the backend; the UI may show these navigation items to all users but the API will enforce access control — no client-side role gating is required.
- Mobile responsiveness is out of scope for this iteration; the UI targets desktop-width viewports consistent with the existing pages.
