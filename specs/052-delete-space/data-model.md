# Data Model: Delete Space

No schema changes. This documents the existing entities involved in the cascade and how deletion propagates through them.

## Entities in the deletion cascade

| Entity | Table | Relation to Space | Delete behavior |
|---|---|---|---|
| Space (target + descendants) | `spaces` | `parent_space_id → spaces.id` (self-referential, `ON DELETE SET NULL`) | Resolved via recursive CTE, then removed in one bulk `DELETE ... WHERE id IN (subtree_ids)`. `SET NULL` never fires because every descendant is included in the same statement. |
| Document | `documents` | `space_id → spaces.id` (`ON DELETE CASCADE`) | Cascades automatically once its owning space row is deleted. |
| DocumentVersion | `document_versions` | `document_id → documents.id` (`ON DELETE CASCADE`) | Cascades transitively via Document. |
| DocumentDraft | `document_drafts` | `document_id → documents.id` (`ON DELETE CASCADE`) | Cascades transitively via Document. |
| Chunk (search index) | `chunks` | `document_id → documents.id` and `space_id → spaces.id` (both `ON DELETE CASCADE`) | Cascades transitively via Document or directly via Space; either path removes it. |
| UpdateProposal | `update_proposals` | `document_id → documents.id` (`ON DELETE CASCADE`) | Cascades transitively via Document. |
| SpaceMembership | `space_memberships` | `space_id → spaces.id` (`ON DELETE CASCADE`) | Cascades automatically. |
| RolePermission | `role_permissions` | `space_id → spaces.id` (`ON DELETE CASCADE`) | Cascades automatically. |
| Connector | `connectors` | `space_id → spaces.id` (`ON DELETE CASCADE`) | Cascades automatically; its own `source_artifacts` cascade via `connector_id → connectors.id` (`ON DELETE CASCADE`). |
| Deletion audit entry | `audit_records` | `entity_id` is a bare UUID column (no FK) | Written *before* commit, in the same transaction as the delete; survives the space's removal since there is no foreign key to enforce. |

## New value shape (no new table)

`SqlSpaceRepository.delete_subtree(space_id: UUID) -> tuple[int, int]`

Returns `(deleted_space_count, deleted_document_count)`:
- `deleted_space_count`: size of the resolved subtree, including the target space itself.
- `deleted_document_count`: `COUNT(*)` of `documents` rows whose `space_id` is in the subtree, taken *before* the delete executes.

No new Pydantic domain model is introduced for this return value — a plain tuple is sufficient for the one caller (`SpaceHierarchyService.delete`), which turns it into the audit metadata and the HTTP response body.

## Validation rules (enforced in `SpaceHierarchyService.delete`)

- Target space MUST resolve within the caller's `company_id` (`ValueError("not_found")` otherwise → 404).
- Caller MUST hold `SpaceRole.ADMIN` on the target space, or `is_company_admin` MUST be `True` (`PermissionError` otherwise → 403).
- No additional validation is needed beyond existence + authorization: unlike `create`/`rename`, deletion has no user-supplied fields to validate.

## State transitions

None — deletion is a terminal, irreversible removal, not a lifecycle state change (unlike `DocumentLifecycleState`).
