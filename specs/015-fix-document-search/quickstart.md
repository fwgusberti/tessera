# Quickstart Validation Guide: Fix Document Search Returns No Results

**Date**: 2026-06-20

## Prerequisites

- Local stack running: `make dev` (API, workers, PostgreSQL+pgvector, Ollama, Redis)
- Valid JWT for an authenticated user
- At least one Space exists

## End-to-End Validation Scenario

### Step 1: Create and publish a document

```bash
# Create document
curl -s -X POST http://localhost:8000/v1/documents \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "space_id": "'$SPACE_ID'",
    "title": "Quarterly Budget Review",
    "content_markdown": "This document covers the budget allocation for Q3.",
    "language": "en"
  }' | tee /tmp/doc.json

DOC_ID=$(jq -r '.document.id' /tmp/doc.json)

# Publish
curl -s -X POST http://localhost:8000/v1/documents/$DOC_ID/publish \
  -H "Authorization: Bearer $JWT"
```

### Step 2: Wait for indexing

The publish endpoint dispatches the `index_document_version` Celery task. Allow ~5 seconds for the worker to embed and persist chunks.

```bash
sleep 5
```

### Step 3: Search for a title keyword

```bash
curl -s -X POST http://localhost:8000/v1/search \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"query": "quarterly"}' | jq .
```

**Expected**: `results` contains at least one entry where `citation.document_title` is "Quarterly Budget Review".

### Step 4: Verify "no results" message in the UI

1. Open the search page in the browser.
2. Search for a term that matches no document title.
3. **Expected**: A "No results found" message is displayed (not a blank page).

### Step 5: Verify drafts are excluded

```bash
# Create another document but do NOT publish it
curl -s -X POST http://localhost:8000/v1/documents \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "space_id": "'$SPACE_ID'",
    "title": "Secret Draft Document",
    "content_markdown": "confidential draft content",
    "language": "en"
  }'

# Search for the draft title keyword
curl -s -X POST http://localhost:8000/v1/search \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"query": "secret draft"}' | jq '.results | length'
```

**Expected**: `0` — draft documents must not appear in results.

## Automated Test Validation

```bash
# API unit tests (fast, no DB)
cd apps/api && uv run pytest tests/unit/test_search_router.py -v

# Chunk repository tests (fast, no DB)
cd apps/api && uv run pytest tests/unit/ -v -k "chunk"

# Workers unit tests
cd apps/workers && uv run pytest tests/ -v

# Full coverage gate
cd apps/api && uv run pytest --cov=tessera_api --cov-fail-under=85
cd apps/workers && uv run pytest --cov=tessera_workers --cov-fail-under=85
```

All tests must pass at ≥85% statement coverage.
