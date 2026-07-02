# Contracts: Document Draft Endpoints

Three new endpoints added to the existing documents router
(`apps/api/tessera_api/routers/documents.py`), following the same auth,
tenant-scoping, and error-shape conventions already used by
`GET /documents/{id}`, `GET /documents/{id}/versions`, and
`POST /documents/{id}/publish`.

All three:
- Resolve the document via `SqlDocumentRepository.get_by_id_for_company(document_id, company_id)` first; a miss returns the generic `404 {"error": {"code": "not_found", "message": "Not found"}}` and writes a `cross_tenant_denied` audit record, exactly like the existing handlers (indistinguishable-404 for cross-tenant access).
- Require `CompanyMemberContext` and enforce `can_write_document(actor, document.space_id, memberships, is_company_admin=company_admin)`, returning `403` (same shape as `POST /documents`'s check) if the caller is not an effective EDITOR/ADMIN in the document's space.

## `GET /v1/documents/{document_id}/draft`

Fetch the active draft for a document, if one exists — used when opening the
edit view, to resume any in-progress or abandoned session.

**Response 200**:
```json
{ "draft": null }
```
or
```json
{
  "draft": {
    "content_markdown": "...",
    "editor_user_id": "uuid",
    "started_at": "2026-07-02T10:00:00Z",
    "last_autosaved_at": "2026-07-02T10:04:12Z"
  }
}
```
A missing draft is a normal state (200 + `null`), not an error — the
frontend falls back to the document's current version content.

## `PUT /v1/documents/{document_id}/draft`

Autosave in-progress content. Called periodically (debounced) while the edit
view is open.

**Request**:
```json
{ "content_markdown": "..." }
```

**Response 200**: `{ "draft": { ...same shape as GET... } }`

Upserts the single `document_drafts` row for this document (creates it on
first call, updates it on every subsequent call — see data-model.md for the
"last session wins" rationale). Does not touch `DocumentVersion` or
`Document.current_version_id`, and does not write an audit record (see
research.md §7).

## `POST /v1/documents/{document_id}/draft/finish`

Finalize the current editing session. Called by the frontend when the user
explicitly leaves the edit view, on `pagehide`/`beforeunload`, or when the
client-side inactivity timer elapses.

**Response 200**, no version created (no draft existed, or draft content is
unchanged from the current version — FR-011):
```json
{ "version": null }
```

**Response 200**, version created:
```json
{
  "document": { ...updated Document, current_version_id now points to the new version... },
  "version": { ...new DocumentVersion... }
}
```

Side effects when a version is created: new `DocumentVersion` row
(`version_number` = current max + 1), `Document.current_version_id`
repointed to it, the `document_drafts` row deleted, one `document_edited`
audit record written (`entity_type="document"`, `entity_id=document_id`,
`metadata={"version_id": ..., "editor_user_id": ...}`). This endpoint is
idempotent from the caller's perspective: calling it again with no draft
present is a harmless no-op (`{"version": null}`).
