# Phase 1 Data Model: Delete Document

No new tables, columns, or migrations. This feature deletes rows from existing entities; it does
not add any.

## Entities touched by a deletion

| Entity | Table | Effect of deleting a `Document` |
|---|---|---|
| Document | `documents` | Row deleted directly by the new repository method. |
| DocumentVersion | `document_versions` | Cascade-deleted (`ON DELETE CASCADE` on `document_id`). |
| DocumentDraft | `document_drafts` | Cascade-deleted (`ON DELETE CASCADE` on `document_id`, PK). |
| UpdateProposal | `update_proposals` | Cascade-deleted (`ON DELETE CASCADE` on `document_id`). |
| Chunk (search index) | `chunks` | Cascade-deleted (`ON DELETE CASCADE` on `document_id`) — this is what removes the document from search (FR-005). |
| AuditRecord | `audit_records` | New row **inserted** (not touched by cascade — `entity_id` is a plain UUID column, not a foreign key, so the audit trail survives the document's deletion, satisfying FR-010). |

## New repository method

`DocumentRepository.delete(document_id: UUID) -> None` (port:
`packages/core/tessera_core/ports/repositories/document.py`; implementation:
`apps/api/tessera_api/adapters/repositories/document.py`) — executes
`DELETE FROM documents WHERE id = :document_id`. No return value: the router already holds the
`Document` it needs (title, space_id) from the lookup it performed before deleting, for the
audit metadata and the 404 case.

## New domain permission function

`can_delete_document(user: User, document: Document, memberships: list[SpaceMembership], is_company_admin: bool = False) -> bool`
in `packages/core/tessera_core/permissions/access.py`, alongside `can_write_document` and
`can_manage_members`. See [research.md](./research.md#1-permission-model) for the rule and
rationale.

## State transitions

None. Deletion is not a `DocumentLifecycleState` transition — a document is removed outright
regardless of its current state (`ingested`, `published`, or `archived`), per spec Edge Cases.
