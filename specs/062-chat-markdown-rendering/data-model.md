# Data Model: Chat Markdown Rendering

**Feature**: 062-chat-markdown-rendering | **Date**: 2026-07-11

This feature is display-only. **No database tables, API schemas, or stored
entities are added or modified.** The entities below already exist in
`apps/web/lib/types.ts` and are consumed unchanged; they are documented here
to anchor the rendering contract.

## Existing entities (unchanged)

### ChatTurn (client-side, in-memory only)

| Field | Type | Notes |
|-------|------|-------|
| `id` | `string` | Client-generated turn id |
| `question` | `string` | User's typed question — always rendered as plain text (spec Assumptions: question bubble unaffected) |
| `status` | `"pending" \| "complete" \| "error"` | Drives which bubble state renders; states other than the complete answer body are untouched (FR-006) |
| `errorMessage` | `string?` | Rendered as plain text, unchanged |
| `answer` | `AssistantAnswer \| null` | Present when `status === "complete"` |

### AssistantAnswer (existing API response shape, unchanged)

| Field | Type | Notes |
|-------|------|-------|
| `answer` | `string` | **The only field whose presentation changes**: now interpreted as markdown and rendered formatted (FR-001). May contain markup originating from source documents; may be plain prose (FR-003); may contain raw HTML, which must stay inert (FR-004) |
| `confidence` | `number` | Unused by rendering |
| `dont_know` | `boolean` | When true, the don't-know message renders exactly as today (FR-006) |
| `suggested_owner` | `{ space_name: string, … }?` | Unchanged |
| `citations` | `Citation[]?` | Quotes remain plain-text excerpts (spec Assumptions); list renders below the formatted answer, unchanged |

## New component-level model (no persistence)

### MarkdownContent props

| Prop | Type | Notes |
|------|------|-------|
| `content` | `string` | Markdown source to render |
| `className` | `string?` | Prose wrapper classes; each surface supplies its scale (viewer: `prose prose-slate max-w-none`; chat: `prose prose-sm prose-slate max-w-none break-words`) |
| `openLinksInNewTab` | `boolean?` | Default `false` (viewer behavior). Chat passes `true` → anchors get `target="_blank" rel="noopener noreferrer"` (FR-005) |

## State transitions

None added. The existing `ChatTurn.status` lifecycle
(`pending → complete | error`) is untouched; rendering is a pure function of
the already-delivered answer string.

## Validation rules

- Markdown parsing must never throw for malformed input — `react-markdown`
  degrades gracefully (unclosed `**` renders as literal text), satisfying the
  malformed-markup edge case.
- Raw HTML in `answer` must never become executable DOM (FR-004): enforced by
  omitting `rehype-raw` (see [research.md](./research.md) R6) and asserted by
  test.
