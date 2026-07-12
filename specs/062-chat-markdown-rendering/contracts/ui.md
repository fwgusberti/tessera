# UI Contracts: Chat Markdown Rendering

**Feature**: 062-chat-markdown-rendering | **Date**: 2026-07-11

No API contracts change — `POST /v1/chat/ask` and its response schema are
untouched. The contracts below are component/UI contracts within `apps/web`.

## C1. `MarkdownContent` — shared markdown renderer

**File**: `apps/web/components/markdown/MarkdownContent.tsx` (new, client component)

```ts
interface MarkdownContentProps {
  content: string;
  className?: string;          // prose wrapper classes supplied by the surface
  openLinksInNewTab?: boolean; // default false
}
```

Guarantees:

- Renders `content` via `react-markdown` with `remarkPlugins={[remarkGfm]}` —
  the identical parser/plugin configuration for every consumer (SC-002).
- Never enables raw HTML (`rehype-raw` is not used): embedded HTML/script in
  `content` is rendered inert or dropped, never executed (FR-004).
- Malformed markdown never throws; it degrades to literal text (edge case).
- When `openLinksInNewTab` is true, every rendered `<a>` carries
  `target="_blank"` and `rel="noopener noreferrer"` (FR-005).
- Applies `className` on the wrapper so the surface controls typography scale.

## C2. `DocumentContent` — document viewer (refactor, no behavior change)

**File**: `apps/web/components/documents/DocumentContent.tsx` (modified)

- Keeps its exact public prop: `{ version: DocumentVersion | null }`.
- Keeps its empty-state message when `version` is null.
- Delegates rendering to `MarkdownContent` with
  `className="prose prose-slate max-w-none"` and default link behavior.
- **Visual output must be pixel-equivalent to today** — existing
  document-viewer tests must pass unmodified.

## C3. `MessageBubble` — assistant answer body (modified)

**File**: `apps/web/components/chat/MessageBubble.tsx` (modified)

- Public prop unchanged: `{ turn: ChatTurn }`.
- For `status === "complete"` and `!answer.dont_know`, the answer body
  (previously `<p className="whitespace-pre-wrap">`) is replaced with
  `MarkdownContent` using
  `className="prose prose-sm prose-slate max-w-none break-words"` and
  `openLinksInNewTab` enabled, wrapped in an `overflow-x-auto` container so
  wide tables/code scroll inside the bubble (FR-007, US2-AC3).
- **Everything else is byte-for-byte unchanged** (FR-006): user question
  bubble, pending spinner (`role="status"`), error paragraph, don't-know
  message + suggested-space hint, and the citations block (still below the
  answer, still `target="_blank"`).

## C4. Test contract

**File**: `apps/web/tests/chat-markdown.test.tsx` (new)

Must assert, rendering `MessageBubble` (and `MarkdownContent` directly where
simpler):

1. Headings, bold, and bullet lists render as elements (`<h_>`, `<strong>`,
   `<li>`) with no literal `#`/`**`/`-` markers visible (US1-AC1, SC-001).
2. Plain-prose answers render as normal paragraphs (US1-AC2, FR-003).
3. Answer links have `target="_blank"` + `rel="noopener noreferrer"`
   (US1-AC3, FR-005).
4. Tables render `<table>` rows/columns; code blocks render `<pre><code>`
   (US2-AC1/AC2).
5. The answer body sits inside an `overflow-x-auto` container (US2-AC3,
   FR-007).
6. `<script>alert(1)</script>` in an answer produces no `script` element and
   its code does not execute (FR-004 edge case).
7. Literal markdown inside a code block stays visible as text (edge case).
8. Citations render below a formatted answer, unchanged (US3-AC1).

**Regression guards (must pass unmodified)**: `apps/web/tests/chat.test.tsx`
(FR-006/SC-003) and existing document-viewer suites, e.g.
`document-detail-modernized.test.tsx` (C2 no-behavior-change).
