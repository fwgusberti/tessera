# Quickstart: Local Ollama Embedding Provider

**Feature**: 002-ollama-embeddings
**Date**: 2026-06-12

This guide describes how to validate that the feature works end-to-end in a local Docker Compose environment.

---

## Prerequisites

- Docker and Docker Compose installed and running
- Internet access for the first run (model weights download ~274 MB)
- The repository cloned and on the branch implementing this feature

---

## 1. First-Time Setup (requires internet)

```bash
# Pull all Docker images (does NOT pull model weights)
docker compose -f deploy/docker-compose.yml pull

# Start the stack — Ollama will download nomic-embed-text on first run
docker compose -f deploy/docker-compose.yml up -d

# Watch until ollama is healthy (model pull complete)
docker compose -f deploy/docker-compose.yml logs -f ollama
# Expected: "model 'nomic-embed-text' ready"
```

The `api` and `worker` services wait for the `ollama` healthcheck to pass before starting, so no manual sequencing is needed.

---

## 2. Validate: No API Key Required

```bash
# Confirm VOYAGE_API_KEY is absent from all running containers
docker compose -f deploy/docker-compose.yml exec api env | grep -i voyage
# Expected: (no output)

docker compose -f deploy/docker-compose.yml exec worker env | grep -i voyage
# Expected: (no output)
```

---

## 3. Validate: Embeddings Generated Locally

```bash
# Call the Ollama embed endpoint directly
curl -s http://localhost:11434/api/embed \
  -H "Content-Type: application/json" \
  -d '{"model": "nomic-embed-text", "input": ["hello world"]}' \
  | python3 -c "import sys, json; d=json.load(sys.stdin); print('dimensions:', len(d['embeddings'][0]))"
# Expected: dimensions: 768
```

---

## 4. Run Database Migration

```bash
# Apply the new migration (0002_ollama_embeddings)
docker compose -f deploy/docker-compose.yml exec api \
  alembic -c /app/db/migrations/alembic.ini upgrade head

# Confirm the chunks column is now vector(768)
docker compose -f deploy/docker-compose.yml exec postgres \
  psql -U tessera tessera -c "\d chunks" | grep embedding
# Expected: embedding | vector(768) | ...
```

---

## 5. Validate: Document Ingestion Produces 768-dim Vectors

Use the API to ingest a document. See `contracts/ollama-embed-api.md` for the embedding endpoint shape.

```bash
# After ingestion, check a chunk's embedding dimension
docker compose -f deploy/docker-compose.yml exec postgres \
  psql -U tessera tessera -c \
  "SELECT array_length(embedding::real[], 1) AS dims FROM chunks LIMIT 1;"
# Expected: dims = 768
```

---

## 6. Validate: Semantic Search Works

```bash
# Submit a search query (requires a JWT; adjust as needed for your auth setup)
curl -s -X POST http://localhost:8000/search \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "top_k": 3}' \
  | python3 -m json.tool
# Expected: {"results": [...]} with score > 0 for at least one result
```

---

## 7. Validate: Offline Operation (After First Run)

```bash
# Stop the stack
docker compose -f deploy/docker-compose.yml down

# Block outbound internet (or disconnect network adapter)
# Then restart — the stack must come up and serve embeddings without internet

docker compose -f deploy/docker-compose.yml up -d

# Re-run the embed validation from step 3
# Expected: same result (768 dimensions) with no network calls to external services
```

---

## Cleanup

```bash
docker compose -f deploy/docker-compose.yml down -v
# WARNING: -v removes the ollama_data volume; next start will re-download model weights
```

---

## References

- [Ollama Embed API contract](contracts/ollama-embed-api.md)
- [Data model changes](data-model.md)
- [Research decisions](research.md)
