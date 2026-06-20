# Data Model: Fix Document Search Returns No Results

**Date**: 2026-06-20
**Feature**: specs/015-fix-document-search

## Affected Entities

No schema changes are required. All bugs are in application-layer code. The existing table structure is correct.

### `chunks` table (existing — no migration needed)

```sql
chunks (
    id                  UUID PRIMARY KEY,
    document_version_id UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    document_id         UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    space_id            UUID NOT NULL REFERENCES spaces(id) ON DELETE CASCADE,
    ordinal             INTEGER NOT NULL,
    text                TEXT NOT NULL,
    embedding           vector(768),          -- populated by indexing worker
    confidentiality     VARCHAR(50) NOT NULL,
    language            VARCHAR(10) NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
)
```

**Before the fix**: `embedding` is always NULL because `upsert_chunks` never executes. The `AND c.embedding IS NOT NULL` filter in the search query excludes all rows.

**After the fix**: `embedding` is populated for every chunk of every published document, enabling vector cosine similarity search.

### `documents` table (existing — no migration needed)

```
documents.title  VARCHAR(500)  -- title prepended to chunk text at indexing time
documents.state  VARCHAR(50)   -- 'published' filter already in search SQL; no change
```

## Data Flow Changes

### Indexing pipeline (after fix)

```
publish_document endpoint
  → dispatch index_document_version.delay(version_id, document_id, space_id)
      → _do_index(version_id, document_id, space_id)
          → load Document (to get title) + DocumentVersion
          → prepend "# {title}\n\n" to content_markdown
          → chunk_document(version_with_title_prefix, ...)  → []Chunk
          → OllamaEmbeddingProvider.embed([chunk.text, ...])
          → chunk.embedding = embeddings[i]
          → upsert_chunks(chunks)
              → INSERT INTO chunks (..., embedding) VALUES (..., CAST(... AS vector))
              ON CONFLICT (id) DO UPDATE SET text=..., embedding=...
          → session.commit()
```

### Search pipeline (unchanged)

```
POST /v1/search { query: "quarterly report" }
  → embed query via Ollama → query_embedding
  → SELECT ... FROM chunks c JOIN documents d ON d.id = c.document_id
    WHERE c.space_id = ANY(...) AND d.state = 'published' AND c.embedding IS NOT NULL
    ORDER BY embedding <=> query_embedding
    LIMIT 10
  → return top-k results with document_title in citation
```
