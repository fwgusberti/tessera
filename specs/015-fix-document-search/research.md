# Research: Fix Document Search Returns No Results

**Date**: 2026-06-20
**Feature**: specs/015-fix-document-search

## Root Cause Analysis

### Decision: Three co-located bugs prevent search results from ever being returned

**Rationale**: Investigation of the full indexing and search pipeline (`apps/api/tessera_api/adapters/repo.py`, `apps/api/tessera_api/routers/documents.py`, `apps/workers/tessera_workers/indexing/_index.py`) reveals three compounding defects. Any one of them alone would produce zero search results; all three are present simultaneously.

**Bug 1 — `upsert_chunks` never executes the SQL statement** (`repo.py:389-407`)

```python
async def upsert_chunks(self, chunks: list[Chunk]) -> None:
    for chunk in chunks:
        _stmt = insert(...).values(...)  # noqa: F841  ← built, never executed
```

The INSERT statement is constructed but `await session.execute(_stmt)` is never called. The `# noqa: F841` comment suppresses the "assigned but never used" linter warning, masking the defect entirely. Result: no chunks are ever written to the database.

**Bug 2 — `embedding` omitted from INSERT values** (`repo.py:389-407`)

Even if execution were added, the `embedding` field is not included in the VALUES clause. The search query filters `AND c.embedding IS NOT NULL`, so all chunks would be excluded from results regardless.

**Bug 3 — `publish_document` never dispatches the indexing Celery task** (`routers/documents.py:126-177`)

The `index_document_version` Celery task exists (`workers/tessera_workers/indexing/tasks.py`) but is never triggered from the API's publish endpoint. Documents published via the API path are never enqueued for chunking and embedding. The connector sync path (`_sync.py`) also never dispatches this task.

**Alternatives considered:**
- Redesigning search to use keyword/full-text search instead of vector search — rejected; would require a new search architecture and migration
- Fixing only the execute call without the embedding field — insufficient; search would still return nothing
- Fixing only the publish dispatch without the upsert fix — chunks would be queued but silently dropped on write

---

### Decision: Prepend document title to chunk text at indexing time

**Rationale**: The `chunk_document()` function splits `version.content_markdown` only. For documents created via the API, `content_markdown` is user-supplied and may not include the document title. Since the spec requires that a search for a word from a document title returns that document (FR-001), the title must appear in the indexed text.

**Approach**: In `_do_index`, prepend `"# {document.title}\n\n"` to `content_markdown` before passing it to `chunk_document()`. The chunker then includes the title in the first chunk's text, which gets embedded. The search query will then find documents whose title contains the search term via semantic similarity.

**Alternatives considered:**
- Adding a separate dedicated "title chunk" — adds complexity; prepending to content is simpler
- Returning to a keyword/SQL LIKE search for title — out of scope for P1 fix; would change the search API contract
- Modifying the `DocumentVersion` entity to carry the title — violates constitution separation; `Document.title` already owns that data

---

### Decision: Fix `upsert_chunks` with raw SQL consistent with existing patterns

**Rationale**: The existing `search()` and `delete_by_document()` methods in `SqlChunkRepository` use raw SQL via `sqlalchemy.text()`. There is no `ChunkModel` ORM class (chunks table exists only in migrations and raw SQL). Consistency requires continuing with raw SQL for `upsert_chunks`.

**Approach**: Replace the broken `insert()` call with a parameterized `INSERT INTO chunks ... ON CONFLICT (id) DO UPDATE SET ...` raw SQL statement via `session.execute(text(...))`, matching the pattern already used by the `search` method. Include `embedding` as a parameter using PostgreSQL `CAST(... AS vector)`.

**Alternatives considered:**
- Adding a `ChunkModel` ORM class — clean long-term but out of scope for a focused bug fix; adds migration risk
- Using `sqlalchemy.dialects.postgresql.insert` properly — the `type("chunks", ...)` trick cannot produce a proper mapped table; raw SQL is more reliable here

---

### Decision: Dispatch indexing task from `publish_document` endpoint

**Rationale**: The workers package exports `index_document_version` as a Celery task. The publish endpoint must dispatch it with `index_document_version.delay(str(version_id), str(document_id), str(space_id))` after the state transition commits.

**Dependency order**: The task must be dispatched after `session.commit()` to ensure the document and version are visible to the worker's database session.

**Alternatives considered:**
- Dispatching from the domain service (`lifecycle.publish_document`) — violates DDD; domain services must not know about infrastructure tasks
- Using a database trigger or event — overly complex; Celery dispatch is the existing pattern

---

### Decision: Add "no results" message to the frontend search page

**Rationale**: FR-003 requires a "no results found" message when no documents match. Currently the search page renders nothing when `results` is an empty array (`results.length > 0` guard hides the result area entirely). A simple conditional message is needed.

**Approach**: Add a `{results.length === 0 && !loading && query.trim() && !answer && searched}` conditional block that shows "No results found." after the user has submitted at least one search. Track whether a search was submitted with a `searched` boolean state flag.
