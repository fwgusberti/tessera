# Contract Delta: `POST /v1/documents/{document_id}/draft/finish`

This feature does not change the endpoint's request shape, response shape,
status codes, or auth/tenant-scoping rules documented in
`specs/046-document-edit-flow/contracts/draft-endpoints.md`. It adds exactly
one conditional side effect after a new version is created.

## Side effect added

When `finish_document_draft` creates a new `DocumentVersion` (i.e. the
response body is the "version created" shape, not `{"version": null}`), the
handler now also checks the document's current lifecycle state:

- **If `document.state == PUBLISHED`**: dispatch
  `get_celery_app().send_task("tessera.index_document_version", args=[str(new_version.id), str(document_id), str(document.space_id)])` —
  identical call shape to the existing dispatch in `publish_document` and
  `reindex_document`.
- **If `document.state != PUBLISHED`**: no dispatch. (Matches the existing
  rule enforced in `reindex_document` that only published documents can be
  reindexed.)
- **If no new version was created** (no draft existed, or draft content is
  unchanged — response is `{"version": null}`): no dispatch, regardless of
  document state.

## Not changed

- Request body: none (unchanged — `draft/finish` takes no body).
- Response body shape: unchanged in both the "no version" and "version
  created" cases.
- Status codes: unchanged (200 success, 403 write-access denied, 404
  cross-tenant/not-found).
- Auth / tenant scoping: unchanged — resolution still goes through
  `_resolve_document_for_draft_write` before this logic runs.

## Failure mode

If the Celery dispatch call itself raises (e.g., broker unavailable), that
is the same fire-and-forget risk that already exists for
`publish_document`/`reindex_document` today — out of scope for this fix to
change, per FR-006 (dispatch failure must not roll back or block the
already-committed version).
