# Feature Specification: Reindex Document on Finishing an Edit

**Feature Branch**: `047-fix-edit-reindex`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "when finishing editing a document it must be reindexed"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Search reflects a document's latest edited content (Priority: P1)

A space member with write access opens a published document, edits its
Markdown content, and finishes the editing session (creating a new version).
Someone searching for terms that only appear in the newly edited content
should find the document; someone searching for terms that only existed in
the old content (and were removed by the edit) should no longer find it
there.

**Why this priority**: This is the core problem being fixed — today,
finishing an edit creates a new document version but search results keep
showing the previous version's content indefinitely, which is confusing and
undermines trust in search.

**Independent Test**: As a space member with write access, open a published
document, change its Markdown content to include a new distinctive word,
finish the editing session, wait for indexing to complete, then search for
that new word — the document appears in results. Search for a distinctive
word that was only in the removed content — the document no longer appears.

**Acceptance Scenarios**:

1. **Given** a published document a user has write access to, **When** the
   user edits its content and finishes the editing session (producing a new
   version with different content), **Then** the system triggers
   reindexing of the document using the newly finished version's content.
2. **Given** reindexing has completed after a finished edit, **When** a user
   searches using terms found only in the new content, **Then** the document
   appears in search results.
3. **Given** reindexing has completed after a finished edit, **When** a user
   searches using terms that existed only in the prior (now replaced)
   content, **Then** the document no longer appears in search results for
   those terms.

---

### User Story 2 - No-op edits don't trigger unnecessary reindexing (Priority: P2)

A user opens the edit view for a document but finishes the session without
actually changing the content. Because no new version was created, the
system does not trigger a reindex — there is nothing new to index.

**Why this priority**: Avoids wasted indexing work and keeps the reindex
trigger tied strictly to "there is new content to reflect," which matters
once this fix is live and reindexing runs automatically on every finished
edit.

**Independent Test**: Open the edit view for a published document, make no
changes (or revert back to the original content), finish the editing
session, and confirm no new version was created and no reindexing was
triggered.

**Acceptance Scenarios**:

1. **Given** a published document open in the edit view, **When** the user
   finishes the editing session without changing the content, **Then** no
   new version is created and no reindexing is triggered.

---

### User Story 3 - Editing an unpublished document doesn't trigger reindexing (Priority: P3)

A user finishes editing a document that has never been published (or is no
longer in the published state). Because unpublished documents are not
searchable, finishing the edit does not trigger a reindex.

**Why this priority**: Keeps the reindex trigger consistent with the
existing rule that only published documents are searchable and reindexable,
avoiding indexing work for content nobody can search for yet.

**Independent Test**: Open the edit view for a document that has not been
published, make a content change, finish the editing session, and confirm a
new version is created but no reindexing is triggered.

**Acceptance Scenarios**:

1. **Given** a document that is not currently published, **When** a user
   edits it and finishes the editing session (producing a new version),
   **Then** no reindexing is triggered even though a new version was
   created.

---

### Edge Cases

- What happens if the reindexing step itself fails or the indexing worker is
  unavailable when an edit is finished? The user's edit and new version must
  still be saved successfully — reindexing failure must not block or roll
  back the finished edit.
- What happens if a user finishes editing a document, and before reindexing
  completes, finishes editing it again? The system should end up reflecting
  the latest finished version once indexing catches up, without requiring
  the user to manually trigger reindexing.
- What happens when a document is edited and finished immediately after
  being published (same session)? The finish-triggered reindex must operate
  on the new version's content, not the version that was just published.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST trigger reindexing of a document whenever finishing
  an edit session creates a new version for a document that is currently in
  the published state.
- **FR-002**: The reindex triggered by finishing an edit MUST use the content
  of the newly created version, not any prior version.
- **FR-003**: System MUST NOT trigger reindexing when finishing an edit
  session does not create a new version (i.e., the content was unchanged).
- **FR-004**: System MUST NOT trigger reindexing when finishing an edit
  session on a document that is not currently in the published state.
- **FR-005**: Triggering reindexing when an edit is finished MUST NOT delay
  or block the user from seeing their edit session complete successfully.
- **FR-006**: If reindexing fails after an edit is finished, the newly
  created version MUST remain saved and intact regardless of the indexing
  outcome.
- **FR-007**: The reindexing triggered by finishing an edit MUST stay scoped
  to the document's own company/space, consistent with existing tenant
  isolation guarantees for search and indexing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a user finishes editing a published document with real
  content changes, search results reflect the new content within 5 seconds
  under normal operating conditions.
- **SC-002**: Once reindexing completes after a finished edit, search never
  returns a document based solely on content that was removed by that edit.
- **SC-003**: Finishing an edit session with no content changes results in
  zero reindexing operations being triggered.
- **SC-004**: Finishing an edit session on a document that has never been
  published (or is no longer published) results in zero reindexing
  operations being triggered.

## Assumptions

- "Finishing an edit session" refers to the existing action that converts a
  user's in-progress edits into a new, saved document version (introduced in
  feature 046), not merely autosaving in-progress drafts.
- Only published documents are searchable and eligible for reindexing,
  consistent with the existing manual reindex capability.
- This feature reuses the existing reindexing/search pipeline (the same one
  used when a document is published or manually reindexed); it does not
  change how indexing itself works, only when it is triggered.
- The 5-second indexing turnaround in SC-001 matches the expectation already
  established for publish and manual reindex operations.
