---
description: "Task list for Landing Page as LLM Chat Interface"
---

# Tasks: Landing Page as LLM Chat Interface

**Input**: Design documents from `specs/022-landing-llm-chat/`

**Prerequisites**: plan.md ✅ · spec.md ✅ · research.md ✅ · data-model.md ✅ · contracts/assistant-chat-api.md ✅ · quickstart.md ✅

**TDD**: Constitution Principle IV is NON-NEGOTIABLE — all test tasks MUST be written and confirmed FAILING before the implementation tasks they cover.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in every task description

---

## Phase 1: Setup (Shared Type Definitions)

**Purpose**: Establish the shared TypeScript types and API wrapper that all frontend stories depend on.

- [X] T001 [P] Add `ChatTurn`, `AnswerResponse`, `Citation`, and `HistoryMessage` type exports to `apps/web/lib/types.ts` per data-model.md
- [X] T002 [P] Create `apps/web/lib/chat.ts` with the `askAssistant(query: string, history: HistoryMessage[]): Promise<AnswerResponse>` typed wrapper for `POST /v1/assistant/answer`

**Checkpoint**: Types compile with `tsc --noEmit`; `chat.ts` module exports `askAssistant` with correct signature.

---

## Phase 2: Foundational — Backend History Support (TDD)

**Purpose**: Extend the existing `POST /v1/assistant/answer` endpoint to accept optional conversation history and forward it into the LLM completion step. This unblocks US2.

**⚠️ CRITICAL**: Complete Phase 1 before starting. Write T003 tests, **confirm they FAIL**, then implement T004–T005.

- [X] T003 Write failing unit tests for history-augmented prompt construction in `apps/api/tests/test_assistant_history.py` — must cover: `history=None` produces identical prompt to current behavior; non-empty history is prepended to LLM message list before context+question block; item with empty `content` is rejected (422); item with invalid `role` is rejected (422)
- [X] T004 [P] Add `ChatHistoryMessage(BaseModel)` with `role: Literal["user","assistant"]` and `content: str` to `apps/api/tessera_api/routers/assistant.py`, and extend `AnswerRequest` with `history: list[ChatHistoryMessage] | None = None`
- [X] T005 Update `generate_answer` in `apps/api/tessera_api/rag/assistant.py` to accept a `history` parameter and prepend prior turns as LLM messages before the context + question block (embedding/retrieval pipeline remains unchanged — only `query` is embedded)

**Checkpoint**: `cd apps/api && pytest tests/test_assistant_history.py -v` — all tests pass. Manually `curl` the endpoint with and without `history` to confirm backward-compatible behavior.

---

## Phase 3: User Story 1 — Ask a Question on the Landing Page (Priority: P1) 🎯 MVP

**Goal**: User arrives at the root URL, sees a chat input as the primary interface, types a question, submits it, sees a loading indicator, then sees the LLM answer rendered in the conversation area.

**Independent Test**: Navigate to `localhost:3000`, type any question, press Enter or click **Ask**, verify loading indicator appears and then a meaningful answer renders — without a full page reload.

**⚠️ TDD: Write T006 first and confirm it FAILS before implementing T007–T010**

- [X] T006 [P] [US1] Write failing Vitest tests in `apps/web/tests/chat.test.tsx` covering: chat input textarea renders on landing page; submit button is present; submitting a question calls `askAssistant`; loading indicator appears while pending; answer text renders after response; question input clears after successful submission
- [X] T007 [P] [US1] Create `apps/web/components/chat/MessageBubble.tsx` — renders one `ChatTurn`: user question in a right-aligned `slate-100` bubble, assistant answer in a left-aligned `slate-50` bubble with optional citation list; uses `indigo-600` accent for sender label; handles `status === "pending"` with a spinner and `status === "error"` with a `red-*` error marker
- [X] T008 [US1] Create `apps/web/components/chat/ChatInterface.tsx` — full conversation UI: scrollable turn list rendering `<MessageBubble />` for each turn; auto-resize textarea (single-row default, expands on content); **Ask** submit button with `indigo-600` / `indigo-700` hover styling; empty-state prompt ("Ask a question to get started") when `turns` is empty; calls `askAssistant` on submit and appends a `ChatTurn` with `status: "pending"` immediately
- [X] T009 [US1] Update `apps/web/app/page.tsx` — render `<ChatInterface />` as the primary full-width content above the fold; move existing stats cards and nav links into a secondary section below the chat, accessible without a toggle (no collapse in MVP — just below the fold)
- [X] T010 [P] [US1] Update `apps/web/tests/home.test.tsx` to assert `<ChatInterface />` is present as the primary element; remove any assertions that required the stats dashboard to be above the fold

