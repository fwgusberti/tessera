# Quickstart Validation Guide: Fix Search Indexing

**Date**: 2026-06-20

## Prerequisites

- Local stack running: `make dev` (API, workers, PostgreSQL+pgvector, Ollama, Redis)
- Valid JWT for an authenticated user (`$JWT`)
- At least one Space exists (`$SPACE_ID`)
- Admin JWT for bulk reindex tests (`$ADMIN_JWT`)

## Scenario 1: New Document Is Searchable After Publish

### Step 1: Verify worker starts with correct Ollama URL

```bash
make workers 2>&1 | grep OLLAMA_BASE_URL
# Expected: OLLAMA_BASE_URL=http://localhost:11434 present in the startup line
```

### Step 2: Create and publish a document

```bash
DOC=$(curl -s -X POST http://localhost:8000/v1/documents \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "space_id": "'$SPACE_ID'",
    "title": "Quarterly Budget Review",
    "content_markdown": "This document covers the budget allocation for Q3.",
    "language": "en"
  }')
DOC_ID=$(echo $DOC | jq -r '.document.id')

curl -s -X POST http://localhost:8000/v1/documents/$DOC_ID/publish \
  -H "Authorization: Bearer $JWT"
```

### Step 3: Wait for indexing, then search

```bash
sleep 5

curl -s -X POST http://localhost:8000/v1/search \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"query": "quarterly"}' | jq '.results | length'
```

**Expected**: `1` or more.

---

## Scenario 2: Worker Logs Embedding Failures

### Step 1: Stop Ollama, then publish a document

```bash
cd deploy && docker compose stop ollama
# Publish a document (as in Scenario 1 Step 2)
```

### Step 2: Check worker log

```bash
# In the worker terminal or log output, look for:
# indexing_embedding_failed document_id=<uuid> error=<connection refused message>
```

**Expected**: Structured error log appears; worker does not crash silently.

### Step 3: Restart Ollama

```bash
cd deploy && docker compose start ollama
```

---

## Scenario 3: Per-Document Reindex Endpoint

```bash
# Trigger reindex for an existing published document
curl -s -X POST http://localhost:8000/v1/documents/$DOC_ID/reindex \
  -H "Authorization: Bearer $JWT" | jq .
# Expected: {"queued": true, "document_id": "<uuid>"}

sleep 5

# Verify document is searchable
curl -s -X POST http://localhost:8000/v1/search \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"query": "quarterly"}' | jq '.results | length'
# Expected: 1 or more

# Verify 403 for a non-owner
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/v1/documents/$DOC_ID/reindex \
  -H "Authorization: Bearer $OTHER_JWT"
# Expected: 403

# Verify 404 for missing document
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/v1/documents/00000000-0000-0000-0000-000000000000/reindex \
  -H "Authorization: Bearer $JWT"
# Expected: 404
```

---

## Scenario 4: Bulk Admin Reindex

```bash
# Trigger bulk reindex (recovers all published docs with no chunks)
curl -s -X POST http://localhost:8000/v1/admin/reindex \
  -H "Authorization: Bearer $ADMIN_JWT" | jq .
# Expected: {"dispatched": N}  where N >= 0

sleep 10

# All previously un-indexed documents should now be searchable
curl -s -X POST http://localhost:8000/v1/search \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"query": "quarterly"}' | jq '.results | length'
# Expected: 1 or more

# Verify non-admin cannot call bulk reindex
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/v1/admin/reindex \
  -H "Authorization: Bearer $JWT"
# Expected: 403
```

---

## Automated Test Validation

```bash
# API unit tests
cd apps/api && uv run pytest tests/unit/test_reindex_router.py -v

# Worker error-handling tests
cd apps/workers && uv run pytest tests/unit/test_indexing_error_handling.py -v

# Full coverage gates
cd apps/api && uv run pytest --cov=tessera_api --cov-fail-under=85
cd apps/workers && uv run pytest --cov=tessera_workers --cov-fail-under=85
```

All tests must pass at ≥85% statement coverage.
