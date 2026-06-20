# API Contract: Reindex Endpoints

**Date**: 2026-06-20

## POST /v1/documents/{document_id}/reindex

Dispatch an indexing task for a single published document.

### Authorization

Requires a valid JWT. The caller must be either:
- The document owner (`owner_user_id` matches the caller's user ID), or
- A system admin (`is_admin: true` in JWT claims).

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `document_id` | UUID | The document to reindex |

### Request Body

None.

### Responses

| Status | Condition | Body |
|--------|-----------|------|
| 200 OK | Task dispatched | `{"queued": true, "document_id": "<uuid>"}` |
| 400 Bad Request | Document is not in published state | `{"detail": "Only published documents can be reindexed"}` |
| 400 Bad Request | Document has no versions | `{"detail": "No versions to index"}` |
| 403 Forbidden | Caller is not owner or admin | `{"detail": "Only the document owner or an admin may reindex"}` |
| 404 Not Found | Document does not exist | (no body) |

### Notes

- The endpoint dispatches the Celery task asynchronously. A 200 response means the task was queued, not that indexing is complete.
- The document will be searchable after the worker processes the task (typically within a few seconds if Ollama is healthy).

---

## POST /v1/admin/reindex

Dispatch indexing tasks for all published documents that currently have zero chunks stored.

### Authorization

Requires a valid JWT with `is_admin: true`. All other authenticated users receive 403.

### Request Body

None.

### Responses

| Status | Condition | Body |
|--------|-----------|------|
| 200 OK | Tasks dispatched (may be zero) | `{"dispatched": <count>}` |
| 403 Forbidden | Caller is not a system admin | `{"detail": "Admin required"}` |

### Notes

- If all published documents already have chunks, `{"dispatched": 0}` is returned — this is not an error.
- Documents that are in draft state or have no `current_version_id` are skipped.
- Tasks are dispatched asynchronously; full reindexing time depends on the number of documents and Ollama throughput.
