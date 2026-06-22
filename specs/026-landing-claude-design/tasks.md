# Tasks: Landing Page Claude-Chat Design

**Input**: Design documents from `/specs/026-landing-claude-design/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ui-components.md ✅, quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in every description

---

## Phase 1: Setup

**Purpose**: Establish a passing baseline before any changes are made.

- [X] T001 Run the existing chat test suite to confirm it is green before changes: `pnpm --filter web test tests/chat.test.tsx` from repo root; record any pre-existing failures

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: Update the landing page wrapper before implementing any chat layout — ChatInterface must receive correct height context.

**⚠️ CRITICAL**: This must complete before any user story implementation can begin.

- [X] T002 Simplify `apps/web/app/page.tsx` — remove `StatCard`, `NavCard`, stats API fetch (`/v1/spaces`, `/v1/metrics`), and loading state; replace body with `AuthGuard` wrapping a `<div className="-mx-4 -my-8 min-h-[calc(100dvh-3.25rem)] flex flex-col">` that renders `<ChatInterface />` per `contracts/ui-components.md`

**Checkpoint**: Landing page renders `ChatInterface` in a full-height wrapper; no stat cards or nav cards visible.

---

## Phase 3: User Story 1 — Centered Chat Welcome Screen (Priority: P1) 🎯 MVP

**Goal**: When `turns.length === 0`, show a centered welcome view with `h1` "Tessera", a tagline, and the centered input area — no dashboard widgets anywhere.

**Independent Test**: Navigate to `http://localhost:3000/` as an authenticated user with no prior turns. Verify: `h1` "Tessera" is visible, tagline is visible, input and Ask button are centered and visible, no stat/nav cards present.

### Tests for User Story 1

> **Write these tests FIRST and confirm they FAIL before implementing T004**

- [X] T003 [US1] In `apps/web/tests/chat.test.tsx`, update the existing empty-state test — change the assertion from its current placeholder text to `screen.getByRole("heading", { name: /tessera/i })` and add an assertion that the tagline text is visible; run tests and confirm T003 now fails

### Implementation for User Story 1

- [X] T004 [US1] Implement the welcome view branch in `apps/web/components/chat/ChatInterface.tsx` — when `turns.length === 0`, render: a vertically centered flex column containing `<h1 className="text-4xl font-bold text-slate-900">Tessera</h1>`, a `<p className="text-lg text-slate-500">` tagline, and the textarea + Ask button wrapped in a `max-w-2xl w-full` container; remove any previous placeholder paragraph or empty-state element

**Checkpoint**: User Story 1 fully functional — welcome heading and centered input visible with no prior turns; T003 tests pass.

---

## Phase 4: User Story 2 — Pinned Input Bar with Chat History (Priority: P2)

**Goal**: When `turns.length > 0`, switch to conversation view: scrollable `MessageBubble` history fills the viewport, input bar is `sticky bottom-0`, "New conversation" button visible in header.

**Independent Test**: Send one message; scroll up through history; verify the input bar remains at the bottom of the viewport without scrolling down.

### Tests for User Story 2

> **Write these tests FIRST and confirm they FAIL before implementing T006**

- [X] T005 [US2] In `apps/web/tests/chat.test.tsx`, add a `describe("conversation view", ...)` block — simulate a state with one completed turn, then assert: (1) a `MessageBubble` element is rendered for that turn, (2) the "New conversation" button is present (`getByRole("button", { name: /new conversation/i })`), (3) the Ask button is still present; run tests and confirm T005 fails

### Implementation for User Story 2

- [X] T006 [US2] Implement the conversation view branch in `apps/web/components/chat/ChatInterface.tsx` — when `turns.length > 0`, render: a header row (`text-xl font-semibold text-slate-900` "Tessera" + "New conversation" `<button>`), the existing `MessageBubble` list in natural flow (body scrolls), and the textarea + Ask button in a `sticky bottom-0 bg-white border-t border-slate-200 py-4` bar with `max-w-3xl mx-auto` inner wrapper; clicking "New conversation" clears all turns

**Checkpoint**: User Stories 1 AND 2 functional — conversation view with sticky input and "New conversation" button; T005 tests pass.

---

## Phase 5: User Story 3 — Suggested Starter Prompts (Priority: P3)

**Goal**: 4 starter-prompt chips visible on the welcome screen; clicking one populates the input and focuses it; chips are hidden once `turns.length > 0`.

**Independent Test**: Load welcome screen — verify 4 chips are present. Click one — verify input is populated with that chip's text. Send a message — verify chips are no longer rendered.

### Tests for User Story 3

