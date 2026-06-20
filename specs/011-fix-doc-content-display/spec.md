# Feature Specification: Fix Document Content Display

**Feature Branch**: `011-fix-doc-content-display`

**Created**: 2026-06-19

**Status**: Draft

**Input**: User description: "I saved a new document but when I try to see it the content says No content available for this document."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — View Content of a Newly Created Document (Priority: P1)

A user creates a new document through the "Add Document" form, submits it with content in the markdown field, then navigates to the document's detail page. They expect to see the content they typed, not a placeholder message.

**Why this priority**: This is the broken core flow — a document is created successfully but its content is invisible on the detail page immediately after creation, making the feature appear broken and the saved content inaccessible.

**Independent Test**: Can be fully tested by creating a document with non-empty content markdown via the Add Document modal, clicking the document title in the list, and verifying the content appears in the "Current Content" section of the detail page.

**Acceptance Scenarios**:

1. **Given** a user submits the Add Document form with a non-empty content markdown field, **When** the document detail page is opened, **Then** the content entered during creation is displayed in the "Current Content" section.
2. **Given** a user submits the Add Document form with an empty content markdown field, **When** the document detail page is opened, **Then** the "No content available" placeholder is shown (empty content is a valid state).
3. **Given** a document was created and its content is visible on the detail page, **When** the page is refreshed, **Then** the content remains visible without disappearing.

---

### User Story 2 — Version History Shows Initial Version (Priority: P2)

After creating a document, the user views its version history and sees the initial version (version 1) listed, confirming the content was saved as a version record.

**Why this priority**: Confirms that the document versioning system is functioning correctly at creation time, not just at publish time.

**Independent Test**: Can be fully tested by creating a document and checking that the "Version History" table on the detail page contains at least one row with version number 1.

**Acceptance Scenarios**:

1. **Given** a user creates a new document, **When** they open the document detail page, **Then** the Version History section shows version 1 as the initial entry.

---

### Edge Cases

- What if a document was created before this fix was deployed? (Those documents will still show "No content available" since their `current_version_id` was never set — the fix applies to newly created documents only.)
- What if the content markdown submitted is only whitespace? (Whitespace-only content is treated as non-empty; the content is stored and displayed as submitted.)
- What if creation succeeds but setting the current version fails? (The system should treat this as a creation failure and surface an error to the user rather than silently saving a document with inaccessible content.)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When a document is created via the document creation form, the system MUST associate the initial content version as the document's current version at the moment of creation.
- **FR-002**: The document detail page MUST display the content of the initial version immediately after the document is created, without requiring any additional action such as publishing.
- **FR-003**: A document created with non-empty content MUST show that content in the "Current Content" section of its detail page when the page is first loaded.
- **FR-004**: A document created with empty content MUST still show the "No content available" placeholder — this is the correct and expected state for empty content.
- **FR-005**: The fix MUST NOT alter the publish workflow — publishing a document still sets the approved version as the current version.

### Key Entities

- **Document**: A knowledge artifact with a `current_version_id` pointer that identifies which version represents its current content for viewing purposes.
- **DocumentVersion**: A snapshot of content at a point in time, created at document creation (version 1) and at each publish event. Version 1 is the initial draft content.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of documents created with non-empty content display that content immediately on the detail page without requiring a publish action.
- **SC-002**: The create-document flow completes with the document's current version pointer set — zero documents reach the "ingested" state with an unlinked initial version.
- **SC-003**: All existing document creation tests continue to pass, and a new regression test covering this scenario is added.
- **SC-004**: The publish workflow is unaffected — documents published after this fix behave identically to documents published before it.

## Assumptions

- The bug exists solely in the backend creation endpoint, which creates a `DocumentVersion` record but does not set `current_version_id` on the `Document` at creation time.
- Documents already in the database before this fix are out of scope; a data migration for existing records is not required for this fix.
- The fix is a backend-only change; no frontend changes are needed.
- The `set_current_version` method already exists on the document repository and is used by the publish endpoint — it can be reused here without modification.
- "No content available" for a document created with an empty content markdown field is correct and intentional behaviour that should be preserved.
