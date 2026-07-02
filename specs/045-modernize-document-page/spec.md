# Feature Specification: Modernize Document Page

**Feature Branch**: `045-modernize-document-page`

**Created**: 2026-07-01

**Status**: Draft

**Input**: User description: "modernize document page."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read a document in a modern, consistent layout (Priority: P1)

A user opens a document's detail page to read its content and check its status. Today the page uses a dated, plain layout (raw preformatted text, bare table, inline ad-hoc styling) that looks and feels inconsistent with the rest of the app, which has recently been refreshed (e.g., the Spaces folder browser). The user should instead land on a page that looks and feels like the same product — clear visual hierarchy, readable content, and consistent styling.

**Why this priority**: This is the core experience of the page — every other action (publishing, reindexing, reviewing history) happens on top of it. Without a coherent, readable layout, the modernization delivers no value.

**Independent Test**: Can be fully tested by opening any document's detail page and confirming the header, content area, and overall layout use the app's current visual language (colors, spacing, typography, iconography) and that document content is easy to read.

**Acceptance Scenarios**:

1. **Given** a published document with formatted markdown content, **When** the user opens its detail page, **Then** the content is displayed as readable formatted text (headings, lists, emphasis, code blocks rendered distinctly) rather than raw unformatted text.
2. **Given** a document detail page, **When** the user views the header area, **Then** the title, status, confidentiality level, and tags are presented with clear visual hierarchy consistent with other modernized areas of the app.
3. **Given** a document that belongs to a nested space (e.g., a sub-space of a top-level space), **When** the user views the page, **Then** a breadcrumb trail shows each ancestor space leading to the document, and clicking any ancestor segment navigates to that space.

---

### User Story 2 - Take document actions with clear, modern controls (Priority: P2)

A user eligible to publish or reindex a document wants the available actions to be obvious, well-styled, and give clear feedback (loading, success, error), matching the interaction patterns used elsewhere in the app.

**Why this priority**: Actions are the primary way users change document state; they must remain fully functional and become visually consistent, but the page is still useful for reading even if this story weren't done.

**Independent Test**: Can be fully tested by, as an eligible user, publishing an ingested document and reindexing a published document, and confirming each action shows a modern-styled control with correct loading/success/error feedback and that ineligible users do not see actions they cannot perform.

**Acceptance Scenarios**:

1. **Given** an ingested document owned by the current user, **When** the user clicks "Publish", **Then** the button shows a loading state, then reflects the resulting published state, styled consistently with the app's modern action controls.
2. **Given** a published document the current user does not own and is not an admin for, **When** the user views the page, **Then** no reindex action is shown.
3. **Given** an action fails (e.g., publish or reindex request errors), **When** the failure occurs, **Then** a clearly styled error message is shown near the action without disrupting the rest of the page.

---

### User Story 3 - Scan version history at a glance (Priority: P3)

A user reviewing a document's history wants to quickly scan its versions, approval dates, and approvers in a format that's easy to read, replacing the current bare, minimally-styled table.

**Why this priority**: Version history is important for auditing and context but is secondary to reading current content and taking action; it can be modernized independently of the other two stories.

**Independent Test**: Can be fully tested by opening a document with multiple historical versions and confirming the version list is presented in a modern, scannable format showing version number, approval timestamp, and approver for each entry.

**Acceptance Scenarios**:

1. **Given** a document with three or more versions, **When** the user views the version history section, **Then** each version's number, approval date/time, and approver are clearly legible and visually distinct from one another.
2. **Given** a document with no version history, **When** the user views the version history section, **Then** a clear, styled empty-state message is shown instead of an empty table.

---

### Edge Cases

