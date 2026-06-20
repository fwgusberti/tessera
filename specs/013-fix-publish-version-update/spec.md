# Feature Specification: Fix Publish — Record Approval on Existing Version

**Feature Branch**: `013-fix-publish-version-update`

**Created**: 2026-06-20

**Status**: Draft

**Input**: User description: "Publishing a document returns 500 Internal Server Error. Root cause: the publish endpoint calls ver_repo.create(approved_version) where approved_version is a model_copy of the latest version — keeping the same UUID and version_number — then attempts to INSERT it, hitting the primary key and unique constraint on (document_id, version_number). The fix should update the existing version's approver_user_id and approved_at fields in-place instead of creating a duplicate row."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Publish a Document Successfully (Priority: P1)

A user clicks "Publish" on a document that has content. The system records who approved it and when, then marks the document as published. Currently this always returns a server error and the document never transitions to the Published state.

**Why this priority**: The publish action is entirely broken — any attempt produces a server error. This is the highest priority fix.

**Independent Test**: Can be fully tested by creating a document, adding content, and publishing it — if the document state becomes "published" and no server error occurs, this story is done.

**Acceptance Scenarios**:

1. **Given** a document exists with at least one content version, **When** an authorized user publishes it, **Then** the publish succeeds, the document state changes to "published," and the approval timestamp and approver are recorded on the version.
2. **Given** a document was published successfully, **When** the user views the document, **Then** the document shows state "published" with the approver and approval time correctly set.
3. **Given** a document is published, **When** the same document is published again (re-publish), **Then** the approval information is updated on the existing version without creating duplicate records.

---

### User Story 2 - Approval Metadata Is Preserved After Publish (Priority: P2)

After a successful publish, the system correctly records who approved the document and at what time. This data is visible and accurate for audit and governance purposes.

**Why this priority**: The approval record (approver identity and timestamp) is required by the audit and governance requirements of the platform. Without it, published documents cannot be traced back to their approver.

**Independent Test**: After publishing, retrieve the document version and confirm `approver` and `approved_at` fields are non-null and accurate.

**Acceptance Scenarios**:

1. **Given** a document is published by user A, **When** the document version is retrieved, **Then** the version shows user A as the approver and the approval timestamp matches the publish time.
2. **Given** a document already has approval metadata set, **When** it is published again, **Then** the approval metadata is overwritten with the new approver and timestamp.

---

### Edge Cases

- What happens when a document has no content versions? The publish fails with a clear "no content" message (existing behavior, unaffected by this fix).
- What if the approval update fails mid-publish (e.g., database error)? The entire operation is rolled back; the document remains unpublished.
- What if the same version is approved twice concurrently? The last write wins; the document ends up published either way with the most recent approver recorded.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When a user publishes a document, the system MUST record the approver's identity and the exact timestamp of approval on the existing version record — without creating a new version record.
- **FR-002**: The system MUST NOT create a duplicate version record during publish. Each document version is immutable in its content but may have its approval metadata updated.
- **FR-003**: After a successful publish, the document MUST be in the "published" state and its current version MUST reference the approved version.
- **FR-004**: The publish operation MUST be atomic: either all changes (approval metadata + document state) are committed, or none are.
- **FR-005**: A publish failure MUST return a clear, non-server-error response explaining why publication could not complete (no content, invalid state, etc.).

### Key Entities *(include if feature involves data)*

- **Document**: A managed content artifact with a lifecycle state. Key state: transitions from "ingested"/"outdated" to "published" on successful publish.
- **Document Version**: An immutable content snapshot with mutable approval metadata fields: `approver` (the user who approved) and `approved_at` (timestamp of approval).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of publish attempts on documents with content succeed without server errors.
- **SC-002**: Every successfully published document version has non-null `approver` and `approved_at` values immediately after publish.
- **SC-003**: The total number of version records in the system does not increase during a publish operation — only existing version records are modified.
- **SC-004**: Publish errors (invalid state, no content) return a 4xx response, never a 5xx.

## Assumptions

- A document version's content (markdown, frontmatter) is never changed during publish — only the approval metadata fields are updated.
- The approver identity is derived from the authenticated user performing the publish action; no separate approval workflow is required.
- Re-publishing an already-published document (to update approval metadata) is an acceptable operation.
- The existing version numbering and content remain unchanged; only `approver_user_id` and `approved_at` are written.
