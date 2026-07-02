# Phase 1 Data Model: Reindex Document on Finishing an Edit

No new entities, fields, or state transitions are introduced by this
feature. It reads one existing field and reuses three existing entities
exactly as they are defined today:

- **Document** (`tessera_core.domain.entities.Document`) — only the existing
  `state: DocumentLifecycleState` and `space_id` fields are read (to decide
  whether to dispatch a reindex, and to pass as a Celery task argument).
  Nothing about `Document` changes.
- **DocumentVersion** (`tessera_core.domain.entities.DocumentVersion`) — the
  version created by `finish_document_draft` (already implemented in feature
  046) is the version whose `id` is passed to the reindex task. No change to
  this entity.
- **DocumentDraft** (`tessera_core.domain.entities.DocumentDraft`) — used
  only to detect whether the draft's content differs from the current
  version (already implemented). No change to this entity.

No database migration is required.
