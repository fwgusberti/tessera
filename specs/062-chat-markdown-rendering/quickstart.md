# Quickstart: Chat Markdown Rendering

**Feature**: 062-chat-markdown-rendering | **Date**: 2026-07-11

Validation guide proving the feature works end-to-end. Details live in
[plan.md](./plan.md), [data-model.md](./data-model.md), and
[contracts/ui.md](./contracts/ui.md).

## Prerequisites

- Node.js 20+ and npm; repo dependencies installed:

  ```bash
  cd apps/web && npm install
  ```

- For the manual scenario: the full stack running (API + Postgres) with at
  least one indexed markdown document, e.g. via the repo's docker-compose /
  usual dev setup, then:

  ```bash
  cd apps/web && npm run dev
  ```

## Automated validation

```bash
cd apps/web
npx vitest run tests/chat-markdown.test.tsx   # new feature suite (contract C4)
npx vitest run tests/chat.test.tsx            # FR-006 regression guard — must pass unmodified
npx vitest run                                # full web suite
```

**Expected**: all pass. `chat.test.tsx` and the document-viewer suites pass
without any edits to their assertions.

## Manual validation scenarios

### US1 — formatted answer (P1)

1. Open the chat (home page), ask a question whose answer draws on a
   markdown-heavy document (headings, bold, bullets).
2. **Expected**: the answer shows rendered headings/bold/bullets; zero literal
   `#`, `**`, or `-` markers outside code blocks (SC-001).
3. Click a link inside an answer. **Expected**: opens in a new tab; the
   conversation is still on screen (US1-AC3).

### US2 — parity with the document viewer (P2)

1. Ask a question whose answer includes a table and a code block; open the
   source document in the viewer (`/documents/{id}`) side by side.
2. **Expected**: equivalent rendering (table with rows/columns, monospaced
   code block), only proportionally smaller in the bubble (SC-002).
3. Ask something yielding a wide table or long code line. **Expected**: the
   element scrolls horizontally inside the bubble; page layout intact on
   desktop and a narrow mobile viewport (SC-004).

### US3 — existing behaviors preserved (P3)

1. Ask a question → **Expected**: "Thinking…" spinner unchanged while pending.
2. Ask with the API stopped → **Expected**: error message unchanged.
3. Ask something unanswerable → **Expected**: don't-know message (and
   suggested-space hint when present) unchanged.
4. For an answer with sources → **Expected**: citations list below the
   formatted answer, links still open the document in a new tab (SC-003).

### Edge cases

- Answer with unclosed `**`: renders legibly as text, no broken bubble.
- Answer containing `<script>` or HTML: shown inert, never executed (check
  devtools console — no execution, no injected elements).
- Answer quoting literal markdown inside a code block: symbols stay visible.

## Done when

- All automated suites above pass.
- Manual US1–US3 scenarios and edge cases behave as expected.
- `npm run build` (apps/web) succeeds with no type errors.
