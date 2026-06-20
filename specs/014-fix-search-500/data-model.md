# Data Model: Fix Search Endpoint 500 Error

**Feature**: 014-fix-search-500  
**Date**: 2026-06-20

No schema changes are introduced by this fix. All entities below are existing.

## Existing Entities Involved

### SearchRequest (Pydantic input model — unchanged)

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| query | str | Yes | — | Natural-language query text |
| space_ids | list[UUID] \| None | No | None | Filter to specific spaces; None = all accessible |
| language | str \| None | No | None | Reserved for future language filtering |
| top_k | int | No | 10 | Maximum results to return |

**Validation**: `query` must be non-empty (Pydantic enforces via `str` type; router receives 422 for missing field).

### SearchResult (Pydantic output model — unchanged)

| Field | Type | Notes |
|-------|------|-------|
| document_id | UUID | The document the chunk belongs to |
| version_id | UUID | The specific document version |
| chunk_id | UUID | The individual text chunk |
| score | float | Cosine similarity score (0.0–1.0) |
| snippet | str | First 300 chars of chunk text |
| citation | dict | `{chunk_id, document_version_id, quote, score}` |

### Chunk (PostgreSQL table — unchanged)

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| document_version_id | UUID FK → document_versions | |
| document_id | UUID FK → documents | |
| space_id | UUID FK → spaces | |
| ordinal | integer | Position in document |
| text | text | Raw chunk content |
| embedding | vector(768) | Ollama nomic-embed-text embedding (may be NULL for un-ingested chunks) |
| confidentiality | varchar(50) | internal / confidential / restricted |
| language | varchar(10) | e.g., pt-BR |
| created_at | timestamptz | |

**HNSW index**: `ix_chunks_embedding_hnsw` on `embedding vector_cosine_ops` (m=16, ef_construction=64).

**Filter invariants enforced at query time**:
- `c.embedding IS NOT NULL` — skips un-ingested chunks
- `d.state = 'published'` — excludes draft/ingested documents
- `c.confidentiality = ANY(CAST(:allowed_confidentiality AS text[]))` — excludes RESTRICTED and levels above user ceiling

## Parameter Binding Contract (internal)

The `SqlChunkRepository.search()` method passes the following bind parameters to the raw SQL query:

| Parameter name | Python type | PostgreSQL cast | Example value |
|----------------|-------------|-----------------|---------------|
| `:embedding` | str | `CAST(... AS vector)` | `'[0.12, 0.34, ...]'` (768 floats) |
| `:space_ids` | str | `CAST(... AS uuid[])` | `'{uuid1,uuid2}'` |
| `:allowed_confidentiality` | str | `CAST(... AS text[])` | `'{internal,confidential}'` |
| `:top_k` | int | direct | `10` |

**Change in this fix**: `:allowed_confidentiality` is now serialized to `'{val1,val2}'` string (same pattern as `:space_ids`) instead of passing a Python `list`.
