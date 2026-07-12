# UI Contract: Search Result Card

**Feature**: `064-format-search-results` | **Date**: 2026-07-11

No new or modified HTTP endpoints. This feature consumes two existing
contracts and defines the UI contract of the result card built on them.

## Consumed API contracts (unchanged)

### `POST /v1/search`

Request: `{ "query": string, "space_ids"?: UUID[], "language"?: string, "top_k"?: number }`

Response `200`:

```json
{
  "results": [
    {
      "document_id": "uuid",
      "version_id": "uuid",
      "chunk_id": "uuid",
      "score": 0.87,
      "snippet": "## Setup\n\nRun **npm install** and…",
      "citation": { "document_title": "Getting Started", "source": "…" }
    }
  ]
}
```

The card relies on: `document_id`, `score`, `snippet`,
`citation.document_title` (optional). See [data-model.md](../data-model.md).

### `GET /v1/documents/{id}` (navigation destination)

Existing document detail page contract, including its not-found / no-access
error handling. Unchanged.

## UI contract: result card (`app/search/page.tsx`)

For every entry in `results`, in Search mode:

| # | Guarantee | Spec ref |
|---|-----------|----------|
| 1 | Document title (or `Untitled document` fallback) renders at the top of the card, visually more prominent than the excerpt | FR-001, FR-008 |
| 2 | `snippet` renders as formatted rich text — bold, lists, inline code, headings interpreted; no raw Markdown syntax shown as plain text | FR-002 |
| 3 | Embedded HTML/script in `snippet` is escaped text, never live DOM/executed | FR-003 |
| 4 | Malformed/truncated Markdown stays visually contained inside its own card | FR-004 |
| 5 | Headings inside the excerpt render at card scale, not page-title scale | FR-005 |
| 6 | Clicking anywhere on the card (or pressing Enter/Space with the card focused) navigates client-side to `/documents/{document_id}` | FR-006 |
| 7 | Card exposes `role="link"`, `tabIndex=0`, pointer cursor, and a visible hover state | FR-006, FR-007 |
| 8 | Markdown links inside the excerpt render as styled, non-navigating text; they never override card navigation | Edge case (links) |
| 9 | Relevance score remains visible on the card as a percentage | FR-009 |
| 10 | Browser Back from the document page returns to the search page (client-side `router.push`, history preserved) | US2 scenario 3 |

## Component contract: `MarkdownContent` (extended)

`apps/web/components/markdown/MarkdownContent.tsx`

```ts
interface MarkdownContentProps {
  content: string;
  className?: string;
  openLinksInNewTab?: boolean;   // existing
  components?: Components;       // NEW: react-markdown element overrides;
                                 // caller entries take precedence over the
                                 // component's own openLinksInNewTab override
}
```

Backward compatibility: `components` is optional; existing call sites
(`DocumentContent`, chat `MessageBubble`) compile and behave identically
without changes.
