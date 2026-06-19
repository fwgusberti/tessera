# Feature Specification: Add Document — Frontend

**Feature Branch**: `009-add-document-frontend`

**Created**: 2026-06-18

**Status**: Draft

**Input**: User description: "im unable to add documents in front-end"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Create a New Document (Priority: P1)

A logged-in user navigates to the Documents page, clicks "Add Document", fills in the document title, selects a target space, picks the language and confidentiality level, writes the initial content in markdown, and submits the form. The new document appears immediately in the document list with an "ingested" state badge.

**Why this priority**: This is the core missing capability — without a creation form, no new documents can be added via the frontend, making the entire Documents feature incomplete.

**Independent Test**: Can be fully tested by rendering the Documents page, clicking "Add Document", submitting a valid form, and verifying the new document row appears in the list — delivers a complete document-creation workflow.

**Acceptance Scenarios**:

1. **Given** the user is on the Documents page, **When** they click "Add Document", **Then** a modal dialog with the document creation form appears over the document list.
2. **Given** the form is displayed, **When** the user fills in title, space, language, confidentiality, and content markdown and clicks "Save", **Then** the document is created and appears in the document list with state "ingested".
3. **Given** the user clicks "Add Document" but has no spaces available, **When** the form opens, **Then** a message explains that a space must exist before adding documents.

---

### User Story 2 — Form Validation and Error Handling (Priority: P2)

A user attempts to submit an incomplete or invalid form, and the system provides clear inline guidance about what needs to be corrected without losing the data they've already entered.

**Why this priority**: Prevents silent failures and user frustration during the document creation flow; ensures data quality without blocking legitimate submissions.

**Independent Test**: Can be fully tested by submitting a form with a missing required field (e.g., blank title or no space selected) and verifying an inline validation message is shown without page navigation.

**Acceptance Scenarios**:

1. **Given** the creation form is displayed, **When** the user submits with an empty title, **Then** an inline error message is shown next to the title field and the form is not submitted.
2. **Given** the creation form is displayed, **When** no space is selected, **Then** an inline error message asks the user to choose a space.
3. **Given** the API returns an error after submission, **When** the error response arrives, **Then** a user-readable error banner is shown at the top of the form.

---

### User Story 3 — Cancel / Dismiss Without Saving (Priority: P3)

A user who started filling in the form decides not to create the document and cancels, returning to the document list without any changes being made.

**Why this priority**: Standard UX pattern that prevents accidental data entry; low risk but necessary for a polished experience.

**Independent Test**: Can be fully tested by opening the form, typing content, clicking "Cancel", and verifying the document list is displayed with no new document added.

**Acceptance Scenarios**:

1. **Given** the creation form is open with partial data entered, **When** the user clicks "Cancel", **Then** the form is dismissed and the document list is shown with no changes.

---

### Edge Cases

- What happens when the content markdown field is empty on submission? (Assume empty string is allowed at creation; validation deferred to publish step.)
- How does the system handle network failure during document creation? (Display a dismissible error message; allow the user to retry.)
- What if the space list loads slowly? (Show a loading indicator in the space selector within the form.)
- What if the user has access to many spaces (50+)? (The space selector uses a scrollable dropdown; no pagination needed for MVP.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Documents list page MUST display an "Add Document" button visible to all authenticated users.
- **FR-002**: Clicking "Add Document" MUST open a modal dialog containing the document creation form; the modal is dismissable via "Cancel" button or pressing Escape.
- **FR-003**: The creation form MUST include fields for: title (text, required), space (select from user's available spaces, required), language (select, defaults to "pt-BR"), confidentiality (select: internal / restricted / public, defaults to "internal"), and content in markdown (plain textarea with no preview, optional at creation).
- **FR-004**: The form MUST validate that title and space are provided before allowing submission.
- **FR-005**: On successful submission, the modal MUST close and the new document row MUST be prepended to the current document list without navigating away or reloading the page.
- **FR-006**: On API error, the form MUST remain open and display a human-readable error message.
- **FR-007**: A "Cancel" button MUST be available to dismiss the form without saving.
- **FR-008**: The space selector inside the form MUST reuse the already-loaded space list (no duplicate API call if spaces are already fetched).

### Key Entities

- **Document**: A knowledge artifact belonging to a space, with title, language, confidentiality, lifecycle state, and an initial content version.
- **Space**: An organisational container for documents; the user selects one when creating a document.
- **DocumentVersion**: The initial content snapshot created alongside the document; version number starts at 1.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A logged-in user can create a new document from the Documents page in under 60 seconds from clicking "Add Document" to seeing the document in the list.
- **SC-002**: 100% of required-field validation errors are surfaced inline before the form is submitted to the server.
- **SC-003**: The document list updates to include the newly created document without a full page reload after a successful save.
- **SC-004**: All document creation tests in the frontend test suite pass, maintaining or improving overall coverage.

## Clarifications

### Session 2026-06-18

- Q: Should the creation form open as a modal dialog, inline panel, or separate page? → A: Modal dialog overlaying the document list; dismissable via Cancel or Escape.
- Q: After successful document creation, should the user stay on the list or navigate to the new document? → A: Stay on the documents list; modal closes and new document row appears inline.
- Q: Should the content markdown field be a plain textarea or include a live preview? → A: Plain textarea only; no markdown preview in the creation modal.

## Assumptions

- The user is already authenticated and has completed onboarding (the documents page is behind the auth guard).
- At least one space must exist for a document to be created; the form will surface a message if no spaces are available.
- Tags support is out of scope for this MVP; tags will default to an empty list.
- The `frontmatter` field is an advanced option out of scope for this MVP; it will default to an empty object.
- The existing `/v1/spaces` and `POST /v1/documents` API endpoints are already implemented and functional — this feature is purely a frontend addition.
- Mobile layout is not a primary concern for MVP; a responsive design that is functional on desktop is sufficient.
