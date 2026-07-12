# Tasks: Chat Markdown Rendering

**Input**: Design documents from `/specs/062-chat-markdown-rendering/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui.md, quickstart.md

**Tests**: Included — Constitution Principle IV (Test-Driven Development) requires the new Vitest suite to be written first, and the plan/contract C4 define it explicitly.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. This feature is frontend-only: all paths are under `apps/web/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup

**Purpose**: Confirm the existing rendering stack and regression baseline before changing anything. No new dependencies are introduced.

- [X] T001 Verify `react-markdown` ^9, `remark-gfm` ^4, and `@tailwindcss/typography` ^0.5 are present in `apps/web/package.json` and installed (`cd apps/web && npm install`); no additions expected
- [X] T002 Establish the regression baseline: run `cd apps/web && npx vitest run tests/chat.test.tsx tests/document-detail-modernized.test.tsx` and confirm both suites pass before any change (they are the FR-006/C2 regression guards and must pass unmodified at the end)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared `MarkdownContent` renderer (contract C1) that both user stories consume. No story work can begin until it exists.

**⚠️ CRITICAL**: US1 (chat rendering) and US2 (viewer parity) both delegate to this component.

- [X] T003 Write failing unit tests for the `MarkdownContent` contract (C1) in `apps/web/tests/chat-markdown.test.tsx`, rendering the component directly: (a) markdown headings/bold/lists/tables/code render as elements via GFM; (b) `className` is applied to the wrapper; (c) `openLinksInNewTab` default `false` adds no `target`, `true` adds `target="_blank"` + `rel="noopener noreferrer"` on every `<a>`; (d) `<script>alert(1)</script>` input produces no `script` element and does not execute (FR-004); (e) malformed markdown (unclosed `**`) renders legibly as text without throwing
- [X] T004 Implement `MarkdownContent` client component in `apps/web/components/markdown/MarkdownContent.tsx` with props `{ content: string; className?: string; openLinksInNewTab?: boolean }`: wraps `ReactMarkdown` with `remarkPlugins={[remarkGfm]}`, no `rehype-raw` (research R6), and a `components={{ a }}` override applying `target="_blank" rel="noopener noreferrer"` only when `openLinksInNewTab` is true (research R5); run T003 tests until green

**Checkpoint**: Shared renderer exists and satisfies contract C1 — user story phases can now begin.

---

## Phase 3: User Story 1 - Read a formatted chat answer (Priority: P1) 🎯 MVP

**Goal**: Assistant answers in the chat render as formatted markdown (headings, bold, lists, links) instead of raw markup text, with links opening in a new tab so the conversation is never discarded.

**Independent Test**: Render `MessageBubble` with an answer containing headings, bold text, and a list; verify real formatting with no visible markup symbols, and that answer links carry `target="_blank"`.

### Tests for User Story 1 ⚠️ write first, must fail before implementation

- [X] T005 [US1] Add failing `MessageBubble` tests to `apps/web/tests/chat-markdown.test.tsx` (contract C4 items 1–3): (a) an answer with `#` heading, `**bold**`, and `-` list renders `<h_>`/`<strong>`/`<li>` elements with no literal `#`/`**`/`-` markers visible outside code (US1-AC1, SC-001); (b) a plain-prose answer renders as normal paragraphs (US1-AC2, FR-003); (c) a markdown link in the answer renders with `target="_blank"` and `rel="noopener noreferrer"` (US1-AC3, FR-005)

### Implementation for User Story 1

