# Feature Specification: Fix Search Still Returns No Results After Spec-015 Fixes

**Feature Branch**: `016-fix-search-indexing`

**Created**: 2026-06-20

**Status**: Draft

**Input**: User description: "Im still cant search for documents"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Search Returns Matching Documents (Priority: P1)

A user publishes a document and then searches for a word from its title. The search still returns no results even after the spec-015 fixes. The root cause is that the Celery worker is started without the `OLLAMA_BASE_URL` environment variable, so it falls back to `http://ollama:11434` (the Docker internal hostname), which is unreachable in local development. Embedding fails silently; chunks are never stored; search always returns empty.

**Why this priority**: Search is non-functional for all local development. Until this is fixed no one can validate the feature end-to-end locally.

**Independent Test**: Start the stack with `make dev`, publish a document, wait 5 seconds, and search for a title keyword — the document must appear in results.

**Acceptance Scenarios**:

1. **Given** the stack is started with `make dev`, **When** a user publishes a document titled "Budget Review" and waits ~5 seconds, **Then** searching for "budget" returns that document in results.
2. **Given** the stack is started with `make dev`, **When** the worker attempts to embed text for indexing, **Then** it successfully reaches Ollama at `localhost:11434` without a connection error.
3. **Given** a previously published document whose chunks were never stored (published before spec-015 fix or with a broken worker), **When** a user triggers re-indexing via the admin API, **Then** the document becomes searchable.

---

### User Story 2 - Re-index Already Published Documents (Priority: P2)

Documents that were published while the indexing pipeline was broken have no chunks in the database. Users need a way to trigger re-indexing of those documents without re-publishing them.

**Why this priority**: After the P1 fix, the worker will work for newly published documents, but existing published documents remain unsearchable until explicitly re-indexed.

**Independent Test**: With an existing published document that has no chunks, trigger re-indexing and verify the document then appears in search results.

**Acceptance Scenarios**:

1. **Given** a published document with no indexed chunks, **When** the document owner makes a POST request to `/v1/documents/{document_id}/reindex`, **Then** the indexing task is dispatched and the document is searchable after the worker processes it.
2. **Given** a document that does not exist, **When** a POST request is made to `/v1/documents/{document_id}/reindex`, **Then** the API returns 404.
3. **Given** an authenticated user who is not the document owner and not a space admin, **When** they make a POST request to `/v1/documents/{document_id}/reindex`, **Then** the API returns 403.

---

### User Story 3 - Bulk Recovery Reindex (Priority: P2)

An operator needs to recover all published documents that were never indexed (due to the broken indexing pipeline). Rather than calling the per-document reindex endpoint for each affected document, they call a single bulk endpoint that dispatches indexing tasks for every published document with zero chunks.

**Why this priority**: Without bulk reindex, recovery from the broken-pipeline period is manual and error-prone. This endpoint makes recovery a single API call.

**Independent Test**: With several published documents that have no chunks, call `POST /v1/admin/reindex` and verify each document becomes searchable after the worker processes it.

**Acceptance Scenarios**:

1. **Given** 3 published documents with no chunks and 1 published document with existing chunks, **When** a system admin calls `POST /v1/admin/reindex`, **Then** the response returns `{"dispatched": 3}` and all 3 documents become searchable after the worker runs.
2. **Given** a non-admin authenticated user, **When** they call `POST /v1/admin/reindex`, **Then** the API returns 403.

---

### Edge Cases

- What happens if Ollama is still unavailable when the worker processes the indexing task — does the task fail gracefully with a logged error, or crash silently?
- What happens if a document has empty content — is an empty chunk stored, or is it skipped?
- What happens if re-indexing is triggered while the document is in draft state?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Celery worker MUST be started with `OLLAMA_BASE_URL=http://localhost:11434` in local development (both `Makefile` `workers` target and `scripts/dev.sh`).
- **FR-002**: The `docker-compose.yml` worker service MUST also have `OLLAMA_BASE_URL` explicitly set to `http://ollama:11434` so it is visible and intentional (not relying on the code default).
- **FR-003**: When the indexing task fails to reach the embedding service, the error MUST be logged with enough detail (document_id, error message) to diagnose the failure.
- **FR-004**: The API MUST expose a `POST /v1/documents/{document_id}/reindex` endpoint that dispatches the indexing Celery task for an existing published document.
- **FR-005**: The reindex endpoint MUST require authentication; only the document owner or a user with admin rights in the document's space may trigger reindexing — all other authenticated users receive 403. Return 404 if the document does not exist.
- **FR-006**: The reindex endpoint MUST return 400 if the document is in draft state (only published documents can be reindexed).
- **FR-007**: The API MUST expose a `POST /v1/admin/reindex` endpoint that dispatches indexing tasks for all published documents that currently have zero chunks stored. This endpoint MUST require authentication; only users with a system-admin role may call it, and all other authenticated users receive 403.
- **FR-008**: The bulk reindex endpoint MUST return the count of documents whose indexing tasks were dispatched so the caller can confirm the operation scope.

### Key Entities *(include if feature involves data)*

- **Document**: Has a state (draft/published). Only published documents can be indexed and searched.
- **Chunk**: A vector-indexed unit of a document's content. Created during indexing; absent when indexing has never run or failed.
- **Indexing Task**: A Celery background task that embeds a document version and stores chunks. Fails if Ollama is unreachable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After `make dev`, publishing a document and waiting ≤10 seconds, searching for a title keyword returns that document in results 100% of the time (assuming Ollama is healthy).
- **SC-002**: The re-index endpoint allows previously un-indexed published documents to become searchable within ≤10 seconds of the request.
- **SC-003**: Worker indexing failures appear in the worker log with document_id and error details — zero silent failures.
- **SC-004**: `make dev` and `make workers` both start the worker with a correct `OLLAMA_BASE_URL` for local development.
- **SC-005**: Calling `POST /v1/admin/reindex` dispatches indexing tasks for exactly the number of published documents with zero chunks, and all of those documents are searchable within ≤10 seconds of the worker processing them.

## Clarifications

### Session 2026-06-20

- Q: Who is authorized to trigger the reindex endpoint? → A: Only the document owner or a user with admin rights in the document's space; all other authenticated users receive 403.
- Q: Should there be a bulk reindex endpoint for recovery, or per-document only? → A: Add `POST /v1/admin/reindex` that re-queues all published documents with zero chunks.

## Assumptions

- Ollama is reachable at `http://localhost:11434` in local development (started by `make infra` or `make dev`).
- In Docker Compose, Ollama is reachable at `http://ollama:11434` by the worker container.
- The `nomic-embed-text` model is already pulled by the Ollama container startup (as configured in `docker-compose.yml`).
- Documents published before this fix have zero chunks in the database and will need to be re-indexed.
- Authentication is already in place; the reindex endpoint uses the same auth mechanism as publish.
