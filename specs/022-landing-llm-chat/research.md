# Research: Landing Page LLM Chat Interface

**Phase 0 findings — resolved unknowns and technology choices**

---

## 1. Multi-turn conversation: where to hold state?

**Decision**: Browser `useState` (in-memory, session-scoped).

**Rationale**: The spec explicitly says conversation history is not persisted between sessions. Adding a database table or server-side session store would require schema changes, auth session binding, and cleanup logic — all out of scope. React state is the simplest path: zero infra changes, no privacy surface, automatically cleared on navigation away.

**Alternatives considered**:
- `localStorage` — rejected; Data Locality principle (III) forbids local persistence without explicit consent capture, and there is no mechanism for that in this feature.
- Server-side session (Redis) — rejected; ephemeral state, adds infra dependency, not required for single-user chat UX.

---

## 2. How to forward history to the LLM?

**Decision**: Extend `AnswerRequest` with optional `history: list[dict[str, str]] | None` and prepend prior turns into the LLM message list inside `generate_answer`.

**Rationale**: The RAG retrieval step (embedding + vector search) is intentionally keyed on the *current* question only — including history in the embedding query would degrade retrieval precision. History only matters at the LLM completion step, where it gives the model conversational context.

**Alternatives considered**:
- Send full history as a single concatenated string appended to `query` — rejected; mixes retrieval input with context, hurts embedding quality.
- Create a separate `/v1/assistant/chat` endpoint — rejected; the existing endpoint is already doing the same RAG pipeline; duplication adds maintenance cost without benefit.

---

## 3. What becomes of the existing landing page content?

**Decision**: Stats and nav cards are preserved but moved to a secondary collapsed section below the chat. The page title "Tessera" and subtitle remain.

**Rationale**: The dashboard metrics (space count, total queries, documents with drift) and quick-nav cards have real value for power users. Discarding them entirely would be a regression. Placing them below the fold (or behind a "Show dashboard" toggle) keeps the chat as the unmistakable primary interface while retaining discoverability.

**Alternatives considered**:
- Remove dashboard entirely — rejected; too destructive, existing home.test.tsx tests cover the stat cards and quick-nav links.
- Keep dashboard above chat — rejected; contradicts the feature goal of making the landing page "the interface to ask questions".

---

## 4. Input UX: text input vs. textarea?

**Decision**: `<textarea>` with auto-resize (single line by default, expands on content).

**Rationale**: Questions to a RAG assistant can be multi-sentence. A single-line `<input type="text">` truncates long prompts visually. Textarea with `rows={1}` and `resize-none overflow-hidden` + JS height adjustment gives a familiar chat-box UX.

**Alternatives considered**:
- `<input type="text">` — rejected; poor UX for multi-line questions.
- Fixed-height large textarea — rejected; wastes space on short one-liners.

---

## 5. Empty submission prevention

**Decision**: Disable the submit button and block `Enter` key when the trimmed input is empty; show no error message until the user has typed and cleared the field.

**Rationale**: Preventing submission on empty input is simpler than showing an inline error for an action the user hasn't taken yet. The submit button being visually disabled (`disabled:opacity-50`) is self-explanatory.

---

## 6. Error state retention

**Decision**: On LLM error, mark the turn `status: "error"`, display the error message inline in the conversation, and re-populate the textarea with the failed question.

**Rationale**: Users shouldn't have to retype a failed question. Keeping the conversation history visible (with an error marker) and pre-filling the input for retry is the standard chat error pattern.

---

## 7. Streaming vs. complete-response

**Decision**: Complete-response (no streaming in this iteration).

**Rationale**: The existing `AnthropicLLMProvider.complete()` is not a streaming method. Adding SSE or WebSocket streaming would require backend route changes, a new frontend EventSource integration, and additional tests — significantly more scope than warranted for v1. The loading indicator (`status: "pending"`) bridges the wait time adequately.
