# Phase 0 Research: Reindex Document on Finishing an Edit

No `NEEDS CLARIFICATION` markers were left in the Technical Context — this
feature reuses existing infrastructure end to end. The two decisions below
were the only ones with more than one reasonable option.

## Decision 1: Reuse the existing `tessera.index_document_version` task

**Decision**: Dispatch the same Celery task (`tessera.index_document_version`,
called with `[version_id, document_id, space_id]`) that `publish_document`
and `reindex_document` already dispatch, rather than introducing a new task
or a synchronous indexing call.

**Rationale**: The task already does exactly what's needed — index one
version's content for one document/space. Two call sites already dispatch it
identically; adding a third with the same signature is the smallest possible
change and guarantees identical indexing behavior (chunking, embedding,
tenant scoping) across publish, manual reindex, and finish-edit.

**Alternatives considered**:
- *New dedicated task for edit-triggered reindexing*: Rejected — would
  duplicate the existing task's logic for no behavioral benefit; the content
  being indexed (a document version's markdown) is identical regardless of
  what triggered the reindex.
- *Synchronous indexing inline in the request*: Rejected — would block the
  finish-edit response on embedding/indexing latency, violating FR-005 (must
  not delay the user) and diverging from the fire-and-forget pattern already
  established for publish/reindex.

## Decision 2: Inline the publish-state check in the router, not a new service function

**Decision**: Add the `doc.state == DocumentLifecycleState.PUBLISHED` guard
directly inline in `finish_document_draft`, matching the existing inline
guard (`doc.state != DocumentLifecycleState.PUBLISHED`) already written in
`reindex_document` in the same file.

**Rationale**: The condition is a single field comparison already expressed
this way twice in the same module (`publish_document` implicitly always
publishes-then-indexes; `reindex_document` explicitly checks state). Extracting
a shared helper for a one-line, non-reused-elsewhere condition would be
premature abstraction for a three-call-site pattern that's already legible
inline.

**Alternatives considered**:
- *Domain-layer `should_reindex(document) -> bool` helper in
  `tessera_core`*: Rejected for now — no second consumer outside the router
  exists yet, and the condition is trivial; would add an indirection without
  removing any duplication that matters at this scale.
