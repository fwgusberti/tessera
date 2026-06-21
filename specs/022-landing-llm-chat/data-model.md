# Data Model: Landing Page LLM Chat Interface

No new database entities are introduced. All conversation state is ephemeral, living only in browser memory for the duration of the session.

---

## Frontend-only types (`apps/web/lib/types.ts` additions)

### `ChatTurn`

Represents a single round-trip in the conversation.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` (UUID) | Stable React key; generated client-side with `crypto.randomUUID()` |
| `question` | `string` | The user's raw input text |
| `answer` | `AnswerResponse \| null` | Null while `status === "pending"` |
| `status` | `"pending" \| "complete" \| "error"` | Lifecycle state of this turn |
| `errorMessage` | `string?` | Populated only when `status === "error"` |

### `AnswerResponse` (already partially typed on the Search page)

Promote to a shared export in `lib/types.ts`:

| Field | Type | Description |
|-------|------|-------------|
| `answer` | `string \| null` | The LLM's response text; null when `dont_know` is true |
| `citations` | `Citation[]?` | Source chunks used to ground the answer |
| `confidence` | `number` | Float 0–1; confidence score from the retrieval pipeline |
| `dont_know` | `boolean?` | True when the retrieval confidence is below the space threshold |
| `suggested_owner` | `{ space_name: string }?` | Hint when `dont_know` is true |

### `Citation`

| Field | Type | Description |
|-------|------|-------------|
| `chunk_id` | `string` | Identifier of the source document chunk |
| `document_version_id` | `string` | Version the chunk came from |
| `quote` | `string` | Excerpt used as evidence |
| `score` | `number` | Relevance score for this citation |

### `HistoryMessage` (request shape)

Shape of each item in the `history` array sent to the backend.

| Field | Type | Description |
|-------|------|-------------|
| `role` | `"user" \| "assistant"` | Speaker for this message |
| `content` | `string` | Full message text |

---

## Backend DTO changes (`apps/api/tessera_api/routers/assistant.py`)

### `AnswerRequest` (extended)

```python
class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class AnswerRequest(BaseModel):
    query: str
    space_ids: list[UUID] | None = None
    language: str | None = None
    history: list[ChatHistoryMessage] | None = None  # NEW
```

No changes to `AssistantResponse` or `DontKnowResponse`.

---

## State transitions

```
ChatTurn lifecycle:
  [created]
    │  status = "pending", answer = null
    ▼
  API call in flight
    │
    ├── success → status = "complete", answer = AnswerResponse
    └── error   → status = "error",    errorMessage = <message>
```

---

## Conversation history derivation

History sent to the API is derived lazily from the in-memory `turns` array:

```
turns (ChatTurn[])
  → filter: status === "complete" AND answer.answer !== null
  → flatMap: [{role:"user", content: question}, {role:"assistant", content: answer}]
  → pass as `history` in next AnswerRequest
```

The *current* question is not included in `history`; it is sent as `query` (unchanged semantics for the existing endpoint).
