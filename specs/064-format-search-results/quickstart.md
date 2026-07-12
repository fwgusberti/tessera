# Quickstart: Formatted Search Results with Document Navigation

**Feature**: `064-format-search-results`

Validation guide for the reworked search result cards. Contracts:
[contracts/search-result-card.md](./contracts/search-result-card.md) ·
Data shape: [data-model.md](./data-model.md).

## Prerequisites

- Repo dependencies installed (`npm install` in `apps/web`; API/worker venvs per repo README).
- Backend stack running (API + PostgreSQL + Ollama embeddings + workers), e.g. via the repo's usual `make`/docker-compose targets, so `POST /v1/search` returns results.
- A user account with at least one space containing an **indexed, published document whose content includes Markdown formatting** (headings, `**bold**`, a list, `` `inline code` ``). Create one via Spaces → Add Document if needed, and ensure it is indexed (search for a word in it and confirm a result).

## Automated validation (primary)

```bash
cd apps/web
npx vitest run tests/search.test.tsx
```

Expected: all cases pass, including the new ones — title rendered above the
excerpt, `Untitled document` fallback, formatted snippet (a `**bold**` snippet
produces `<strong>` and no literal `**` text), embedded `<script>`/HTML never
mounted as elements, score still shown, card click and Enter key navigate to
`/documents/{document_id}`, excerpt links do not hijack navigation.

Full web suite (regression check for `MarkdownContent` callers — document page
and chat):

```bash
cd apps/web
npx vitest run
```

## Manual validation (end-to-end)

```bash
cd apps/web && npm run dev   # with the backend stack up
```

1. **Formatted snippet + title (US1 / FR-001, FR-002, FR-005)**: Log in, open
   `/search`, keep the **Search** mode, and search a term matching the
   Markdown-rich document. Each result card shows the document title on top
   (bold, more prominent) and the excerpt below with rendered formatting — no
   raw `#`, `**`, or backticks visible as text; a heading inside the excerpt
   stays card-sized. Score percentage still visible (FR-009).
2. **Navigation (US2 / FR-006, FR-007)**: Hover a card → pointer cursor and
   hover feedback. Click anywhere on the card → browser goes to that
   document's detail page with full content. Press the browser **Back**
   button → you return to the search page.
3. **Safety (FR-003)**: In a document, include `<script>alert(1)</script>` and
   `<img src=x onerror="alert(1)">`, publish + index, then search for adjacent
   text. The result card shows the tags as inert text; no alert fires, and no
   `<script>`/`<img>` element appears in DevTools inside the card.
4. **Malformed Markdown (FR-004)**: Search a term whose match lands next to a
   code fence or list so the 300-char excerpt cuts mid-syntax. The card stays
   legible and contained; adjacent cards and page layout are unaffected.
5. **Fallback title (FR-008)**: For a result lacking a document title (or by
   temporarily mocking one in the component test), the card shows
   `Untitled document` and remains clickable.

## Expected outcome summary

- 100% of result excerpts render formatted, contained, and script-free
  (SC-001, SC-004).
- Every card shows a title or fallback above the excerpt (SC-002).
- Search → full document is a single click; Back returns to results (SC-003).
