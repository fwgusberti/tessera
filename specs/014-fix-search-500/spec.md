# Feature Specification: Fix Search Endpoint 500 Error

**Feature Branch**: `014-fix-search-500`

**Created**: 2026-06-20

**Status**: Draft

**Input**: User description: "POST /v1/search returns 500 Internal Server Error for query 'mamadeira'"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Search Returns Results (Priority: P1)

An authenticated user sends a natural-language query (e.g., "mamadeira") to the search endpoint and receives a list of relevant document snippets instead of a server error.

**Why this priority**: The search endpoint is completely broken — any query causes a 500 error, blocking the core retrieval use case of the platform.

**Independent Test**: Can be fully tested by POSTing `{"query": "mamadeira"}` to `/v1/search` with a valid JWT and verifying the response is 200 with a `results` array.

**Acceptance Scenarios**:

1. **Given** an authenticated user and at least one published document in the system, **When** they POST `{"query": "mamadeira"}` to `/v1/search`, **Then** the response is HTTP 200 with a `{"results": [...]}` body (list may be empty if no relevant documents exist).
2. **Given** an authenticated user, **When** they POST a search query containing non-ASCII characters (e.g., accented Portuguese words), **Then** the response is HTTP 200 — not a 500 error.
3. **Given** an unauthenticated request, **When** a client calls `/v1/search`, **Then** the response is HTTP 401, not 500.

---

### User Story 2 - Search Gracefully Handles No Matching Results (Priority: P2)

An authenticated user searches for a term that no published document covers and receives an empty results list rather than an error.

**Why this priority**: Zero-result scenarios are normal usage; they must not be confused with system failures.

**Independent Test**: POST a query that is guaranteed to have no matches (unique nonsense string). Expect HTTP 200 with `{"results": []}`.

**Acceptance Scenarios**:

1. **Given** an authenticated user and no published documents matching the query, **When** they POST `{"query": "zzz-no-match-xyz"}` to `/v1/search`, **Then** the response is HTTP 200 with `{"results": []}`.

---

### User Story 3 - Search Respects Confidentiality and Published-Only Filter (Priority: P3)

Search results never surface draft or restricted documents, preserving the ACL-first contract already established in the codebase.

**Why this priority**: Security invariant — must be preserved through any fix. Lower priority only because it is already present in the current code path (not broken by the 500 bug itself).

**Independent Test**: Verify that only `state = published` documents appear in results, and that `RESTRICTED` confidentiality documents are absent.

**Acceptance Scenarios**:

1. **Given** a draft document and a published document both matching the query, **When** search executes, **Then** only the published document's chunks appear in the results.
2. **Given** a document with `RESTRICTED` confidentiality, **When** any user searches, **Then** that document is absent from results regardless of the query score.

---

### Edge Cases

- What happens when the embedding service (Ollama) is unavailable? The system should return a meaningful error (503 or 502), not an unhandled 500.
- What happens when `space_ids` is provided but all listed spaces are inaccessible? The response must be HTTP 200 with an empty results list.
- What happens when the `chunks` table has no `embedding` column populated (no documents ingested yet)? Response must be HTTP 200 with empty results, not a database error.
- What happens when `top_k` is 0 or negative? The system should either treat it as the default (10) or return a 422 validation error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST return HTTP 200 with a `results` array for any authenticated POST to `/v1/search` with a non-empty `query` string.
- **FR-002**: When no documents match the query, the system MUST return `{"results": []}` rather than an error.
- **FR-003**: The system MUST return HTTP 401 for unauthenticated search requests.
- **FR-004**: Search results MUST include only published documents; draft and ingested-state documents MUST be excluded.
- **FR-005**: Documents with `RESTRICTED` confidentiality MUST never appear in search results.
- **FR-006**: When the embedding service is unavailable, the system MUST return a non-500 error response with a descriptive message (e.g., HTTP 503 "Embedding service unavailable").
- **FR-007**: The root cause of the current 500 error MUST be identified, diagnosed, and resolved — not merely swallowed by a try/except.
- **FR-008**: Each result in the response MUST include: `document_id`, `version_id`, `chunk_id`, `score`, `snippet`, and `citation`.

### Key Entities

- **SearchRequest**: `query` (string, required), `space_ids` (optional list of UUIDs), `language` (optional string), `top_k` (int, default 10).
- **SearchResult**: `document_id`, `version_id`, `chunk_id`, `score` (0.0–1.0), `snippet` (truncated text), `citation` (dict with document title and source).
- **Chunk**: A segment of a published document's content, stored with a vector embedding for similarity search.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `POST /v1/search` with any valid query string returns HTTP 200 in 100% of authenticated requests (eliminating the current 100% failure rate).
- **SC-002**: Search completes and returns a response in under 5 seconds for typical queries against the current dataset.
- **SC-003**: Zero unhandled exceptions reach the global 500 handler from the search code path after the fix.
- **SC-004**: Embedding-service failure produces a non-500 HTTP response with a meaningful error message visible to API consumers.

## Assumptions

- The Ollama embedding service is configured and reachable under normal operation; the 500 error is not solely caused by Ollama being offline (the fix should handle both infrastructure errors and any code bugs).
- The `chunks` table and its `embedding` column exist in the database (created by prior migrations); the error is not a missing-table issue.
- Authentication (JWT) is working correctly; the 500 occurs after successful auth.
- Portuguese queries (non-ASCII) are valid input and must be handled without encoding errors.
- The fix is scoped to the search code path (`/v1/search`); other endpoints are out of scope.