- [X] T006 [US1] Modify `apps/web/components/chat/MessageBubble.tsx` per contract C3: replace only the answer body `<p className="whitespace-pre-wrap">{turn.answer.answer}</p>` with `MarkdownContent` using `className="prose prose-sm prose-slate max-w-none break-words"` and `openLinksInNewTab`, wrapped in an `overflow-x-auto` container; keep the public prop `{ turn: ChatTurn }` and every other state (question bubble, pending spinner, error, don't-know + suggested-space hint, citations block) byte-for-byte unchanged (FR-006)
- [X] T007 [US1] Verify US1: run `cd apps/web && npx vitest run tests/chat-markdown.test.tsx` (T003 + T005 green) and `npx vitest run tests/chat.test.tsx` (must pass unmodified)

**Checkpoint**: Chat answers render formatted — MVP delivered and independently testable.

---

## Phase 4: User Story 2 - Formatting parity with the document viewer (Priority: P2)

**Goal**: Tables, code blocks, and other rich elements render in chat with the same visual treatment as the document viewer, structurally guaranteed by having both surfaces delegate to the shared renderer; wide elements stay contained inside the bubble.

**Independent Test**: Render `MessageBubble` with an answer containing a table and a code block; verify `<table>` and `<pre><code>` elements and that the answer body sits inside an `overflow-x-auto` container. Confirm the document viewer's output is unchanged.

### Tests for User Story 2 ⚠️ write first, must fail before implementation

- [X] T008 [US2] Add failing parity/containment tests to `apps/web/tests/chat-markdown.test.tsx` (contract C4 items 4, 5, 7): (a) an answer with a GFM table renders `<table>` rows/columns (US2-AC1); (b) a fenced code block renders `<pre><code>` (US2-AC2); (c) the rendered answer body sits inside an `overflow-x-auto` container (US2-AC3, FR-007); (d) literal markdown syntax quoted inside a code block stays visible as text (edge case)

### Implementation for User Story 2

- [X] T009 [US2] Refactor `apps/web/components/documents/DocumentContent.tsx` per contract C2: keep prop `{ version: DocumentVersion | null }` and the null empty-state message; delegate rendering to `MarkdownContent` with `className="prose prose-slate max-w-none"` and default link behavior — visual output must be pixel-equivalent to today
- [X] T010 [US2] Verify US2: run `cd apps/web && npx vitest run tests/chat-markdown.test.tsx` (T008 green) and the document-viewer regression suite `npx vitest run tests/document-detail-modernized.test.tsx` unmodified (C2 no-behavior-change proof)

**Checkpoint**: Both surfaces share one renderer — parity is structural (SC-002); wide elements are contained (SC-004).

---

## Phase 5: User Story 3 - Existing chat behaviors are preserved (Priority: P3)

**Goal**: All non-answer chat states — pending spinner, error, don't-know (with suggested-space hint), citations — look and behave exactly as before the change.

**Independent Test**: Run the existing `chat.test.tsx` suite unmodified plus a citations-below-formatted-answer assertion; every state passes.

### Tests for User Story 3 ⚠️ write first, must fail before implementation

- [X] T011 [US3] Add failing test to `apps/web/tests/chat-markdown.test.tsx` (contract C4 item 8): an answer with markdown content **and** citations renders the citations list below the formatted answer, with citation links unchanged (`target="_blank"`, `/documents/{id}` href) (US3-AC1)

### Implementation for User Story 3

- [X] T012 [US3] Confirm regression guards: run `cd apps/web && npx vitest run tests/chat.test.tsx` — it MUST pass with zero edits to its assertions (FR-006, SC-003); if any assertion fails, fix `MessageBubble.tsx` (never the test) until green

**Checkpoint**: All chat states preserved; T011 citations test green.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Whole-suite validation, quality gates, and manual quickstart verification.

- [X] T013 Run the full web test suite: `cd apps/web && npx vitest run` — all suites pass with no edits to pre-existing test files
- [X] T014 [P] Run quality gates on the changed files: `cd apps/web && npm run lint` and `npm run build` (TypeScript must compile with no errors, per quickstart Done-when)
- [ ] T015 Execute the manual validation scenarios in `specs/062-chat-markdown-rendering/quickstart.md` (US1 formatted answer + new-tab link, US2 side-by-side parity + wide-element containment on desktop and narrow viewport, US3 pending/error/don't-know/citations, edge cases: unclosed `**`, `<script>` inertness, literal markdown in code block) — *status: every scenario has a passing automated equivalent in `chat-markdown.test.tsx`/`chat.test.tsx`; the in-browser visual pass (side-by-side parity, narrow viewport, real new-tab click) still needs a human — dev server is running at http://localhost:3000*

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **blocks all user stories** (both consume `MarkdownContent`)
- **US1 (Phase 3)**: Depends on Phase 2 only
- **US2 (Phase 4)**: Depends on Phase 2 only — independent of US1 for the `DocumentContent` refactor (T009); its containment test (T008c) inspects the `MessageBubble` change from T006, so run T008/T010 after US1 when working solo
- **US3 (Phase 5)**: Verification-only phase — meaningful after T006 exists
- **Polish (Phase 6)**: Depends on all user stories complete

### Task Dependencies

| Task | Depends on |
|------|-----------|
| T003 | T001 |
| T004 | T003 (tests failing first) |
| T005 | T004 |
| T006 | T005 (tests failing first) |
| T007 | T006 |
| T008 | T004 (and T006 for the containment assertion) |
| T009 | T004, T008 |
| T010 | T009 |
| T011 | T006 |
| T012 | T006 |
| T013–T015 | all prior |

### Parallel Opportunities

- **T009 (DocumentContent refactor) ∥ T006 (MessageBubble change)** — different files, both only depend on `MarkdownContent` (T004); two developers can take US1 and US2's refactor simultaneously after Phase 2
- **T011 ∥ T008** — independent test additions once T006 exists (coordinate on the shared test file if truly concurrent)
- **T014 ∥ T013** — lint/build and test run are independent commands

Most tasks touch the same two files (`MessageBubble.tsx`, `chat-markdown.test.tsx`), so this feature is largely sequential for a solo developer — the natural order is simply T001 → T015.

### Parallel Example: after Phase 2 completes

```bash
# Developer A (US1):
Task: "T005 failing MessageBubble tests in apps/web/tests/chat-markdown.test.tsx"
Task: "T006 render answer via MarkdownContent in apps/web/components/chat/MessageBubble.tsx"

# Developer B (US2, refactor half):
Task: "T009 delegate rendering to MarkdownContent in apps/web/components/documents/DocumentContent.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (Setup) → Phase 2 (Foundational: `MarkdownContent` + its tests)
2. Phase 3 (US1): chat answers render formatted, links open in new tab
3. **STOP and VALIDATE**: `npx vitest run tests/chat-markdown.test.tsx tests/chat.test.tsx` — the feature's core value is delivered even without the `DocumentContent` refactor

### Incremental Delivery

1. Setup + Foundational → shared renderer ready
2. US1 → formatted chat answers (MVP — the entire user-visible ask)
3. US2 → structural parity via `DocumentContent` delegation + containment proof
4. US3 → regression confirmation (chat.test.tsx unmodified)
5. Polish → full suite, lint/build, manual quickstart

---

## Notes

- Constitution Principle IV: within every phase, tests are written and observed failing before the implementation task runs
- `apps/web/tests/chat.test.tsx` and `apps/web/tests/document-detail-modernized.test.tsx` must never be edited — they are the FR-006/SC-003 and C2 regression proofs
- No backend, storage, or API changes anywhere in this feature (plan Technical Context); the 85% Python coverage gate is unaffected
- Commit after each task or logical group
