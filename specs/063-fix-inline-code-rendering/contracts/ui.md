# UI Contract: Inline Code Rendering

**Feature**: 063-fix-inline-code-rendering | **Date**: 2026-07-11

This feature exposes no API, CLI, or schema contract. Its externally
observable interface is the rendered appearance of markdown content on the
two display surfaces. This document is the binding contract for that
appearance.

## Surfaces in scope

| Surface | Component | Wrapper classes |
|---|---|---|
| Chat answer | `apps/web/components/chat/MessageBubble.tsx` → `MarkdownContent` | `prose prose-sm prose-slate max-w-none break-words` |
| Document viewer | `apps/web/components/documents/DocumentContent.tsx` → `MarkdownContent` | `prose prose-slate max-w-none` |

Both surfaces MUST render identical inline-code treatment for identical
input (SC-004).

## CSS contract

`apps/web/app/globals.css` MUST contain an override that suppresses the
typography plugin's decorative backticks on inline code:

```css
.prose code::before,
.prose code::after {
  content: none;
}
```

- The selector MUST target `.prose code` (specificity (0,1,2)) so it beats
  the plugin's `:where()`-based rule (specificity (0,1,1)) regardless of
  source order.
- The rule MUST NOT alter any other declaration of the `code` element
  (font-family, color, font-weight remain governed by the plugin and the
  existing `--tw-prose-code` variable).

## Rendering contract (per markdown input)

| # | Input (markdown) | Required rendering | Spec ref |
|---|---|---|---|
| C1 | `` Run `main` now `` | `<code>main</code>`; no backtick visible before or after the snippet; surrounding prose unchanged | FR-001, US1 |
| C2 | Sentence with several inline snippets | Every snippet per C1; prose between them intact | US1-AS3 |
| C3 | Inline snippet inside bold, link, heading, list item, or table cell | Rendered as distinct code there too, no backticks | FR-002, US2-AS2, edge case |
| C4 | Inline code anywhere | Visually distinct from prose: monospace (Geist Mono via `--font-mono`), `--tw-prose-code` color — unchanged from today except the backticks | FR-002, US2 |
| C5 | Fenced code block whose content includes `` ` `` characters | Backticks inside the block remain visible verbatim | FR-004, US3-AS1 |
| C6 | Prose containing a single unpaired `` ` `` | The backtick appears as typed (it is a text node, not decoration) | FR-004, US3-AS2 |
| C7 | Empty/whitespace-only inline span (```` `` ````, `` ` ` ``) | No stray symbols or layout artifacts | Edge case |
| C8 | All other markdown elements (headings, bold, lists, links, tables, quotes, code blocks) | Render exactly as before this fix | FR-005, SC-003 |

## Verification mapping

| Contract | Automated check | Manual check |
|---|---|---|
| CSS contract | Stylesheet regression test in `apps/web/tests/inline-code-rendering.test.tsx` (reads `globals.css`) | Browser DevTools: `code::before` computed `content` is `none` |
| C1–C3, C5–C7 (markup layer) | DOM assertions in `inline-code-rendering.test.tsx` for both surfaces | quickstart.md scenarios |
| C4 (visual distinction) | `<code>` element presence asserted in DOM tests | quickstart.md visual check |
| C8 (no regressions) | Existing `chat-markdown.test.tsx`, `documents*.test.tsx` suites must keep passing | quickstart.md side-by-side check |
| SC-001/SC-004 (pixels) | Not automatable in jsdom (pseudo-elements) — see research.md R3 | quickstart.md visual check |
