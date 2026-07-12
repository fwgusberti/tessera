# Research: Chat Markdown Rendering

**Feature**: 062-chat-markdown-rendering | **Date**: 2026-07-11

No NEEDS CLARIFICATION items remained in the Technical Context — the rendering
stack already exists in the repo and the spec is display-only. Research below
records the decisions and the alternatives considered.

## R1. Markdown rendering library

- **Decision**: Reuse `react-markdown` ^9 with `remark-gfm` ^4 — the exact
  stack `DocumentContent.tsx` already uses.
- **Rationale**: FR-002/SC-002 demand parity with the document viewer; using
  the same parser and plugin set makes the supported element set identical by
  construction. Both packages are already in `apps/web/package.json`, so no
  new dependency is introduced. GFM gives tables, strikethrough, task lists,
  and autolinks — matching the viewer.
- **Alternatives considered**:
  - `marked` / `markdown-it` + `dangerouslySetInnerHTML`: rejected — requires
    manual sanitization (XSS risk, FR-004) and diverges from the viewer stack.
  - Server-side rendering of answers to HTML: rejected — spec assumes a
    display-only change; would touch the API for no benefit.

## R2. Parity mechanism: shared component vs. duplicated markup

- **Decision**: Extract a shared `MarkdownContent` client component
  (`apps/web/components/markdown/MarkdownContent.tsx`) that wraps
  `ReactMarkdown` with `remarkPlugins={[remarkGfm]}` and the Tailwind
  typography (`prose prose-slate`) wrapper. `DocumentContent` delegates to it
  unchanged; `MessageBubble` uses it for the answer body.
- **Rationale**: SC-002 requires 100% element parity with the viewer. A single
  shared renderer makes drift impossible — any future plugin or style change
  applies to both surfaces. Duplicating `<ReactMarkdown …>` in `MessageBubble`
  would satisfy today's spec but decay silently.
- **Alternatives considered**:
  - Inline `ReactMarkdown` directly in `MessageBubble`: rejected — parity by
    copy-paste, breaks on the next viewer change.
  - Reusing `DocumentContent` itself in chat: rejected — its prop is a
    `DocumentVersion`, and its empty-state message is document-specific; the
    chat needs a plain-string interface.

## R3. Typography sizing inside the chat bubble

- **Decision**: The shared component accepts a `className` (or size variant)
  so each surface picks its scale: the document viewer keeps
  `prose prose-slate max-w-none`; the chat bubble uses
  `prose prose-sm prose-slate max-w-none break-words` to fit the existing
  `text-sm` bubble.
- **Rationale**: FR-002 allows visual treatment "adjusted only as needed to
  fit the chat bubble's dimensions". `prose-sm` is Tailwind typography's
  official small scale — same element styling, proportionally smaller, so the
  treatment still matches the viewer. `max-w-none` removes the default 65ch
  prose cap so the bubble's own `max-w-[85%]` governs width.
- **Alternatives considered**: full-size `prose` in the bubble — rejected,
  headings/margins overwhelm a `text-sm` bubble and look broken next to the
  user's question bubble.

## R4. Containment of wide elements (FR-007 / SC-004)

- **Decision**: Wrap the rendered markdown in the bubble with
  `overflow-x-auto` and rely on `break-words` for long unbroken strings.
  Wide tables and long code lines scroll horizontally *inside* the bubble;
  the conversation and page layout never overflow.
- **Rationale**: The bubble is already `max-w-[85%]`; an inner scroll
  container is the standard, minimal containment mechanism and matches the
  spec's "element is contained within the bubble" acceptance (US2-AC3).
- **Alternatives considered**: `table-fixed` + truncation — rejected, hides
  content; shrinking font per-element — rejected, unpredictable and diverges
  from the viewer.

## R5. Link behavior (FR-005)

- **Decision**: In the chat surface, markdown links render with
  `target="_blank"` and `rel="noopener noreferrer"` via a `components={{ a }}`
  override on `ReactMarkdown` (the `linkTarget` prop was removed in
  react-markdown v9). The override is opt-in through a prop on
  `MarkdownContent` (e.g. `openLinksInNewTab`), so the document viewer's
  current in-tab link behavior is unchanged.
- **Rationale**: Chat conversation state lives in client memory
  (`ChatInterface` React state); an in-tab navigation would discard it,
  violating FR-005/US1-AC3. New-tab links match how citation links already
  behave in `MessageBubble` today.
- **Alternatives considered**: persisting conversation state so in-tab
  navigation is safe — rejected, large scope increase and conflicts with
  Constitution Principle III (client-side persistence needs consent).

## R6. HTML / script neutralization (FR-004)

- **Decision**: Rely on `react-markdown`'s default behavior: raw HTML in the
  source is never parsed into DOM elements (no `rehype-raw` plugin), so
  embedded `<script>`, `<img onerror>`, etc. are rendered inert as text or
  dropped. A dedicated test asserts script content does not execute or
  produce elements.
- **Rationale**: This is the library's documented, default-safe posture and
  exactly matches the viewer (which also omits `rehype-raw`), so behavior
  stays consistent (FR-002) and safe (FR-004) with zero added code.
- **Alternatives considered**: `rehype-sanitize` — unnecessary while raw HTML
  is never enabled; revisit only if `rehype-raw` is ever added.

## R7. Plain-prose answers and line breaks (FR-003)

- **Decision**: No `remark-breaks` plugin. Paragraphs separated by blank
  lines render as paragraphs; single newlines inside a paragraph soft-wrap
  per standard markdown, identical to the document viewer. The current
  `whitespace-pre-wrap` on the answer `<p>` is removed along with that `<p>`
  (markdown block elements own their spacing).
- **Rationale**: Parity with the viewer is the spec's explicit reference
  (FR-002); adding a chat-only line-break plugin would create the exact
  divergence the feature exists to remove. Assistant answers originate from
  markdown source documents and use markdown paragraph conventions
  (spec Assumptions).
- **Alternatives considered**: `remark-breaks` in chat only — rejected as a
  parity violation; it would also render literal markdown examples
  differently in the two surfaces.

## R8. What is explicitly untouched (FR-006)

- Pending/loading spinner, error message, don't-know response (including the
  suggested-space hint), and the citations block in `MessageBubble` keep their
  exact current JSX. Only the `turn.answer.answer` paragraph is replaced by
  the markdown renderer. `chat.test.tsx` (asking, loading, errors, don't-know,
  citations) must keep passing unmodified, serving as the FR-006/SC-003
  regression proof; document-viewer suites guard the `DocumentContent`
  refactor.
