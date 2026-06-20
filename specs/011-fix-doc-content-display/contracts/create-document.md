# Contract: POST /v1/documents

## Request

```json
{
  "space_id": "<uuid>",
  "title": "<string, required>",
  "language": "pt-BR",
  "confidentiality": "internal",
  "content_markdown": "<string, may be empty>",
  "tags": [],
  "frontmatter": {}
}
```

## Response (201 Created)

```json
{
  "document": {
    "id": "<uuid>",
    "space_id": "<uuid>",
    "title": "<string>",
    "language": "pt-BR",
    "confidentiality": "internal",
    "state": "ingested",
    "tags": [],
    "current_version_id": "<uuid>",   ← MUST be non-null after fix
    "owner_user_id": null,
    "validity_until": null
  },
  "version": {
    "id": "<uuid>",
    "document_id": "<uuid>",
    "version_number": 1,
    "content_markdown": "<same as request body>",
    "frontmatter": {},
    "author_user_id": null,
    "approver_user_id": null,
    "approved_at": null
  }
}
```

## Invariants

1. `document.current_version_id` MUST equal `version.id` in the response.
2. `version.version_number` MUST be `1`.
3. `document.state` MUST be `"ingested"`.
4. `GET /v1/documents/{document.id}` called immediately after creation MUST return `current_version` matching `version` above.

## Unchanged invariants

- Requires valid JWT (`Authorization: Bearer <token>`). Returns 401 if missing.
- Returns 400 if `space_id` references a non-existent space (existing behaviour, unchanged).
