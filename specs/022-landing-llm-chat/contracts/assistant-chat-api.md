# Contract: Assistant Chat API

**Endpoint**: `POST /v1/assistant/answer`
**Auth**: Bearer JWT (required — 401 if missing or expired)
**Changed by this feature**: `history` field added to request body (optional, backward-compatible)

---

## Request

```json
{
  "query": "What is the onboarding process for new engineers?",
  "space_ids": ["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
  "language": "en",
  "history": [
    { "role": "user",      "content": "Tell me about the engineering team." },
    { "role": "assistant", "content": "The engineering team is divided into..." }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | **yes** | The current user question |
| `space_ids` | string[] (UUID) | no | Restrict retrieval to these spaces; defaults to all accessible spaces |
| `language` | string | no | Hint for language-aware processing |
| `history` | array | no | Prior conversation turns, in chronological order (oldest first). Each item has `role` ("user" or "assistant") and `content` (string). Maximum recommended depth: 10 turns (20 messages) to stay within LLM context limits. |

---

## Response — Success (200 OK)

### Case A: Answer found

```json
{
  "answer": "The onboarding process begins with...",
  "citations": [
    {
      "chunk_id": "c1d2e3f4-...",
      "document_version_id": "a1b2c3d4-...",
      "quote": "New engineers start with a two-week orientation...",
      "score": 0.87
    }
  ],
  "confidence": 0.87,
  "dont_know": false
}
```

### Case B: Insufficient confidence

```json
{
  "answer": null,
  "dont_know": true,
  "confidence": 0.42,
  "suggested_owner": { "space_name": "Engineering Handbook" }
}
```

---

## Response — Error cases

| HTTP Status | Condition | Body |
|-------------|-----------|------|
| 400 | `query` is empty or missing | `{ "detail": "..." }` |
| 401 | Missing or expired JWT | `{ "detail": "Not authenticated" }` |
| 422 | Malformed request body | FastAPI validation error |
| 500 | LLM provider or retrieval failure | `{ "detail": "Internal server error" }` |

---

## Behavior with `history`

When `history` is provided and non-empty:
- The retrieval pipeline (embedding + vector search) uses only `query` — history is **not** embedded.
- The LLM completion step prepends history turns before the context + question block, so the model can resolve references like "What about the second point you mentioned?".
- History items are validated: `role` must be `"user"` or `"assistant"`; `content` must be a non-empty string.
- If `history` is `null` or omitted, the endpoint behaves exactly as before this feature (fully backward-compatible).

---

## Frontend call signature (`apps/web/lib/chat.ts`)

```typescript
export async function askAssistant(
  query: string,
  history: HistoryMessage[],
): Promise<AnswerResponse> {
  return api.post<AnswerResponse>("/v1/assistant/answer", { query, history });
}
```
