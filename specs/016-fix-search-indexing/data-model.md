# Data Model: Fix Search Indexing — Worker Env + Reindex Endpoints

**Date**: 2026-06-20

No schema changes are required. This feature fixes environment configuration and adds API endpoints that dispatch existing Celery tasks against existing tables.

## Affected Entities

### Document (`documents` table)

| Field | Type | Relevant to this feature |
|-------|------|--------------------------|
| `id` | UUID | Identifies the document to reindex |
| `state` | enum (draft, published, …) | Reindex endpoint gates on `state = 'published'` |
| `current_version_id` | UUID FK → `document_versions.id` | Used to determine which version to index |
| `space_id` | UUID FK → `spaces.id` | Passed as argument to the indexing Celery task |
| `owner_user_id` | UUID FK → `users.id` | Authorization check for per-document reindex |

### DocumentVersion (`document_versions` table)

| Field | Type | Relevant to this feature |
|-------|------|--------------------------|
| `id` | UUID | Passed as `version_id` argument to the indexing task |

### Chunk (`chunks` table)

| Field | Type | Relevant to this feature |
|-------|------|--------------------------|
| `document_id` | UUID FK → `documents.id` | Used in `NOT EXISTS` subquery for bulk reindex |
| `embedding` | vector(768) | Null when indexing failed — documents with null embeddings are excluded from search |

## Data Flow: Reindex

```
POST /v1/documents/{id}/reindex  (or /v1/admin/reindex)
    │
    ├── Query: documents WHERE id = ? (per-doc) OR
    │         documents WHERE state='published' AND NOT EXISTS (chunks) (bulk)
    │
    └── Dispatch: tessera.index_document_version(version_id, document_id, space_id)
                      │
                      └── Worker: embed text → upsert chunks → session.commit()
```

## No Migrations Required

The fix is purely in application code and environment configuration. The `chunks` table, `documents` table, and all indexes remain unchanged.
