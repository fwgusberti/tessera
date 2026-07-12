# Feature Specification: Formatted Search Results with Document Navigation

**Feature Branch**: `064-format-search-results`

**Created**: 2026-07-11

**Status**: Draft

**Input**: User description: "na pagina search nos resultados de pesquisa mostre o trecho do documento como .md formatado mostrando o título do documento e abaixo o trecho. Hoje mostra como .md crú. Além disso faça com que eu possa clicar em um documento e navegar até ele"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Readable, Formatted Search Result Snippets (Priority: P1)

As a user searching the documentation, when I run a search I want each result to show the document's title prominently at the top and, below it, the matching excerpt rendered as formatted rich text (headings, bold, lists, inline code, links) instead of raw Markdown source, so I can quickly scan results and judge relevance.

**Why this priority**: Today snippets show raw Markdown syntax (`#`, `**`, `` ` ``, etc.), which makes results hard to read and the title appears as a small footnote below the snippet. This is the core readability problem the user reported and affects every search performed.

**Independent Test**: Can be fully tested by searching for a term that matches a document containing Markdown formatting and verifying the result card shows the document title on top and a formatted (not raw) excerpt below it.

**Acceptance Scenarios**:

1. **Given** a document whose content contains Markdown formatting (bold, lists, inline code), **When** the user searches for a term matching that document, **Then** each result card displays the document title at the top and the excerpt below it with the formatting visually rendered (no raw Markdown syntax characters visible as plain text).
2. **Given** search results are displayed, **When** the user views a result card, **Then** the document title appears above the excerpt, visually more prominent than the excerpt text.
3. **Given** a result whose excerpt contains Markdown structures cut off mid-syntax (e.g., a truncated code block or list), **When** the result renders, **Then** the excerpt still displays legibly without breaking the layout of the page or of other results.

---

### User Story 2 - Navigate to a Document from a Search Result (Priority: P2)

As a user reviewing search results, I want to click a result and be taken to that document's page, so I can read the full content in context instead of only the excerpt.

**Why this priority**: Finding a result is only useful if the user can act on it. Today results are inert cards, forcing users to remember the title and locate the document manually. This closes the search-to-read loop, but the readability fix (P1) delivers value even on its own.

**Independent Test**: Can be fully tested by clicking any search result and verifying the browser navigates to the corresponding document's detail page.

**Acceptance Scenarios**:

1. **Given** search results are displayed, **When** the user clicks a result, **Then** the application navigates to that document's detail page showing its full content.
2. **Given** search results are displayed, **When** the user hovers over a result, **Then** the result gives a visual affordance that it is clickable (e.g., pointer cursor and hover feedback).
3. **Given** the user navigated to a document from search results, **When** they use the browser's back action, **Then** they return to the search page.

---

### Edge Cases

- Result has no document title available: the result must still render with a sensible fallback label (e.g., "Untitled document") and remain clickable.
- Excerpt contains heading markers (`#`, `##`): rendered headings must not dominate the result card visually (an excerpt heading should not render as a huge page-level title).
- Excerpt contains truncated/unbalanced Markdown (unclosed code fence, cut-off emphasis): rendering must degrade gracefully without breaking the card or leaking formatting into adjacent results.
- Excerpt contains raw HTML or script-like content: it must never execute; content must be rendered safely.
- Excerpt contains links: clicking a link inside the excerpt must not conflict confusingly with the card's navigation behavior (card navigation must remain predictable).
- The referenced document was deleted or the user lost access after indexing: navigation lands on the document page's existing "not found / no access" handling rather than a broken state.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each search result MUST display the document title at the top of the result card, visually more prominent than the excerpt.
- **FR-002**: Each search result MUST render its excerpt as formatted rich text (interpreting Markdown: emphasis, inline code, lists, links, headings) instead of showing raw Markdown source.
- **FR-003**: Excerpt rendering MUST be safe: embedded HTML or script content in document text must never execute in the user's browser.
- **FR-004**: Excerpt rendering MUST degrade gracefully for truncated or malformed Markdown, keeping the result card and page layout intact.
- **FR-005**: Rendered excerpt formatting MUST be visually scaled to fit a compact result card (e.g., headings inside excerpts must not render at page-title size).
- **FR-006**: Users MUST be able to click a search result to navigate to the corresponding document's detail page.
- **FR-007**: Results MUST present a clear clickable affordance (pointer cursor and hover state).
- **FR-008**: When a result has no document title, the system MUST display a fallback label and the result MUST remain clickable.
- **FR-009**: The existing relevance indicator (score) MUST remain visible on each result.

### Key Entities

- **Search Result**: A match returned for a query; carries a reference to the source document, the matching excerpt (Markdown text), a relevance score, and citation metadata including the document title.
- **Document**: The full content the excerpt was taken from; has a detail page that is the navigation target of a result click.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For documents containing formatting, 100% of search result excerpts display rendered formatting with no raw Markdown syntax characters shown as plain text.
- **SC-002**: Every search result displays a document title (or fallback label) above its excerpt.
- **SC-003**: Users can go from a displayed search result to the full document in a single click.
- **SC-004**: No search result — including ones with malformed or truncated excerpts — breaks the layout of the results list or executes embedded content.

## Assumptions

- The scope is the "Search" mode results on the search page; the "Ask Assistant" answer and its citation list are out of scope for this feature (citations may be addressed separately).
- The entire result card is the click target for navigation (rather than only the title), since the card is the natural unit users will try to click; links inside the rendered excerpt, if present, are subordinate to card navigation.
- Search results already carry enough information to identify the target document, and a document detail page already exists as the navigation destination.
- Excerpts are fragments of larger documents, so imperfect formatting at the fragment boundaries (e.g., a list starting mid-way) is acceptable as long as rendering is legible and contained.
- Access control is unchanged: search already returns only documents the user may see, and the document page's existing error handling covers stale results.
