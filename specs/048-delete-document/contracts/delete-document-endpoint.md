# Contract: `DELETE /v1/documents/{document_id}`

New endpoint added to the existing documents router
(`apps/api/tessera_api/routers/documents.py`), following the same auth,
tenant-scoping, and error-shape conventions already used by the other
`/documents/{document_id}/*` handlers.

## Request

No body. Requires `CompanyMemberContext` (same dependency used by the draft
endpoints and `reindex_document`), so both `company_id` and the caller's
`CompanyMembership` (for `is_company_admin`) are available.

## Resolution & authorization

1. Resolve the document via
   `SqlDocumentRepository.get_by_id_for_company(document_id, company_id)`. A
   miss returns the generic
   `404 {"error": {"code": "not_found", "message": "Not found"}}` and writes
   a `cross_tenant_denied` audit record — identical to every other handler
   in this router (indistinguishable-404 for cross-tenant access, and this
   is also what a *second* delete of an already-deleted document sees, per
   spec Edge Cases).
2. Load the caller's `User` and the document's space `SpaceMembership` list
   (same pattern as `_resolve_document_for_draft_write`).
3. Enforce `can_delete_document(actor, document, memberships, is_company_admin=company_admin)`
   (new function, see [data-model.md](../data-model.md#new-domain-permission-function)).
   Returns `403 {"detail": "You must be the document owner or a space admin to delete this document"}`
   if denied — same shape as the existing write-access 403s in this router.

## Response 200

```json
{ "deleted": true, "document_id": "uuid" }
```

Matches the existing `{"queued": true, "document_id": ...}` ack shape used
by `POST /documents/{id}/reindex` — the frontend only needs a success signal
before navigating away, not the (now-deleted) document body.

## Side effects

- `DELETE FROM documents WHERE id = :document_id`, which cascades at the
  database level to `document_versions`, `document_drafts`,
  `update_proposals`, and `chunks` (search index) — see
  [data-model.md](../data-model.md) and
  [research.md §2](../research.md#2-cascade-deletion-mechanics). No
  application-level cleanup of those tables is needed.
- One audit record: `action="document_deleted"`, `entity_type="document"`,
  `entity_id=document_id`, `metadata={"space_id": str(document.space_id), "title": document.title}`
  (title/space_id captured in metadata because the row itself will be gone).
- No Celery dispatch (unlike publish/reindex/finish-draft) — the DB cascade
  already makes the document unsearchable synchronously, in the same
  transaction.

## Not applicable / no change elsewhere

- `GET /documents/{id}`, `GET /documents/{id}/versions`,
  `GET /documents?space_id=...`: unchanged. After a successful delete they
  naturally 404 / omit the document, since the underlying rows are gone —
  no extra filtering logic needed anywhere else.
- Search (`POST /v1/search` or equivalent): unchanged code path; results
  simply stop including the deleted document once its `chunks` rows are
  cascade-deleted.
