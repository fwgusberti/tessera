# Data Model: Fix Document Content Display

**Date**: 2026-06-19

## No schema changes required

The `current_version_id` column already exists on the `documents` table as a nullable FK to `document_versions.id`. The bug is a missing runtime assignment — not a missing column.

---

## Existing entities (relevant fields only)

### Document

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `current_version_id` | UUID (nullable FK) | Points to the `DocumentVersion` that represents current content. **This was always populated by `publish_document` but never by `create_document` — the bug.** After the fix, it is set to the initial version's ID immediately on creation. |
| `state` | enum (`ingested` / `published` / `archived`) | Unchanged; remains `ingested` after creation |

### DocumentVersion

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `document_id` | UUID (FK → documents.id) | Owning document |
| `version_number` | int | Always `1` for the initial creation version |
| `content_markdown` | str | The content submitted in the creation form |

---

## State transition (creation flow — after fix)

```
POST /v1/documents (with content_markdown)
  → INSERT documents (state=ingested, current_version_id=NULL)
  → INSERT document_versions (version_number=1, content_markdown=<body>)
  → UPDATE documents SET current_version_id = <version.id>   ← NEW
  → COMMIT
  → GET /v1/documents/{id} returns current_version = version 1  ← now works
```

## State transition (publish flow — unchanged)

```
POST /v1/documents/{id}/publish
  → UPDATE document_versions SET approver_user_id, approved_at
  → UPDATE documents SET state=published
  → UPDATE documents SET current_version_id = <approved_version.id>  ← existing
  → COMMIT
```
