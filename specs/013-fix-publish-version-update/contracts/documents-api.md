# API Contract: POST /v1/documents/{document_id}/publish

## Before Fix

- Returns **500 Internal Server Error** for all documents (constraint violation on version insert)

## After Fix

- Returns **200 OK** with the published document and its version

### Request
```
POST /v1/documents/{document_id}/publish
Authorization: Bearer <access_token>
```

### Response (200 OK)
```json
{
  "document": {
    "id": "<uuid>",
    "state": "published",
    "owner_user_id": "<uuid>",
    "current_version_id": "<version-uuid>",
    ...
  },
  "version": {
    "id": "<version-uuid>",
    "document_id": "<uuid>",
    "version_number": 1,
    "content_markdown": "...",
    "approver_user_id": "<publisher-uuid>",   ← MUST be set (not null)
    "approved_at": "<iso-timestamp>",          ← MUST be set (not null)
    ...
  }
}
```

### Invariants

- `document.state` MUST be `"published"` on success.
- `version.approver_user_id` MUST equal the authenticated publisher's user ID.
- `version.approved_at` MUST be a non-null ISO 8601 timestamp.
- The total count of `document_versions` rows for this document MUST NOT increase during publish (no new row created).
- `version.version_number` MUST be unchanged (the same version that existed before publish).

### Error Responses (4xx — not 5xx)

| Status | Condition |
|---|---|
| 404 | Document not found |
| 400 | Document has no content versions |
| 400 | Document in an invalid state for publishing (e.g., expired) |
