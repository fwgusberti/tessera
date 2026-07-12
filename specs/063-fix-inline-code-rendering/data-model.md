# Data Model: Fix Inline Code Rendering

**Feature**: 063-fix-inline-code-rendering | **Date**: 2026-07-11

## Entities

None. This is a presentation-layer (CSS-only) fix with no data implications:

- **No new or modified entities** — no database tables, columns, domain
  models, or API payloads change.
- **No state transitions** — the fix is a static style rule with no runtime
  state.
- **Existing data is untouched**: chat answers (delivered by
  `POST /v1/chat/ask`) and document version content (`content_markdown`)
  are already stored and transported without decorative backticks; the
  defect exists purely in how the `prose` styles decorate the rendered
  `<code>` elements (see [research.md](./research.md) R1).

## Display-layer contract (informational)

The only "model" involved is the rendered DOM produced by the shared
`MarkdownContent` component, which is unchanged:

| Markdown input | Rendered element | Visual after fix |
|---|---|---|
| `` `snippet` `` (inline code) | `<code>snippet</code>` | monospace, `--tw-prose-code` color, **no** backtick pseudo-elements |
| fenced code block | `<pre><code>…</code></pre>` | unchanged (never had pseudo-element backticks) |
| literal backtick in prose (unpaired) | text node containing `` ` `` | unchanged — real content, not decoration |

See [contracts/ui.md](./contracts/ui.md) for the full UI contract.
