# Quickstart: Validate AI-First Interface with Doc Access

## Prerequisites

- Local dev stack running: `docker compose up` (PostgreSQL, Ollama, API, workers, web)
- At least one published document in at least one space
- An authenticated user account with access to that space

---

## US1: AI chat is the default home

```bash
# Navigate to root while authenticated
open http://localhost:3000/
```

**Expected**: The chat input textarea and "Ask" button render immediately as the primary content. No document list, no stat cards, no dashboard widgets in the main area.

**Test coverage**: `apps/web/tests/home.test.tsx` — "renders the chat interface as the primary content element"

---

## US2: Persistent navigation between Chat and Documents

```bash
# From chat home, click the "Chat" nav link — should be active/highlighted
# Then click the "Documents" nav link
open http://localhost:3000/
# → click "Documents" in the nav bar
# → verify document browser renders at /documents
# → click "Chat" in the nav bar
# → verify you are back at / with the chat input
```

**Expected**:
- Both "Chat" and "Documents" labels are visible in the nav bar without scrolling (desktop)
- The active view's nav link has an `indigo-600` style (or similar accent)
- On mobile (≤ 768 px viewport): hamburger reveals both "Chat" and "Documents" entries
- The chat conversation is reset when leaving and returning (per spec: state preserved in component, navigation resets it)

**Test coverage**: `apps/web/tests/navbar.test.tsx` — new tests for Chat/Documents nav links and active state

---

## US3: In-chat document discovery via citations

```bash
# 1. Log in, navigate to /
# 2. Type a question whose answer exists in a published document
#    e.g. "What is our onboarding process?"
# 3. Submit and wait for the response
```

**Expected**:
- The AI response text appears in the conversation
- Below the answer text a "Sources" section lists links to the matched documents
- Each link label is the citation quote (truncated)
- Clicking a source link opens `/documents/{document_id}` in a new browser tab
- The chat conversation is still intact in the original tab

**Test coverage**: `apps/web/tests/chat.test.tsx` — "renders citation document links when answer has citations"

---

## Edge cases

| Scenario | Expected outcome |
|----------|-----------------|
| No documents in accessible space | Chat loads; document browser shows empty-state message |
| User navigates directly to `/documents` | Document browser loads normally (deep link valid) |
| AI returns `dont_know: true` | "I don't have enough information…" message shown; no Sources section |
| AI returns citations with 0 documents after ACL filter | Sources section is omitted (empty array guard) |
| Mobile viewport (< 768 px) | Hamburger shows "Chat" and "Documents"; no visible overflow |

---

## Running the unit test suite

```bash
# Frontend
cd apps/web && npm test -- --run

# Backend citation tests
cd apps/api && uv run pytest tests/ -k "citation" -v
```

All tests must pass before marking the feature complete.
