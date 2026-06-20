# Quickstart: Validate Fix for Search Endpoint 500 Error

**Feature**: 014-fix-search-500  
**Date**: 2026-06-20

## Prerequisites

- Docker stack running: `docker compose up -d` (PostgreSQL + Ollama + API)
- Ollama has the `nomic-embed-text` model: `ollama pull nomic-embed-text`
- At least one published document exists (or test with empty results)
- A valid JWT token (obtain via `POST /v1/auth/token`)

## Validation Scenarios

### Scenario 1: Basic search returns 200 (not 500)

```bash
curl -s -X POST http://localhost:8000/v1/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "mamadeira"}' | jq .
```

**Expected**: HTTP 200 with `{"results": [...]}` (empty array is acceptable if no indexed documents).  
**Before fix**: HTTP 500.

---

### Scenario 2: Embedding service down → 503 (not 500)

Stop Ollama (or point to wrong URL via env override), then:

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/v1/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

**Expected**: `503`  
**Before fix**: `500`

---

### Scenario 3: Unauthenticated request → 401

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "mamadeira"}'
```

**Expected**: `401`

---

### Scenario 4: Unit tests pass

```bash
cd apps/api
uv run pytest tests/unit/test_search_router.py -v
```

**Expected**: All tests GREEN.

---

### Scenario 5: Full test suite passes (85% coverage gate)

```bash
cd apps/api
uv run pytest
```

**Expected**: All tests GREEN, coverage ≥ 85%.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Still getting 500 | Old code running | Restart API container |
| 503 when Ollama IS running | Wrong `OLLAMA_BASE_URL` env var | Check `.env` |
| 0 results but expecting matches | No published docs / no embeddings ingested | Ingest documents first via worker |
| Coverage below 85% | New test file not covering all branches | Add missing test cases |
