# Research: Local Ollama Embedding Provider

**Feature**: 002-ollama-embeddings
**Date**: 2026-06-12

---

## Decision: Ollama HTTP API Endpoint

**Decision**: Use the `/api/embed` endpoint (batch-capable, plural noun).

**Rationale**: Ollama exposes two embedding endpoints:
- `/api/embeddings` (older, singular) — accepts `{"model": "...", "prompt": "..."}`, one text at a time.
- `/api/embed` (newer, available since Ollama 0.1.34) — accepts `{"model": "...", "input": ["text1", "text2"]}`, returns `{"embeddings": [[...], [...]]}`.

The existing `EmbeddingProvider.embed(texts: list[str]) -> list[list[float]]` interface maps directly and without N-round-trips to `/api/embed`. The older endpoint would require a loop, degrading indexing performance.

**Alternatives considered**: Loop over `/api/embeddings` — rejected because it multiplies latency linearly with batch size.

---

## Decision: Embedding Model — nomic-embed-text, 768 dimensions

**Decision**: Use `nomic-embed-text` (768-dimensional vectors).

**Rationale**: `nomic-embed-text` is the de-facto standard offline embedding model for Ollama. It is available from the Ollama model registry, produces 768-dimensional vectors, and has strong multilingual performance on retrieval benchmarks — acceptable for Tessera's document retrieval use case. It is also the smallest model with consistently good quality, keeping memory footprint manageable in a local compose stack.

**Alternatives considered**:
- `mxbai-embed-large` (1024 dims) — would avoid the migration (same dimension as voyage-3), but is substantially larger (~670 MB vs ~274 MB) and offers no meaningful quality advantage for the retrieval use case. Rejected on resource grounds.
- `all-minilm` (384 dims) — much smaller, but retrieval quality noticeably lower on longer documents. Rejected.

---

## Decision: Docker Model Loading Strategy — Entrypoint Script with Named Volume

**Decision**: The `ollama` compose service overrides its entrypoint with a shell script that starts the Ollama server in the background, pulls `nomic-embed-text` if not already present in the volume, then foregrounds the server process.

**Rationale**: The `ollama/ollama` Docker image does not bundle model weights. The volume (`ollama_data`) persists weights across container restarts, so the pull only happens once (requires internet). On subsequent starts the pull is a no-op (model already cached). This satisfies the "fully offline at runtime" constraint after the first pull. The healthcheck waits for the model to be listed before `api` and `worker` services are declared healthy-dependent.

**Tradeoff — `docker compose pull` vs first-run pull**: `docker compose pull` fetches only the Docker image (~2 GB), not the model weights (~274 MB). The model weights are downloaded by the `ollama` container on first startup. This is a documented limitation: full offline operation requires one internet-connected first run. After the first run, the named volume holds the weights and the stack operates offline indefinitely.

**Alternatives considered**:
- Custom Dockerfile baking model into image — rejected; creates a ~2.3 GB image that must be re-built and re-pushed on model upgrades.
- Separate `ollama-init` sidecar service — rejected; adds a service that only runs once and makes the compose file more complex without benefit over the entrypoint approach.
- Manual `docker compose exec ollama ollama pull nomic-embed-text` step in docs — rejected; requires human intervention and breaks the "zero steps beyond `docker compose up`" goal.

---

## Decision: pgvector Migration Strategy — Delete Rows, ALTER TYPE, Recreate Index

**Decision**: Migration `0002` (a) drops the HNSW index on `chunks.embedding`, (b) deletes all rows in `chunks`, (c) alters the column type to `vector(768)`, (d) recreates the HNSW index.

**Rationale**: pgvector does not support in-place dimension conversion — vectors are fixed-length binary blobs and a 1024-dim vector cannot be coerced to 768-dim. Deleting all chunk rows is the only safe migration path. The documents and document_versions records remain intact; re-indexing (re-embedding + re-chunking) is triggered by the existing indexing worker for each document after the migration.

**Alternatives considered**:
- Keep both columns (`embedding_768` alongside `embedding`) during a migration window — rejected; requires dual-write and code complexity that is unwarranted for a dev-only migration.
- Rename table and recreate — rejected; more disruptive and offers no advantage over ALTER COLUMN after row deletion.

---

## Decision: No New Python Dependencies

**Decision**: The `OllamaEmbeddingProvider` uses `httpx`, which is already declared in both `apps/api/pyproject.toml` and `apps/workers/pyproject.toml`. No new packages are needed.

**Rationale**: The Voyage adapter already uses `httpx` for its HTTP call. The Ollama adapter follows the same pattern. There is no official Ollama Python SDK dependency required.

---

## Decision: Timeout — 60 seconds

**Decision**: Set `httpx` timeout to 60 seconds for the Ollama adapter (up from Voyage's 30 seconds).

**Rationale**: On first invocation after a container restart, Ollama may need to load the model into memory (warm-up). This can take 10–30 seconds on typical development hardware. A 60-second timeout accommodates warm-up without being excessively permissive. Subsequent calls complete in < 1 second for typical batch sizes.