> **Write these tests FIRST and confirm they FAIL before implementing T008**

- [X] T007 [US3] In `apps/web/tests/chat.test.tsx`, add a `describe("starter prompts", ...)` block with three tests: (1) assert 4 chip buttons are rendered on the welcome screen (verify at least one chip text, e.g. "What's in our product roadmap?"); (2) simulate a click on one chip and assert the textarea value equals that chip's text; (3) simulate a state with one turn and assert no chip buttons are present; run tests and confirm T007 fails

### Implementation for User Story 3

- [X] T008 [US3] In `apps/web/components/chat/ChatInterface.tsx` — add module-level constant `const STARTER_PROMPTS = ["What's in our product roadmap?", "Summarize the latest meeting notes", "Find our onboarding documentation", "What changed in the last release?"] as const`; add `inputRef = useRef<HTMLTextAreaElement>(null)` if not already present and attach to the textarea; in the welcome view render `STARTER_PROMPTS.map` with chip buttons styled `rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-600 hover:border-indigo-400 hover:text-indigo-600 transition-colors bg-white` in a `flex flex-wrap gap-2 justify-center` container; chip `onClick` calls `setInput(label)` then `inputRef.current?.focus()`; chips only render when `turns.length === 0`

**Checkpoint**: All three user stories functional and independently testable; T007 tests pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate the complete feature end-to-end and confirm no regressions.

- [X] T009 [P] Run the full web test suite from repo root: `pnpm --filter web test` — all tests must pass including pre-existing tests and the new T003/T005/T007 tests
- [X] T010 Run all seven quickstart.md validation scenarios against the local dev server (`pnpm --filter web dev`) — Scenarios 1–7 must all reach their pass criterion
- [X] T011 [P] Verify mobile responsiveness using browser DevTools at 375 × 812 px — confirm no horizontal scroll, no clipped elements on welcome screen, and sticky input bar in conversation view (quickstart Scenario 6)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — run immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user story phases
- **US1 (Phase 3)**: Depends on Foundational — write T003 tests first, then T004 implementation
- **US2 (Phase 4)**: Depends on Foundational — write T005 tests first, then T006 implementation; may start after Phase 3 Checkpoint
- **US3 (Phase 5)**: Depends on US1 (Phase 3) — chips are added to the welcome view; write T007 tests first, then T008 implementation
- **Polish (Phase 6)**: Depends on all user story phases complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no story dependencies
- **US2 (P2)**: After Foundational — independent of US1 (opposite ternary branch in same file); start after US1 checkpoint
- **US3 (P3)**: After US1 — chips live in the welcome view (same branch as US1)

### Within Each User Story

- Tests MUST be written and confirmed failing before implementation
- Checkpoint validation before moving to next story

### Parallel Opportunities

- T003 and T005 test tasks can both be drafted concurrently (different describe blocks in the same file, no implementation dependencies)
- T009 and T011 (Polish) can run in parallel

---

## Parallel Example: All Test Tasks

```bash
# Once T002 (Foundational) is complete, all three test tasks can be drafted together:
Task T003: Update empty-state test in apps/web/tests/chat.test.tsx
Task T005: Add conversation-view describe block in apps/web/tests/chat.test.tsx
Task T007: Add starter-prompts describe block in apps/web/tests/chat.test.tsx
# Run once: pnpm --filter web test  → all three should fail before any implementation
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002)
3. Write T003 test → confirm it fails → implement T004
4. **STOP and VALIDATE**: Welcome screen visible, heading "Tessera" shown, centered input — US1 is independently shippable
5. Run quickstart Scenario 1 to confirm MVP

### Incremental Delivery

1. Setup + Foundational → baseline ready
2. US1 (T003–T004) → welcome screen ✅ Deploy/demo (MVP)
3. US2 (T005–T006) → conversation + sticky input ✅ Deploy/demo
4. US3 (T007–T008) → starter prompts ✅ Deploy/demo
5. Polish (T009–T011) → full validation

---

## Notes

- All three user stories modify `apps/web/components/chat/ChatInterface.tsx` — implement them sequentially within that file
- No new npm packages; no backend changes; no root layout restructure
- Design tokens: `slate-*` neutrals, `indigo-600/700/500` accents (constitution §UI Design System)
- NavBar height constant: `3.25rem` — used in `min-h-[calc(100dvh-3.25rem)]` on the page.tsx wrapper
- Layout mode is derived (no new state variable): `turns.length === 0` → welcome view; `turns.length > 0` → conversation view
- Sticky positioning chosen over fixed to avoid padding-bottom fragility (see research.md)