**Checkpoint**: `cd apps/web && npm test` passes. Visiting `localhost:3000` shows the chat UI; a real question returns a real answer; stats cards remain visible by scrolling down.

---

## Phase 4: User Story 2 — Conversational Follow-Up (Priority: P2)

**Goal**: The conversation maintains multiple turns in state; each new submission derives `history` from completed turns and forwards it to the API; a "New conversation" button clears all turns.

**Independent Test**: Submit two related questions in sequence — the second answer demonstrates awareness of the first. Click **New conversation** — history clears and the next submission is treated as a fresh start.

**⚠️ TDD: Write T011 first and confirm it FAILS before implementing T012–T013**

- [X] T011 [P] [US2] Write failing Vitest tests in `apps/web/tests/chat.test.tsx` covering: multiple turns render in chronological order; `askAssistant` is called with a `history` array derived from all prior completed turns; "New conversation" button clears `turns` state to `[]` and empties the input
- [X] T012 [US2] Extend `apps/web/components/chat/ChatInterface.tsx` to maintain `turns: ChatTurn[]` in React state; before each submission, derive `history: HistoryMessage[]` by filtering completed turns (`status === "complete"` and `answer.answer !== null`) and flat-mapping each to `[{role:"user", content: question}, {role:"assistant", content: answer}]`; pass derived history to `askAssistant`
- [X] T013 [US2] Add a "New conversation" text button to the `ChatInterface.tsx` header that resets `turns` to `[]` and clears the textarea; button should only be visible when `turns.length > 0`

**Checkpoint**: Submit "What topics are covered?" then "Can you elaborate on the first one?" — second answer is context-aware. "New conversation" resets to empty state.

---

## Phase 5: User Story 3 — Empty and Error States (Priority: P3)

**Goal**: Empty or whitespace-only submissions are blocked before reaching the API; LLM service errors surface an inline error message and retain the user's question in the textarea.

**Independent Test**: Submit with an empty textarea — button is disabled, nothing is sent. Stop the API server, submit a question — an inline error appears in the conversation and the question is pre-filled in the textarea.

**⚠️ TDD: Write T014 first and confirm it FAILS before implementing T015–T016**

- [X] T014 [P] [US3] Write failing Vitest tests in `apps/web/tests/chat.test.tsx` covering: submit button is `disabled` when textarea is empty; submit button is `disabled` when textarea contains only whitespace; pressing Enter on an empty textarea does nothing; on API error, the failed turn renders with `status === "error"` and an error message; after API error, the textarea is re-populated with the failed question
- [X] T015 [US3] Implement empty-input prevention in `apps/web/components/chat/ChatInterface.tsx` — compute `isSubmittable = input.trim().length > 0`; set `disabled={!isSubmittable}` on the submit button with `disabled:opacity-50 disabled:cursor-not-allowed` styling; block the Enter-key handler when `!isSubmittable`
- [X] T016 [US3] Implement error state handling in `apps/web/components/chat/ChatInterface.tsx` — wrap the `askAssistant` call in a try/catch; on failure, update the pending turn to `{ status: "error", errorMessage: <message> }` and re-populate the textarea with the failed question so the user can retry

**Checkpoint**: Empty textarea → button visually disabled, no request sent. With API stopped → error marker appears in conversation, textarea re-populated with the question.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates, type safety, responsive validation, and full test suite sign-off.

