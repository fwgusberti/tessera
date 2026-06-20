# API Contracts: Documents — Owner Assignment

## POST /v1/documents

**Before fix**: `owner_user_id` was always `null` in the response.

**After fix**: `owner_user_id` in the response `document` object MUST equal the authenticated user's ID.

### Request
```
POST /v1/documents
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "space_id": "<uuid>",
  "title": "My Document",
  "language": "pt-BR",
  "confidentiality": "internal",
  "content_markdown": "# Hello",
  "tags": [],
  "frontmatter": {}
}
```

### Response (201 Created)
```json
{
  "document": {
    "id": "<uuid>",
    "space_id": "<uuid>",
    "owner_user_id": "<authenticated-user-uuid>",   ← MUST be set (not null)
    "title": "My Document",
    "state": "ingested",
    "current_version_id": "<uuid>",
    ...
  },
  "version": { ... }
}
```

**Invariant**: `document.owner_user_id` MUST equal the `sub` claim from the bearer token used in the request.

---

## POST /v1/documents/{document_id}/publish

**Before fix**: Returns 400 with `"Document has no owner"` for any document created without an owner.

**After fix**: If `document.owner_user_id` is null, the system auto-assigns the publishing user as owner, then proceeds. If it was already set, the existing owner is preserved.

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
    "owner_user_id": "<uuid>",   ← MUST be set (auto-assigned if was null)
    "state": "published",
    ...
  },
  "version": { ... }
}
```

**Invariants**:
- `document.state` MUST be `"published"` on success.
- `document.owner_user_id` MUST NOT be null on success.
- If the document had a pre-existing owner, `document.owner_user_id` MUST equal the pre-existing owner (not the publisher).

---

## GET /v1/documents/{document_id}

No contract change. The `owner_user_id` field was already present in the response schema; it will now be populated for documents created after this fix.
