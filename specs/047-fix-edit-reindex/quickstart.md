# Quickstart Validation Guide: Reindex Document on Finishing an Edit

## Prerequisites

- Stack running locally (`make dev`), including the API, the Celery worker,
  and Ollama for embeddings (see feature 016 for the known
  `OLLAMA_BASE_URL` gotcha if search returns nothing at all).
- A registered user with write access to a space, and a valid access token.
- A **published** document in that space (`state == "published"`).

## Scenario 1: Editing a published document updates search (core fix, US1)

```bash
TOKEN="<your-access-token>"
DOC_ID="<published-doc-id>"

# 1. Start an edit session and change the content to include a distinctive word
curl -s -X PUT http://localhost:8000/v1/documents/$DOC_ID/draft \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"content_markdown": "# Doc\n\nContains the word zzyzxquokka."}' | jq

# 2. Finish the edit session — this creates a new version
curl -s -X POST http://localhost:8000/v1/documents/$DOC_ID/draft/finish \
  -H "Authorization: Bearer $TOKEN" | jq '{version_id: .version.id}'

# 3. Wait for indexing (matches SC-001's 5s target), then search
sleep 5
curl -s -X POST http://localhost:8000/v1/search \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query": "zzyzxquokka"}' | jq '.results[].document_id'
# Expected: DOC_ID appears in the results
```

## Scenario 2: No-op finish triggers no reindex (US2)

```bash
# Finish immediately with no prior PUT /draft call (or content identical to current version)
curl -s -X POST http://localhost:8000/v1/documents/$DOC_ID/draft/finish \
  -H "Authorization: Bearer $TOKEN" | jq
# Expected: {"version": null}
# Verify no new Celery task was enqueued (check worker logs for
# "tessera.index_document_version" — no new entry should appear)
```

## Scenario 3: Editing an unpublished document triggers no reindex (US3)

```bash
UNPUBLISHED_DOC_ID="<ingested-doc-id>"

curl -s -X PUT http://localhost:8000/v1/documents/$UNPUBLISHED_DOC_ID/draft \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"content_markdown": "draft content"}' > /dev/null

curl -s -X POST http://localhost:8000/v1/documents/$UNPUBLISHED_DOC_ID/draft/finish \
  -H "Authorization: Bearer $TOKEN" | jq '.version.id'
# Expected: a new version id IS returned (version creation is unaffected)
# but no "tessera.index_document_version" task appears in worker logs
```

## Running Unit Tests

```bash
cd apps/api
.venv/bin/python -m pytest tests/unit/test_documents_draft_router.py -v --no-cov
```

All tests must pass, including the new cases under `TestFinishDraft` for:
dispatch on a published doc with real changes, no dispatch on a no-op
finish, and no dispatch on an unpublished doc.
