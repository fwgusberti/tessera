# Quickstart: Validate Fix — Document Content Display

**Date**: 2026-06-19

## Prerequisites

- API server running (`uvicorn apps/api/tessera_api.main:app --reload` or via Docker Compose)
- Valid JWT for an authenticated user
- At least one Space exists

## Scenario 1: Content visible immediately after creation (Happy Path)

```bash
# 1. Create a document with content
curl -s -X POST http://localhost:8000/v1/documents \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "space_id": "<your-space-id>",
    "title": "Test Doc",
    "language": "pt-BR",
    "confidentiality": "internal",
    "content_markdown": "# Hello\n\nThis is my test content.",
    "tags": [],
    "frontmatter": {}
  }' | jq '{doc_id: .document.id, current_version_id: .document.current_version_id, version_id: .version.id}'
```

**Expected output** (before fix: `current_version_id` is `null`; after fix: non-null UUID equal to `version_id`):

```json
{
  "doc_id": "...",
  "current_version_id": "same-as-version_id",
  "version_id": "same-as-current_version_id"
}
```

```bash
# 2. Fetch the document and verify content is returned
curl -s http://localhost:8000/v1/documents/<doc_id> \
  -H "Authorization: Bearer <JWT>" | jq '{current_version: .current_version}'
```

**Expected output** (before fix: `current_version: null`; after fix: object with `content_markdown`):

```json
{
  "current_version": {
    "id": "...",
    "version_number": 1,
    "content_markdown": "# Hello\n\nThis is my test content.",
    ...
  }
}
```

## Scenario 2: Empty content — "No content available" remains correct

```bash
curl -s -X POST http://localhost:8000/v1/documents \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "space_id": "<your-space-id>",
    "title": "Empty Doc",
    "language": "pt-BR",
    "confidentiality": "internal",
    "content_markdown": "",
    "tags": [],
    "frontmatter": {}
  }' | jq '.document.current_version_id'
```

**Expected**: A non-null UUID. The frontend will show the (empty) content field, not the "No content available" placeholder.

> Note: An empty `content_markdown` is a valid state. The "No content available" placeholder should only appear when `current_version` is `null` (no version linked at all), not when content is an empty string. See FR-004.

## Scenario 3: Run contract tests

```bash
cd apps/api
python -m pytest tests/contract/test_documents.py -v
```

**Expected**: All tests pass, including the new regression test asserting `set_current_version` is called.

## Scenario 4: Frontend smoke test

1. Log in → navigate to `/documents`
2. Click "Add Document", fill in title + space + content
3. Click "Save" → modal closes, new document row appears in list
4. Click the document title → detail page opens
5. Verify the "Current Content" section shows the markdown text entered in step 2

**Expected**: Content is visible without clicking "Publish".

## Verify publish flow is unaffected

After the fix, publish an ingested document and confirm:
- State transitions to `published`
- `current_version_id` still points to the (now approved) version
- No regression in publish endpoint behaviour
