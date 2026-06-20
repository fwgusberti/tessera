# Feature Specification: Fix Document Search Returns No Results

**Feature Branch**: `015-fix-document-search`

**Created**: 2026-06-20

**Status**: Draft

**Input**: User description: "Searching a document shows no result even with a word that matches a title of a document"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Search Returns Matching Documents (Priority: P1)

A user types a word into the document search box that appears in a document title. They expect to see that document appear in the results. Currently no results are returned, making the search feature completely non-functional.

**Why this priority**: Search is the primary way users discover documents. A broken search that returns zero results for known-matching titles renders the feature unusable and blocks all downstream workflows that depend on finding documents.

**Independent Test**: Can be fully tested by creating a document with a known title, then searching for a word from that title — if the document appears in results, the fix is verified.

**Acceptance Scenarios**:

1. **Given** at least one document exists with the title "Quarterly Report", **When** a user searches for "Quarterly", **Then** the "Quarterly Report" document appears in the search results list.
2. **Given** at least one published document exists, **When** a user searches for any word that is present in that document's title, **Then** the document appears in the search results.
3. **Given** no documents exist whose titles contain the search term, **When** a user searches for that term, **Then** the system displays an empty state message indicating no results were found.

---

### Out of Scope (this feature)

- **Partial/prefix matching** (P2): Searching "Quarter" to find "Quarterly Report" is deferred to a follow-on feature.
- **Body-content search** (P3): Full-text search across document body or description fields is deferred to a follow-on feature.

---

### Edge Cases

- What happens when the search query contains only whitespace or is empty?
- How does the system handle special characters in the search query (e.g., slashes, quotes)?
- What happens when a document title contains accented or non-ASCII characters and the user searches with ASCII?
- Draft documents do NOT appear in search results; only published documents are searchable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The search function MUST return all **published** documents whose titles contain the search term (case-insensitive). Draft documents MUST NOT appear in search results.
- **FR-002**: Search MUST be triggered only on explicit user submission (pressing Enter or clicking a Search button) when the query contains at least one non-whitespace character. Live/as-you-type search is out of scope.
- **FR-003**: The system MUST display a "no results found" message when no documents match the query — not an error or blank screen.
- **FR-004**: Search results MUST include the document title so the user can identify which document matched. Richer metadata (last updated date, status) is out of scope for this P1 fix and deferred to a follow-on feature.
- **FR-005**: The search MUST complete and render results within 2 seconds under normal load (see SC-002) so users are not left waiting without feedback.
- **FR-006**: Whitespace-only or empty queries MUST NOT trigger a search request; the system MAY clear results or show an initial state.
- **FR-007**: Search results MUST remain consistent between page loads — searching the same term twice MUST return the same set of documents (given no documents have been added or removed).

### Key Entities *(include if feature involves data)*

- **Document**: The searchable artifact. Has at minimum a title, status (draft/published), owner, and creation date. The title is the primary field used for matching.
- **Search Query**: The user-supplied string of characters used to filter documents.
- **Search Result**: A document entry returned because it matches the query, displayed with identifying metadata.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A search using any word from an existing document title returns that document in the results 100% of the time.
- **SC-002**: Search results appear within 2 seconds of the user submitting a query under normal load.
- **SC-003**: Zero "false empty" results — a search that previously returned 0 results for a term matching a document title now returns at least 1 result.
- **SC-004**: Users report being able to find a known document by title on the first search attempt.

## Clarifications

### Session 2026-06-20

- Q: Should this feature deliver only the P1 bug fix, or also P2 partial matching and/or P3 body-content search? → A: P1 fix only — restore title-match search; P2 and P3 deferred.
- Q: Should draft documents appear in search results, or only published ones? → A: Published documents only; drafts are excluded from search.
- Q: How is search triggered — on explicit submit or live/as-you-type? → A: Explicit submit only (Enter key or Search button); live search is out of scope.

## Assumptions

- The current search failure is a regression or data-pipeline bug — the search UI is in place and the underlying documents exist; the problem is in matching logic or data indexing.
- Only published documents are searchable. Draft documents are explicitly excluded from search results.
- The search query is compared against document titles at minimum; full-text search across document body content is a P3 enhancement, not part of the core fix.
- The fix targets the existing search infrastructure rather than introducing a new search engine or completely replacing the current implementation.
- Authentication is already in place; search results are scoped to documents the authenticated user is authorized to view.
