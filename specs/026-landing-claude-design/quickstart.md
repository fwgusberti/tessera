# Quickstart Validation Guide: Landing Page Claude-Chat Design

## Prerequisites

- Local dev server running: `pnpm --filter web dev` (port 3000)
- Logged-in user session (create one via `/register` if needed)
- Viewport can be resized (use browser DevTools)

## Scenario 1 — Welcome screen (FR-001, FR-002, FR-004, US1)

1. Navigate to `http://localhost:3000/` as an authenticated user with no prior turns.
2. **Expected**:
   - A centered heading "Tessera" is visible.
   - A tagline below the heading is visible (e.g., "Your knowledge, always answered.").
   - A large text area and an "Ask" button are prominently centered in the viewport.
   - No stat cards (Spaces, Total Queries, Documents with Drift) are present.
   - No "Quick Navigation" section is present.
3. **Pass criterion**: All elements visible without scrolling on a 1280×800 viewport.

## Scenario 2 — Starter prompt chips (FR-003, US3)

1. On the welcome screen, locate the starter-prompt chips below the input area.
2. **Expected**: 3–4 chips are visible (e.g., "What's in our product roadmap?").
3. Click one chip.
4. **Expected**:
   - The chip's text is inserted into the textarea.
   - The textarea has keyboard focus.
   - The chips are still visible (not yet hidden — the user hasn't sent anything).
5. **Pass criterion**: Input populated instantly (< 200 ms).

## Scenario 3 — Chips hidden after first message (US3, acceptance scenario 3)

1. Send a message (click "Ask" or press Enter after typing).
2. **Expected**: Starter-prompt chips are no longer visible once `turns.length > 0`.

## Scenario 4 — Conversation view, pinned input bar (FR-005, FR-006, FR-007, US2)

1. Send at least one message and wait for the response.
2. **Expected**:
   - The heading/tagline welcome screen disappears.
   - Messages are displayed in a scrollable area.
   - The input bar appears at the bottom of the viewport.
3. Send enough messages to make the page scroll (5–10 turns).
4. Scroll to the top of the message history.
5. **Expected**: The input bar remains visible and accessible at the bottom of the viewport without the user scrolling back down.
6. **Pass criterion**: Input bar pinned at viewport bottom throughout scrolling.

## Scenario 5 — "New conversation" resets to welcome screen

1. In conversation view, click "New conversation".
2. **Expected**:
   - All turns are cleared.
   - The welcome screen (heading, tagline, starter prompts, centered input) is shown again.

## Scenario 6 — Mobile viewport at 375 px (FR-010, SC-006)

1. Open DevTools → set viewport to 375 × 812 (iPhone SE / standard mobile).
2. Reload the landing page.
3. **Expected**:
   - Welcome heading and tagline visible without horizontal scroll.
   - Starter-prompt chips wrap onto multiple rows if needed — no overflow.
   - Input area is usable (textarea and Ask button not clipped).
4. Send a message and scroll up.
5. **Expected**: Input bar pinned at bottom on mobile too.
6. **Pass criterion**: No horizontal scroll; no clipped elements.

## Scenario 7 — Existing chat behaviors preserved (FR-008, SC-005)

1. Type a question and click Ask.
2. **Expected**: Loading indicator (spinner or "…") appears in the message area.
3. Wait for response.
4. **Expected**: Answer rendered in the message bubble.
5. Type a follow-up; verify the conversation history is included in the `askAssistant` call (check network tab or mock in test).
6. Simulate an error (disconnect network or modify mock).
7. **Expected**: Error message shown in turn; textarea re-populated with the failed question.

## Automated test commands

```bash
# Run unit tests (from repo root)
pnpm --filter web test

# Run only chat-related tests
pnpm --filter web test tests/chat.test.tsx
```

Expected result: all tests in `chat.test.tsx` pass, including updated empty-state and new starter-prompt tests.
