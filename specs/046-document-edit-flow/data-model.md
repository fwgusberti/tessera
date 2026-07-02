# Data Model: Document Edit Flow

## New entity: DocumentDraft

Represents the in-progress, autosaved working state of a document edit
session. One row per `Document` (upserted); superseded by a new
`DocumentVersion` and deleted when the session finalizes.

| Field              | Type                  | Notes                                                                 |
|--------------------|-----------------------|------------------------------------------------------------------------|
| `document_id`      | UUID, PK, FK→documents.id (ON DELETE CASCADE) | One draft per document; upsert on every autosave. |
| `content_markdown` | Text                  | Latest autosaved Markdown source.                                     |
| `editor_user_id`   | UUID, FK→users.id     | Last user who autosaved; becomes `author_user_id` on the finalized version. |
| `started_at`       | timestamptz           | Set once, when the draft row is first created.                        |
| `last_autosaved_at`| timestamptz           | Updated on every autosave tick; used client-side for "resume draft" messaging. |

No `company_id` column: tenant scoping is always derived by joining through
`documents.space_id → spaces.company_id`, matching how `Document` and
`DocumentVersion` are already scoped (`SqlDocumentRepository.get_by_id_for_company`).
Every repository method on the new `SqlDocumentDraftRepository` MUST accept
and validate `company_id` via that same join — no method may accept a bare
`document_id` (Constitution VI).

**Relationships**: `Document 1 —— 0..1 DocumentDraft` (a document has at most
one active draft at a time). `Document 1 —— * DocumentVersion` (unchanged
from today).

**Lifecycle**:
1. First autosave for a document with no existing draft → row created
   (`started_at` = `last_autosaved_at` = now).
2. Subsequent autosaves → same row updated (`content_markdown`,
   `editor_user_id`, `last_autosaved_at`).
3. Finalization (FR-009/FR-010):
   - If the draft's `content_markdown` differs from the document's current
     version content → create a new `DocumentVersion`
     (`version_number` = current max + 1, `content_markdown` = draft
     content, `author_user_id` = draft's `editor_user_id`, `frontmatter`
     carried over unchanged from the previous current version), set
     `Document.current_version_id` to the new version, write one
     `document_edited` audit record, delete the draft row.
   - If content is unchanged (including the "opened and left without
     editing" case, FR-011) → delete the draft row, no new version, no
     audit record.

## Unchanged entities (reused as-is)

- **Document** (`apps/api/tessera_api/adapters/models/document.py`) — no
  column changes. `current_version_id` continues to represent the
  document's live/current content; it is only repointed at finalization,
  never mid-session, so other viewers never see partially-typed content.
- **DocumentVersion** (`apps/api/tessera_api/adapters/models/document_version.py`)
  — no column changes. A finalized edit session produces exactly one new
  row here, same shape as versions created any other way.
- **SpaceMembership** / `SpaceRole` (VIEWER/EDITOR/ADMIN) — reused unchanged
  to determine edit access via `can_write_document`.

## Migration

New Alembic migration `0014_document_drafts.py` (next sequential number
after `0013_backfill_space_memberships.py`) creating the `document_drafts`
table as specified above, with an index on `document_id` (implicit via
primary key) and a foreign key to `documents(id)` with `ON DELETE CASCADE`
(so deleting a document cleans up any in-progress draft automatically).
