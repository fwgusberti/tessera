# Quickstart: Fix Inline Code Rendering

**Feature**: 063-fix-inline-code-rendering | **Date**: 2026-07-11

Validation guide proving inline code renders without backtick symbols on both
display surfaces. Contracts: [contracts/ui.md](./contracts/ui.md); background:
[research.md](./research.md).

## Prerequisites

- Node dependencies installed at the repo root (`npm install` already done —
  `node_modules/` exists).
- For the visual checks: the app running locally with a signed-in user that
  has at least one space and one document.

## 1. Automated tests

```bash
# New feature suite (DOM assertions + stylesheet regression test)
npx vitest run tests/inline-code-rendering.test.tsx --root apps/web

# Regression guards (FR-005 / SC-003): markdown + document suites must still pass
npx vitest run tests/chat-markdown.test.tsx --root apps/web
npx vitest run --root apps/web
```

**Expected**: all tests pass. Before the CSS fix is applied, the stylesheet
regression test in `inline-code-rendering.test.tsx` fails (TDD failing-first
proof); after the fix it passes.

## 2. Visual validation — document viewer

1. Start the web app (`npm run dev` in `apps/web`) and sign in.
2. Create or edit a document whose body includes:

   ```markdown
   Deploy from the `main` branch using `git push`.

   - Run `npm test` first
   - The `CI` pipeline must be green

   | Command | Purpose |
   | --- | --- |
   | `make build` | Build |

   ```text
   Literal backticks stay: `example`
   ```

   A lone backtick ` in prose stays visible.
   ```

3. Open the document in the viewer.

**Expected** (SC-001/SC-002/FR-004):
- `main`, `git push`, `npm test`, `CI`, `make build` appear in monospace with
  the indigo code color and **no** surrounding backtick characters — in
  prose, list items, and the table cell alike.
- Inside the fenced block, `` `example` `` keeps its backticks verbatim.
- The lone backtick in the last paragraph is visible as typed.

## 3. Visual validation — chat

1. Open a space chat and ask a question whose answer will mention code, e.g.
   "Which branch do we deploy from?" against the document above.
2. Inspect the rendered answer bubble.

**Expected** (SC-001/SC-004): inline snippets in the answer render exactly as
in the document viewer — monospace, no backticks. Comparing the same snippet
side by side in chat and the viewer shows identical treatment.

## 4. No-regression sweep (SC-003)

On both surfaces, confirm headings, bold text, lists, links, tables, block
quotes, and fenced code blocks look unchanged from before the fix (the CSS
change touches only `code::before`/`code::after` pseudo-elements).

## 5. Quality gates

```bash
# Lint + typecheck for the web app
npm run lint --workspace apps/web
npx tsc --noEmit -p apps/web
```

**Expected**: clean. No Python changes in this feature, so Ruff/Black and the
Python coverage gate are unaffected.
