# Contract: POST /v1/assistant/answer

## Change for feature 027

The only change to this contract is the addition of `document_id` to each element of the `citations` array.

---

## Request (unchanged)

```http
POST /v1/assistant/answer
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "query": "string (required, non-empty)",
  "history": [
    { "role": "user" | "assistant", "content": "string (non-empty)" }
  ],
  "space_ids": ["uuid", ...] | null,
  "language": "string" | null
}
```

## Response — answer branch

```json
{
  "answer": "string",
  "confidence": 0.0–1.0,
  "dont_know": false,
  "citations": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "document_version_id": "uuid",
      "quote": "string (≤ 200 chars)",
      "score": 0.0–1.0
    }
  ]
}
```

`document_id` is new in feature 027. It uniquely identifies the document that the chunk belongs to and can be used to construct a frontend link: `/documents/{document_id}`.

## Response — dont_know branch (unchanged)

```json
{
  "answer": null,
  "confidence": 0.0–1.0,
  "dont_know": true,
  "suggested_owner": { "space_id": "uuid", "space_name": "string" } | null
}
```

## Error responses (unchanged)

| Status | Condition |
|--------|-----------|
| 401 | Missing or invalid JWT |
| 422 | Malformed request body (empty query, empty history message content) |
| 503 | Embedding service unavailable |