- [X] T017 [P] Run `cd apps/api && ruff check tessera_api/ && black --check tessera_api/` and fix all lint/formatting violations in modified files (`routers/assistant.py`, `rag/assistant.py`, `tests/test_assistant_history.py`)
- [X] T018 [P] Run `cd apps/web && npx tsc --noEmit` and fix all TypeScript type errors across new and modified files (`lib/types.ts`, `lib/chat.ts`, `components/chat/ChatInterface.tsx`, `components/chat/MessageBubble.tsx`, `app/page.tsx`)
- [X] T019 Run full test suites: `cd apps/api && pytest tests/test_assistant_history.py -v` and `cd apps/web && npm test` — all tests must pass with no skips
- [X] T020 Validate responsive layout at 320 px using browser dev tools: chat textarea and **Ask** button fully visible and usable; conversation turns do not overflow horizontally; stats section below is readable

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately; T001 and T002 are parallel
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS US2 (history feature)
- **US1 (Phase 3)**: Depends on Phase 1 types; does NOT require backend changes (existing endpoint works for single-turn)
  - T006 must be written and FAIL before T007–T010
  - T007 and T006 can run in parallel (different files)
- **US2 (Phase 4)**: Depends on Phase 2 (backend history) AND Phase 3 (ChatInterface exists); T011 must fail before T012–T013
- **US3 (Phase 5)**: Depends on Phase 3 (ChatInterface exists); independent of Phase 2; T014 must fail before T015–T016
- **Polish (Phase 6)**: Depends on all user story phases complete; T017 and T018 are parallel

### User Story Dependencies

- **US1 (P1)**: Requires Phase 1 (types + API wrapper) only — no backend changes needed
- **US2 (P2)**: Requires Phase 2 (backend history) AND US1 (ChatInterface must exist to extend)
- **US3 (P3)**: Requires US1 (ChatInterface must exist to add validation/error handling); independent of US2

### Within Each Phase

1. Test tasks (TDD) MUST be written and confirmed FAILING before implementation
2. T007 (MessageBubble) before T008 (ChatInterface uses it)
3. T008 (ChatInterface) before T009 (page.tsx imports it)

---

## Parallel Execution Examples

### Phase 1 — Setup (run together)

```
Task T001: Add types to apps/web/lib/types.ts
Task T002: Create apps/web/lib/chat.ts
```

### Phase 3 — US1 (tests + bubble can start together, then ChatInterface, then page)

```
# Round 1 — parallel:
Task T006: Write failing tests in apps/web/tests/chat.test.tsx
Task T007: Create apps/web/components/chat/MessageBubble.tsx

# Round 2 — after T006 confirmed failing, T007 complete:
Task T008: Create apps/web/components/chat/ChatInterface.tsx

# Round 3 — after T008:
Task T009: Update apps/web/app/page.tsx
Task T010: Update apps/web/tests/home.test.tsx  [P with T009]
```

### Phase 6 — Polish (quality gates run together)

```
Task T017: Ruff + Black on apps/api/
Task T018: tsc --noEmit on apps/web/
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001, T002)
2. Complete Phase 3: US1 (T006–T010) — skipping backend changes
3. **STOP and VALIDATE**: Visit `localhost:3000`, submit a question, verify end-to-end
4. Demo: single-turn LLM chat on the landing page is fully functional

### Incremental Delivery

1. Phase 1 (Setup) → Foundation ready
2. Phase 3 (US1) → **MVP: chat on landing page** → Demo
3. Phase 2 (Foundational backend) → history API ready
4. Phase 4 (US2) → **Multi-turn conversations** → Demo
5. Phase 5 (US3) → **Resilient UX** → Demo
6. Phase 6 (Polish) → Quality gates pass → Ship

---

## Notes

- `[P]` tasks touch different files and have no unfinished dependencies — they are safe to parallelize
- `[Story]` label maps every implementation task to a user story for traceability
- Constitution Principle IV: every test MUST be written first and confirmed FAILING before the code it covers is written
- Constitution UI rules: use `slate-*` for neutrals, `indigo-600` / `indigo-700` for interactive elements, `red-*` for errors — never `gray-*` or `blue-*`
- Verify tests FAIL → implement → verify tests PASS before moving to the next phase
- Each story phase is a complete, independently demonstrable increment
