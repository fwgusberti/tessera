# Quickstart Validation Guide: Fix Document Publish — Auto-Assign Owner

## Prerequisites

- API running locally (`uvicorn tessera_api.main:app --reload`)
- A registered user account (use `POST /v1/auth/register`)
- An access token from `POST /v1/auth/login`
- A space created (use the admin panel or API)

## Scenario 1: Create and immediately publish a document (the core fix)

```bash
# 1. Login and capture token
TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret123"}' \
  | jq -r '.access_token')

# 2. Create a document
SPACE_ID="<your-space-uuid>"
DOC_RESPONSE=$(curl -s -X POST http://localhost:8000/v1/documents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"space_id\": \"$SPACE_ID\",
    \"title\": \"My Test Doc\",
    \"content_markdown\": \"# Hello world\"
  }")

# Expected: document.owner_user_id is NOT null
echo $DOC_RESPONSE | jq '.document.owner_user_id'

DOC_ID=$(echo $DOC_RESPONSE | jq -r '.document.id')

# 3. Publish immediately
curl -s -X POST http://localhost:8000/v1/documents/$DOC_ID/publish \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.document.state, .document.owner_user_id'

# Expected output:
# "published"
# "<uuid of authenticated user>"
```

## Scenario 2: Existing ownerless document can be published (fallback)

This tests FR-002 — documents that exist in the database without an owner can still be published.

If you have a document with `owner_user_id = null` in the database:

```bash
DOC_ID="<id-of-ownerless-document>"
curl -s -X POST http://localhost:8000/v1/documents/$DOC_ID/publish \
  -H "Authorization: Bearer $TOKEN" \
  | jq '.document.state, .document.owner_user_id'

# Expected: state = "published", owner_user_id = <publisher's uuid>
# Should NOT return 400 "Document has no owner"
```

## Scenario 3: Existing owner is preserved on publish (FR-003)

```bash
# Get a document that already has owner_user_id set
curl -s http://localhost:8000/v1/documents/$DOC_ID \
  -H "Authorization: Bearer $DIFFERENT_USER_TOKEN" \
  | jq '.document.owner_user_id'
# Note the existing owner

# Publish as a different user
curl -s -X POST http://localhost:8000/v1/documents/$DOC_ID/publish \
  -H "Authorization: Bearer $DIFFERENT_USER_TOKEN" \
  | jq '.document.owner_user_id'
# Expected: same as the original owner, not the publisher
```

## Running Unit Tests

```bash
# Core lifecycle tests (no changes needed — already pass)
cd packages/core
python -m pytest tests/test_lifecycle.py -v

# API contract tests (new tests should be written first, then confirmed passing)
cd apps/api
python -m pytest tests/contract/test_documents.py -v
```

## Confirming the Fix

- No `400 "Document has no owner"` errors when publishing newly created documents
- `document.owner_user_id` is populated immediately after `POST /v1/documents`
- `document.state` is `"published"` after `POST /v1/documents/{id}/publish`
