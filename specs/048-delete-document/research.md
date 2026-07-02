# Phase 0 Research: Delete Document

## 1. Permission model

**Decision**: Add `can_delete_document(user, document, memberships, is_company_admin) -> bool` to
`packages/core/tessera_core/permissions/access.py`, returning `True` when
`document.owner_user_id == user.id` OR `effective_space_role(...) == SpaceRole.ADMIN`.

**Rationale**: The user explicitly chose "document owner + admins only" (not editors) when
asked during specification. `effective_space_role` already folds `is_company_admin` into an
implicit `SpaceRole.ADMIN` (see `access.py:150-164`), so passing the router's existing
`is_company_admin` flag through covers both space admins and platform admins with one check —
no separate platform-admin branch needed. This mirrors the existing
`can_manage_members`/`can_write_document` functions added in feature 024, keeping all
space-permission logic in one module with one calling convention.

**Alternatives considered**:
- Reuse `can_write_document` (editor/admin) directly — rejected, contradicts the user's answer;
  delete is more destructive than edit and editors should not have it.
- A bespoke check inline in the router (like `reindex_document`'s
  `if not company_admin and doc.owner_user_id != user_id`) — rejected because that pattern
  only checks *company* admin, not *space* admin, and the spec requires space admins (who may
  not be company admins) to also be able to delete. A new domain function is more correct and
  keeps the permission rule testable in isolation like its siblings.

## 2. Cascade deletion mechanics

**Decision**: Delete the `documents` row directly (`SqlDocumentRepository.delete(document_id)`
executing `DELETE FROM documents WHERE id = :document_id`) inside the request's existing
transaction. No explicit cleanup of versions, drafts, proposals, or search chunks is needed in
application code.

**Rationale**: Every table that references `documents.id` already declares
`ON DELETE CASCADE` at the database level:
- `document_versions.document_id` (`apps/api/tessera_api/adapters/models/document_version.py:25`)
- `document_drafts.document_id` (`.../document_draft.py:21`)
- `update_proposals.document_id` (`.../update_proposal.py:23`)
- `chunks.document_id` (`db/migrations/versions/0001_initial_schema.py:166`) — this is the
  pgvector-backed search index table.

Because `chunks` cascades too, deleting the `documents` row removes the document from search
**synchronously, in the same transaction** — stronger than the eventual-consistency the existing
`tessera.remove_document_index` Celery task would give (that task exists in
`apps/workers/tessera_workers/indexing/tasks.py:25` but is currently dispatched nowhere in the
codebase — it was pre-built for this kind of use case but never wired up). Using the DB cascade
instead of dispatching that task satisfies FR-005 more precisely (SC-003: zero residual content)
and needs no new Celery wiring, no worker-side test doubles, and no window where a deleted
document could still surface in search before an async job runs.

**Alternatives considered**:
- Dispatch `tessera.remove_document_index` after deleting the document row — rejected as
  redundant (chunks are already gone by the time the task would run) and it would reintroduce
  the eventual-consistency gap FR-005 explicitly avoids.
- Soft delete (add a `deleted_at` column, filter it everywhere) — rejected per spec Assumptions:
  the feature is a permanent hard delete, and soft-delete would require auditing and changing
  every existing query that reads `documents`/`chunks` to add the new filter, which is out of
  scope for "add delete button."

## 3. Confirmation UX pattern

**Decision**: Use the browser-native `window.confirm()` dialog before calling the delete
endpoint, matching the existing destructive-action pattern in
`apps/web/components/members/SpaceMembersPanel.tsx:58-66` (`handleRemove`).

**Rationale**: This is the only precedent for a destructive, confirmable action already in the
codebase. Reusing it avoids introducing a new modal/dialog component for a single button, and
keeps the interaction consistent with "remove member," which is conceptually the same shape of
action (destructive, permission-gated, needs confirmation).

**Alternatives considered**:
- A custom confirmation modal component — rejected as unnecessary scope; no existing modal
  component exists in the codebase to reuse, and building one is disproportionate to a single
  delete button.

## 4. Audit logging

**Decision**: Call the existing `write_audit(session, actor_type="user", actor_id=..., action="document_deleted", entity_type="document", entity_id=document_id, metadata={"space_id": ..., "title": ...})` helper before committing the delete, same call shape already used for `"publish"` and `"document_edited"` in `apps/api/tessera_api/routers/documents.py`.

**Rationale**: Satisfies FR-010 and the constitution's blanket audit-logging requirement
("Every state-changing action MUST emit a structured audit log recording the actor, timestamp,
and affected entity ID") using the exact mechanism already in place — no new audit
infrastructure needed. Including `title` in metadata is necessary because after deletion the
`documents` row (and therefore its title) is gone; without it, the audit trail alone could not
tell an investigator *what* was deleted, only that *something* was.

## 5. Post-delete navigation

**Decision**: On the frontend, after a successful delete, `router.push(`/spaces/${document.space_id}`)` (the existing space folder-browser page from feature 044).

**Rationale**: Satisfies FR-006 ("navigate the user away... to a page that still exists"). The
space the document belonged to is the most relevant place to land the user, and the route
already exists (`apps/web/app/spaces/[id]/page.tsx`).

**Alternatives considered**:
- Redirect to `/documents` (the flat list) — rejected as less useful; the user was just working
  in a specific space and most likely wants to keep working there.
