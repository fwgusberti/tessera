# Contract: Ollama Embed API

**Consumer**: `OllamaEmbeddingProvider` (adapter in `apps/api/tessera_api/adapters/embeddings.py`)
**Provider**: Ollama local service (`ollama/ollama` Docker image, >= 0.1.34)
**Endpoint**: `POST /api/embed`

---

## Request

```
POST http://ollama:11434/api/embed
Content-Type: application/json

{
  "model": "nomic-embed-text",
  "input": ["text chunk one", "text chunk two", "..."]
}
```

| Field   | Type            | Required | Description                                |
|---------|-----------------|----------|--------------------------------------------|
| `model` | `string`        | Yes      | Model name as registered in the Ollama registry |
| `input` | `list[string]`  | Yes      | Batch of texts to embed; minimum 1 item    |

---

## Response (200 OK)

```json
{
  "model": "nomic-embed-text",
  "embeddings": [
    [0.012, -0.045, ...],
    [0.089, 0.021, ...]
  ],
  "total_duration": 1234567890,
  "load_duration": 9876543,
  "prompt_eval_count": 42
}
```

| Field        | Type                    | Description                                      |
|--------------|-------------------------|--------------------------------------------------|
| `embeddings` | `list[list[float]]`     | One vector per input text, in the same order     |
| *(others)*   | —                       | Timing metadata; ignored by the adapter          |

The adapter extracts `response.json()["embeddings"]` and returns it directly.

---

## Error Handling

| HTTP Status | Condition                        | Adapter Behaviour                          |
|-------------|----------------------------------|--------------------------------------------|
| 200         | Success                          | Return embeddings list                     |
| 4xx / 5xx   | Model not loaded, bad request    | `raise_for_status()` propagates `httpx.HTTPStatusError` |
| Timeout     | Model warm-up or overload        | `httpx.TimeoutException` propagates; caller logs and returns 503 |

---

## Adapter Configuration

| Parameter        | Source                         | Default                    |
|------------------|--------------------------------|----------------------------|
| `base_url`       | `settings.ollama_base_url`     | `http://ollama:11434`      |
| `model`          | `settings.embedding_model`     | `nomic-embed-text`         |
| `dimensions`     | `settings.embedding_dimensions`| `768`                      |
| `timeout`        | Hardcoded in adapter           | `60.0` seconds             |
