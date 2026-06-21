# Implementation Plan: Landing Page as LLM Chat Interface

**Branch**: `022-landing-llm-chat` | **Date**: 2026-06-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/022-landing-llm-chat/spec.md`

## Summary

Replace the landing page dashboard with a multi-turn LLM chat interface that calls the existing `/v1/assistant/answer` backend. The backend router is extended to accept optional conversation history, which is forwarded into the RAG prompt so follow-up questions are contextually coherent. Conversation state is held entirely in browser memory (no database changes). The stats dashboard and navigation cards are condensed into a secondary section below the chat area.

## Technical Context

**Language/Version**: Python 3.11 (backend) · TypeScript / Next.js 14 (frontend)

**Primary Dependencies**:
- Backend: FastAPI, Pydantic v2, Anthropic SDK (already wired in `llm.py`)
- Frontend: Next.js App Router, React 18, Tailwind CSS, Vitest + Testing Library

**Storage**: No new storage. Conversation history lives in React state for the browser session; existing PostgreSQL + audit log remain unchanged.

**Testing**: Backend — pytest (existing suite under `apps/api/tests/`). Frontend — Vitest + @testing-library/react (existing suite under `apps/web/tests/`).

**Target Platform**: Linux server (backend) + browser (frontend, ≥ 320 px wide per responsive standard).

**Project Type**: Web application (Next.js SPA over a FastAPI REST backend).

**Performance Goals**: No new performance targets introduced. Existing assistant latency is dominated by the LLM call; users tolerate several seconds and see a loading indicator.

**Constraints**: Response must stream or complete within the same HTTP response (streaming not added in this iteration — complete-response model only). No database changes. Auth required (existing `require_user` guard stays in place).

**Scale/Scope**: Single-user landing page interaction. No concurrent chat session requirements beyond what the existing assistant endpoint already handles.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. DDD | ✅ Pass | `generate_answer` domain service unchanged. `ChatMessage` / `ConversationHistory` are transport DTOs, not domain models. |
| II. Separation of Concerns | ✅ Pass | History forwarding is added at the router (transport) layer; the core RAG service receives it as a plain list and builds prompt strings from it. |
| III. Data Locality & Consent | ✅ Pass | Conversation history stays in browser `useState` — no local persistence. No consent mechanism needed. |
| IV. TDD | ✅ Required | New backend logic for history-augmented prompt construction must have unit tests written before implementation. New frontend `ChatInterface` component must have Vitest tests before implementation. |
| V. Quality Gates | ✅ Required | All Python files pass Ruff + Black. All TypeScript passes tsc. |
| Security — JWT Auth | ✅ Pass | `require_user` remains on the `/v1/assistant/answer` route. |
| Security — Audit Logging | ✅ Pass | `write_audit` call in the router is unchanged — every query is logged. |
| UI Design System | ✅ Required | Chat bubbles use `slate-*` + `indigo-600` accent. No `gray-*` or `blue-*` introduced. |

*Post-design re-check*: No violations. No Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/022-landing-llm-chat/
├── plan.md              # This file
├── research.md          # Phase 0 findings
├── data-model.md        # Phase 1 data shapes
├── quickstart.md        # Phase 1 validation guide
├── contracts/
│   └── assistant-chat-api.md  # Extended endpoint contract
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code

```text
apps/api/
├── tessera_api/
│   ├── routers/
│   │   └── assistant.py        # Add optional `history` field to AnswerRequest
│   └── rag/
│       └── assistant.py        # Pass history turns into LLM message list
└── tests/
    └── test_assistant_history.py   # New: unit tests for history-augmented prompt

apps/web/
├── app/
│   └── page.tsx                # Replace dashboard with ChatInterface + collapsed stats
├── components/
│   └── chat/
│       ├── ChatInterface.tsx   # New: full conversation UI
│       └── MessageBubble.tsx   # New: single turn display (user / assistant)
├── lib/
│   ├── types.ts                # Add ChatMessage, ConversationTurn, AnswerResponse exports
│   └── chat.ts                 # New: typed wrapper for POST /v1/assistant/answer
└── tests/
    ├── chat.test.tsx           # New: ChatInterface unit tests
    └── home.test.tsx           # Updated: reflects new chat-primary layout
```

**Structure Decision**: Web application layout. Backend stays in `apps/api/tessera_api/`; frontend in `apps/web/`. No new top-level directories needed.

## Complexity Tracking

No constitution violations. Table omitted.

## Implementation Notes

### Backend: history-augmented prompt

`AnswerRequest` gains an optional field:

```python
history: list[dict[str, str]] | None = None
# each item: {"role": "user"|"assistant", "content": "..."}
```

`generate_answer` receives the history list and prepends prior turns before the current context+question block in the messages sent to the LLM. The embedding and retrieval pipeline is unchanged — only the current `query` is embedded.

### Frontend: conversation state shape

```typescript
interface ChatTurn {
  id: string;            // uuid for React key
  question: string;
  answer: AnswerResponse | null;
  status: "pending" | "complete" | "error";
  errorMessage?: string;
}
```

Conversation history sent to the API is derived from completed turns:

```typescript
history = turns
  .filter(t => t.status === "complete" && t.answer?.answer)
  .flatMap(t => [
    { role: "user",      content: t.question },
    { role: "assistant", content: t.answer!.answer! },
  ]);
```

### Landing page layout

The page retains `AuthGuard`. Layout order:
1. **Chat area** (primary, full-width, takes most vertical space)
   - Conversation history (scrollable, reversed-chronological display — newest at bottom)
   - Input row (textarea + submit button)
   - Empty-state prompt when no conversation yet
2. **Stats + nav** (secondary, collapsed below chat or behind a toggle)

The "New conversation" control appears in the chat header as a text button.
