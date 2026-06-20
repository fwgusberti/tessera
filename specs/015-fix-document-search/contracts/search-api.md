# Contract: Search API

**Endpoint**: `POST /v1/search`
**Auth**: Bearer JWT required

## Request

```json
{
  "query": "string (non-empty, trimmed)",
  "space_ids": ["uuid", ...],  // optional; defaults to all spaces
  "language": "string",         // optional
  "top_k": 10                   // optional; default 10
}
```

## Response (200 OK)

```json
{
  "results": [
    {
      "document_id": "uuid",
      "version_id": "uuid",
      "chunk_id": "uuid",
      "score": 0.92,
      "snippet": "...up to 300 chars of matching chunk text...",
      "citation": {
        "document_title": "Quarterly Report",
        "source": "..."
      }
    }
  ]
}
```

**Behavior guarantees** (after fix):
- When a published document's title contains the query term, that document MUST appear in results (SC-001)
- Draft documents MUST NOT appear in results (FR-001)
- Empty results list `[]` when no chunks match — not an error (FR-003)

## Error Responses

| Status | Condition |
|--------|-----------|
| 400 | Invalid request body |
| 401 | Missing or invalid JWT |
| 503 | Ollama embedding service unavailable |

**Note**: This contract is unchanged by the fix. The fix corrects the data pipeline so that results are actually returned, not the API contract itself.
