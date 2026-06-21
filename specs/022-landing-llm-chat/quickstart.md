# Quickstart: Validate the Landing Page LLM Chat

## Prerequisites

- Local dev stack running (`make dev` or equivalent — API on port 8000, web on port 3000)
- At least one space with indexed documents exists
- A valid user account (email + password)

---

## 1. API layer validation (backend)

Run the backend unit tests for the history-augmented prompt:

```bash
cd apps/api
pytest tests/test_assistant_history.py -v
```

Expected: all tests pass covering:
- `history=None` produces the same prompt as before
- `history=[...]` prepends prior turns before the context block
- Empty-string `content` in history items is rejected (422)
- Invalid `role` in history items is rejected (422)

Manually confirm the endpoint still works (requires a running backend and valid JWT):

```bash
curl -s -X POST http://localhost:8000/v1/assistant/answer \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the main topics covered in this space?"}' | jq .
```

Expected: `{ "answer": "...", "confidence": ..., "dont_know": false, "citations": [...] }`

---

## 2. Frontend unit tests

```bash
cd apps/web
npm test
```

Expected: all existing tests pass; new `tests/chat.test.tsx` passes covering:
- Chat input renders on the landing page
- Empty input blocks submission
- Submitting a question shows loading indicator, then renders answer
- Error state shows error message and retains the question in the input
- "New conversation" button clears all turns
- Conversation history items are displayed in order

---

## 3. End-to-end flow in the browser

1. Navigate to `http://localhost:3000` — should see the chat interface as the primary content.
2. Type a question (e.g., "What documents are in this space?") and press Enter or click **Ask**.
3. Verify:
   - A loading indicator appears immediately.
   - The answer renders in the conversation area with citations (or a "don't know" message).
   - The question input is cleared; the answered turn remains in the history.
4. Type a follow-up referencing the first answer (e.g., "Can you give more detail about the first point?").
5. Verify: the second answer is contextually aware of the first exchange.
6. Click **New conversation** — verify the history clears and the input is empty.
7. Submit without typing anything — verify the submit button is disabled and nothing happens.
8. Scroll below the chat — verify the stats dashboard and navigation cards are still accessible.

---

## 4. Responsive check

Resize the browser to 320 px wide. Verify:
- The chat input and submit button are fully visible and usable.
- Conversation turns do not overflow horizontally.
- The stats section below remains readable.

---

## 5. Error state check

With the API server stopped, submit a question and verify:
- An inline error message appears in the conversation.
- The question text is re-populated in the input so the user can retry.
