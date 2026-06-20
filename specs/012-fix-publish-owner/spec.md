# Feature Specification: Fix Document Publish — Auto-Assign Owner

**Feature Branch**: `012-fix-publish-owner`

**Created**: 2026-06-19

**Status**: Draft

**Input**: User description: "When i click publish document error Document has no owner — assign one before publishing"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Publish a Document Without Manually Assigning an Owner (Priority: P1)

A user creates a document and immediately clicks "Publish." Currently, this fails with "Document has no owner — assign one before publishing." After this fix, the system automatically assigns the user who created the document as the owner, so publishing succeeds without any extra steps.

**Why this priority**: This is the primary blocker: the publish action is completely broken for any document created through the normal flow because the creation step never sets an owner. Fixing this restores the core publish workflow.

**Independent Test**: Can be fully tested by creating a document and immediately clicking "Publish" — if it succeeds and the document transitions to Published state, this story is done.

**Acceptance Scenarios**:

1. **Given** a document was created by a logged-in user and has no explicit owner set, **When** the same or any authorized user clicks "Publish," **Then** the system automatically uses the document creator as the owner and the publish succeeds.
2. **Given** a document was created by a logged-in user, **When** the publish action completes successfully, **Then** the document's owner is recorded as the user who created it.
3. **Given** a document already has an owner explicitly assigned, **When** a user publishes it, **Then** the existing owner is preserved (not overwritten by the publisher).

---

### User Story 2 - See Informative Feedback If Publish Cannot Proceed (Priority: P2)

If publishing fails for any other reason (e.g., no versions exist), the user receives a clear, actionable message rather than a generic error.

**Why this priority**: Secondary to the main fix, but ensures the error-handling surface is coherent after the owner issue is resolved.

**Independent Test**: Can be tested by attempting to publish a document with no content versions and verifying a clear message is returned.

**Acceptance Scenarios**:

1. **Given** a document has no content versions, **When** a user attempts to publish, **Then** the system returns a clear message explaining that content is required before publishing.

---

### Edge Cases

- What happens when the document creator's account has since been deleted or deactivated? The owner field is recorded as-is (the ID is stored regardless of account status); publishing proceeds.
- How does the system handle a publish attempt on a document that is already in the Published state? The system returns an appropriate error indicating the document is already published.
- What if the authenticated user performing the publish is different from the creator? The creator remains the owner; the publisher is recorded as the approver (existing behavior).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When a document is created, the system MUST record the authenticated user who created it as the document's owner.
- **FR-002**: If a document reaches the publish step with no owner recorded, the system MUST automatically assign the publishing user as the owner rather than rejecting the request.
- **FR-003**: The publish action MUST NOT overwrite an owner that has already been explicitly set on the document.
- **FR-004**: After a successful publish, the document MUST reflect the correct owner in its data.
- **FR-005**: The system MUST continue to record the approver (the user who clicked Publish) separately from the owner.

### Key Entities *(include if feature involves data)*

- **Document**: Represents a managed content artifact. Key ownership attribute: `owner_user_id` — the user responsible for the document. Currently not set at creation time.
- **User**: The authenticated actor. Their identity is available at both document creation and publish time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of documents created through the standard creation flow can be published without encountering the "no owner" error.
- **SC-002**: The owner field is populated on every document immediately after creation, with no manual steps required from the user.
- **SC-003**: Existing documents that already have an owner set are unaffected by this change — their owner is not modified during publish.
- **SC-004**: The publish workflow completes in the same number of user actions as before this fix (no additional steps introduced).

## Assumptions

- The authenticated user's identity (ID) is available to the document creation endpoint, as it is to the publish endpoint.
- "Owner" means the user who created the document unless explicitly changed elsewhere; no separate owner-assignment UI is required for this fix.
- Documents created before this fix (with no owner) will be handled at publish time by assigning the publisher as the owner (fallback behavior per FR-002).
- Mobile or alternative clients are out of scope; the fix targets the existing API layer used by the web frontend.