- What happens when a document has no current content (no approved version yet)? The page must show a clear, styled empty state rather than a blank or broken content area.
- What happens when a document has an unusually long title or a large number of tags? The header must wrap or truncate gracefully without breaking the layout.
- What happens when document content is very long or contains wide elements (e.g., code blocks, tables)? Content must remain readable without horizontal overflow breaking the page layout.
- What happens when the page is viewed on a small (mobile-width) screen? Header, actions, content, and version history must all remain usable and readable without horizontal scrolling of the page itself.
- What happens when the document fails to load or does not exist? A clearly styled error or "not found" state must be shown, consistent with the app's current visual style.
- What happens while the document is loading? A clearly styled loading state must be shown.

## Clarifications

### Session 2026-07-01

- Q: Should back-navigation on the document page stay a single "back to Documents" link, or show a full breadcrumb trail reflecting the document's space location? → A: Show a full breadcrumb trail reflecting the document's space location (e.g., Engineering > Backend > Document Title), reusing the same breadcrumb pattern as the Spaces folder browser, with each ancestor segment clickable to navigate to that space.
- Q: Should the document's markdown content be rendered as formatted rich text, or kept as plain/monospace text with only the container restyled? → A: Render markdown as formatted rich text — headings, lists, emphasis, and code blocks are visually distinguished, not shown as raw source.
- Q: Should the version history support pagination/"show more" for documents with many versions, or show all versions in a single unpaginated list? → A: Show all versions in a single list/table, no pagination — assume typical documents have a small number of versions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The document detail page MUST present the document header (title, status, confidentiality level, tags, and back/breadcrumb navigation) using the same visual language (colors, spacing, typography, iconography) as other recently modernized areas of the application.
- **FR-002**: The document detail page MUST render the current version's content as readable formatted text (headings, lists, emphasis, and code blocks visually distinguished) instead of raw unformatted text.
- **FR-003**: The system MUST preserve all existing document actions (publish, reindex), including their current eligibility rules and loading/success/error feedback, restyled to match the modernized design.
- **FR-004**: The version history MUST be presented in a modern, scannable format that clearly shows, for each version, its version number, approval date/time, and approver.
- **FR-005**: The page MUST remain fully usable and readable across both desktop and mobile-sized viewports.
- **FR-006**: The page MUST provide clear, styled empty states for a document with no current content and for a document with no version history.
- **FR-007**: The page MUST provide clear, styled loading and error/not-found states when the document is loading, fails to load, or does not exist.
- **FR-008**: The document detail page MUST display a full breadcrumb trail reflecting the document's location in the space hierarchy (e.g., Engineering > Backend > Document Title), reusing the same breadcrumb navigation pattern as the Spaces folder browser, with each ancestor segment navigable to that space.

### Key Entities

- **Document**: The item being viewed — has a title, lifecycle state (ingested, published, archived), confidentiality level, tags, and an owner. Its state and ownership determine which actions are available.
- **Document Version**: A historical snapshot of a document's content — has a version number, approval timestamp, approver, and the content itself. The most recent approved version is shown as the current content.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can identify a document's status and available actions within 5 seconds of the page finishing loading.
- **SC-002**: Formatted document content (headings, lists, code blocks) renders as structured, legible text for all documents, rather than as raw unformatted text.
- **SC-003**: The page displays correctly with no layout defects across viewport widths from 360px to 1440px and above.
- **SC-004**: Existing actions (publish, reindex) continue to succeed at the same rate as before the redesign — the visual refresh introduces zero functional regressions.
- **SC-005**: The document detail page is visually consistent with other recently modernized pages in the app (e.g., the Spaces folder browser), as judged by a side-by-side design review.

## Assumptions

- This is a visual and structural modernization of the existing document detail page; no new document management capabilities (e.g., inline editing, commenting, sharing) are introduced.
- The redesign follows the visual patterns established in the recent Spaces page redesign (card-based layout, consistent color palette, iconography) for consistency across the app.
- Existing backend/API contracts for documents, versions, publishing, and reindexing are unchanged — this is a frontend presentation change only.
- Existing permission logic determining who can publish or reindex a document is unchanged; only the visual presentation of those controls is updated.
- Documents are expected to have a small number of versions (each created by a publish/approval event), so the version history is displayed as a single unpaginated list without a "show more" control.
