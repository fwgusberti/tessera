# Data Model: Formatted Search Results with Document Navigation

**Feature**: `064-format-search-results` | **Date**: 2026-07-11

No new persistent entities, tables, or migrations. This feature is a
presentation-layer change over existing data. The entities below describe the
client-side view model consumed by the search page.

## SearchResult (existing API shape, consumed as-is)

Returned by `POST /v1/search` (`apps/api/tessera_api/routers/search.py`);
already typed on the frontend in `app/search/page.tsx`.

| Field | Type | Used by this feature as |
|-------|------|------------------------|
| `document_id` | UUID string | Navigation target: `/documents/{document_id}` (FR-006) |
| `version_id` | UUID string | Not used by the card (kept in the type) |
| `chunk_id` | UUID string | React list key (existing behavior) |
| `score` | number (0–1) | Relevance indicator, kept visible (FR-009) |
| `snippet` | string (Markdown fragment, ≤300 chars) | Rendered as formatted rich text (FR-002) |
| `citation.document_title` | string \| undefined | Card title; fallback `"Untitled document"` when absent (FR-001, FR-008) |
| `citation.source` | string \| undefined | Not used by the card |

### Validation / display rules

- **Title**: `citation.document_title` trimmed; if missing or empty →
  display `"Untitled document"`. Card remains clickable either way (FR-008).
- **Snippet**: rendered through `MarkdownContent`; embedded HTML is escaped,
  never executed (FR-003); headings render at card scale, links render as
  inert styled text (FR-005, research R2/R3); long unbroken tokens wrap
  (`break-words`) and overflow is clipped so malformed input stays contained
  (FR-004).
- **Score**: displayed as percentage (`(score * 100).toFixed(0)%`), unchanged.

## Document (existing entity, unchanged)

The navigation destination. Fetched by the existing document detail page
(`app/documents/[id]/page.tsx` → `GET /v1/documents/{id}`), which already
handles not-found / no-access states for deleted or inaccessible documents
(spec edge case). No fields added or changed.

## State transitions

None — search results are ephemeral view state (React `useState`), discarded
on navigation; browser history preserves the search page for Back navigation
(US2 scenario 3).
