# Quickstart Validation Guide: Fix Publish — Record Approval on Existing Version

## Prerequisites

- API running locally (`uvicorn tessera_api.main:app --reload` from `apps/api/`)
- A registered user account and a valid access token
- A space with at least one document that has content (version)

## Scenario 1: Publish succeeds and returns 200 (core fix)

```bash
TOKEN="<your-access-token>"
DOC_ID="5063d8ab-fcd7-46c1-a32b-07d1d080588e"  # or any doc with content

curl -s -X POST http://localhost:8000/v1/documents/$DOC_ID/publish \
  -H "Authorization: Bearer $TOKEN" \
  | jq '{state: .document.state, approver: .version.approver_user_id, approved_at: .version.approved_at}'

# Expected output:
# {
#   "state": "published",
#   "approver": "<publisher-uuid>",
#   "approved_at": "<iso-timestamp>"
# }
# Must NOT return 500 Internal Server Error
```

## Scenario 2: Version count does not increase after publish

```bash
# Count versions before publish
curl -s http://localhost:8000/v1/documents/$DOC_ID/versions \
  -H "Authorization: Bearer $TOKEN" | jq '.versions | length'

# Publish
curl -s -X POST http://localhost:8000/v1/documents/$DOC_ID/publish \
  -H "Authorization: Bearer $TOKEN" > /dev/null

# Count versions after publish — MUST be same number
curl -s http://localhost:8000/v1/documents/$DOC_ID/versions \
  -H "Authorization: Bearer $TOKEN" | jq '.versions | length'
```

## Scenario 3: Error paths return 4xx not 5xx

```bash
# Document with no versions → 400
EMPTY_DOC_ID="<uuid-of-doc-with-no-versions>"
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/v1/documents/$EMPTY_DOC_ID/publish \
  -H "Authorization: Bearer $TOKEN"
# Expected: 400

# Non-existent document → 404
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/v1/documents/00000000-0000-0000-0000-000000000000/publish \
  -H "Authorization: Bearer $TOKEN"
# Expected: 404
```

## Running Contract Tests

```bash
cd apps/api
.venv/bin/python -m pytest tests/contract/test_documents.py -v --no-cov
```

All tests must pass. Key new test: `test_publish_document_records_approval_without_creating_version`.
