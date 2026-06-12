# Data Model: Local Ollama Embedding Provider

**Feature**: 002-ollama-embeddings
**Date**: 2026-06-12

---

## Changed: `chunks.embedding` Column

| Attribute   | Before (Voyage)      | After (Ollama)        |
|-------------|---------------------|-----------------------|
| Column type | `vector(1024)`      | `vector(768)`         |
| HNSW index  | `vector_cosine_ops` | `vector_cosine_ops`   |
| HNSW m      | 16                  | 16                    |
| HNSW ef     | 64                  | 64                    |

**Migration**: Alembic revision `0002_ollama_embeddings`. Steps:
1. Drop `ix_chunks_embedding_hnsw` index.
2. `DELETE FROM chunks` — all existing vectors are incompatible with the new dimension and must be re-generated.
3. `ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(768)`.
4. Recreate `ix_chunks_embedding_hnsw` with the same HNSW parameters.

After migration, documents must be re-indexed by the worker to repopulate chunks with 768-dim vectors.

---

## Changed: Application Configuration

| Setting              | Before                           | After                            |
|----------------------|----------------------------------|----------------------------------|
| `voyage_api_key`     | `str = ""`                       | *(removed)*                      |
| `ollama_base_url`    | *(absent)*                       | `str = "http://ollama:11434"`    |
| `embedding_model`    | `"voyage-3"`                     | `"nomic-embed-text"`             |
| `embedding_dimensions` | `1024`                         | `768`                            |
| Env var (compose)    | `VOYAGE_API_KEY`                 | *(removed)*                      |
| Env var (compose)    | *(absent)*                       | `OLLAMA_BASE_URL` (optional)     |

The `ollama_base_url` field reads from `OLLAMA_BASE_URL` env var (pydantic-settings convention). In compose, the default `http://ollama:11434` resolves to the `ollama` service on the internal Docker network.

---

## New Compose Service: `ollama`

| Attribute   | Value                                      |
|-------------|-------------------------------------------|
| Image       | `ollama/ollama:latest`                    |
| Port        | `11434` (host-exposed for debugging)      |
| Volume      | `ollama_data:/root/.ollama`               |
| Healthcheck | `ollama list` after `nomic-embed-text` pull|

`api` and `worker` services gain a `depends_on: ollama: condition: service_healthy` entry to guarantee the model is loaded before ingestion or search begins.

---

## No Domain Model Changes

The `Chunk` domain entity (`packages/core/tessera_core/domain/entities.py`) stores `embedding: list[float] | None`. This is dimension-agnostic; no change is needed.

The `EmbeddingProvider` ABC (`packages/core/tessera_core/ports/providers.py`) is unchanged.

---

## Entities Affected (Summary)

| Entity / Artifact                        | Change                                       |
|------------------------------------------|----------------------------------------------|
| `chunks` table (PostgreSQL)              | `embedding` column dimension 1024 → 768      |
| `Settings` (pydantic model in config.py) | Remove `voyage_api_key`, add `ollama_base_url`, update defaults |
| `VoyageEmbeddingProvider` (adapter)      | Deleted                                       |
| `OllamaEmbeddingProvider` (adapter)      | Created                                       |
| `docker-compose.yml`                     | Add `ollama` service; remove `VOYAGE_API_KEY`|
| `routers/search.py`                      | Import updated                                |
| `routers/assistant.py`                   | Import updated                                |
| `indexing/_index.py`                     | Import updated                                |
