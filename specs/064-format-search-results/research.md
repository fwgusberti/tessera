# Research: Formatted Search Results with Document Navigation

**Feature**: `064-format-search-results` | **Date**: 2026-07-11

No NEEDS CLARIFICATION items remained after codebase inspection — the feature is a
frontend-only change consuming an existing API. The decisions below resolve the
open design questions.

## R1. Markdown rendering approach for snippets

**Decision**: Reuse the existing `MarkdownContent` component
(`apps/web/components/markdown/MarkdownContent.tsx`), which wraps
`react-markdown` v9 + `remark-gfm` v4, passing snippet-specific `components`
overrides (see R2/R3) rather than introducing a new renderer.

**Rationale**:
- `react-markdown` is already a dependency and already renders document pages
  (`DocumentContent.tsx`) and chat messages (`MessageBubble.tsx`), so search
  snippets will match the formatting users see elsewhere (feature 063's inline
  code pill styling in `globals.css` applies automatically via `.prose`).
- `react-markdown` is safe by default: without `rehype-raw`, embedded HTML in
  the source is rendered as escaped text, never executed, and it does not use
  `dangerouslySetInnerHTML` (satisfies FR-003 with zero extra work).
- remark's parser never throws on malformed input — truncated fences/emphasis
  degrade to literal text or an open code block confined to the card (FR-004).

**Alternatives considered**:
- `marked` / `markdown-it` + `dangerouslySetInnerHTML`: rejected — requires a
  sanitizer (DOMPurify) to be safe, adds a dependency, and duplicates an
  existing capability.
- Regex-stripping Markdown syntax to plain text: rejected — spec explicitly
  requires *rendered* formatting (FR-002), not syntax removal.

## R2. Scaling formatting to a compact result card (FR-005)

**Decision**: Wrap the snippet in `prose prose-sm max-w-none` (the
`@tailwindcss/typography` plugin is already loaded) and pass `components`
overrides to `MarkdownContent` that downscale headings: `h1`–`h6` inside a
snippet render as a single compact style (`text-sm font-semibold`, tight
margins) instead of page-scale headings. Extend `MarkdownContent` with an
optional `components` prop (merged over its own link override) so call sites
can customize element rendering without forking the component.

**Rationale**: `prose-sm` handles body text, lists, and inline code at card
scale, but an `h1` in an excerpt would still render ~2× body size and dominate
the card (explicit edge case in the spec). A components override is the
idiomatic react-markdown mechanism and keeps the CSS blast radius zero — no
new global rules in `globals.css`.

**Alternatives considered**:
- Global `.snippet-prose h1 {...}` rules in `globals.css`: workable but adds
  global CSS for a single call site; component-level override is more local
  and testable.
- Rendering the raw text of headings only: loses formatting fidelity for the
  common case where the excerpt is mostly non-heading content.

## R3. Card click target vs. links inside the excerpt

**Decision**: The entire result card becomes the click target (per spec
assumption), implemented as a card-level navigation handler that calls
`router.push(\`/documents/${result.document_id}\`)`, with
`cursor-pointer` + hover feedback (`hover:border-indigo-500 hover:bg-slate-50`
style affordance) and keyboard accessibility (`role="link"`, `tabIndex=0`,
Enter/Space triggers navigation). Links inside the rendered excerpt are
rendered as **non-navigating styled text** (an `a`→`span` components override
keeping the link color) so a click anywhere in the card always does exactly
one thing: open the document.

**Rationale**:
- Wrapping the card in `next/link` would nest `<a>` inside `<a>` whenever the
  excerpt contains a link — invalid HTML with unpredictable browser behavior,
  which is precisely the confusion the spec's edge case forbids.
- Excerpts are 300-char fragments; a link inside one is frequently truncated
  or context-free, so navigating to it from a search card has low value and
  high misclick cost. Rendering it as inert styled text keeps the visual
  formatting (FR-002) while making card behavior fully predictable.
- `router.push` (already used across the app, e.g. document page) preserves
  browser history, so Back returns to the search page (US2 scenario 3).

**Alternatives considered**:
- Live excerpt links with `stopPropagation`: rejected — splits the card into
  zones with different behaviors, violating "card navigation must remain
  predictable"; also risky with truncated URLs.
- Title-only link: rejected — spec assumption states the whole card is the
  natural click unit.

## R4. Data available to the result card

**Decision**: No backend change. Use the existing `POST /v1/search` response
as-is: `document_id` (navigation target), `snippet` (raw Markdown fragment,
first 300 chars of the chunk), `score` (keep visible, FR-009), and
`citation.document_title` (title, with `"Untitled document"` fallback when
absent — FR-008).

**Rationale**: Verified in `apps/api/tessera_api/routers/search.py`: every
result already carries `document_id` and `citation` built by
`build_citation`. The document detail page (`apps/web/app/documents/[id]/page.tsx`)
already exists, fetches `/v1/documents/{id}`, and has error handling for
missing/inaccessible documents — covering the stale-result edge case with no
new work.

**Alternatives considered**: Adding a dedicated `title` field to the search
response: unnecessary — `citation.document_title` already carries it; a
backend change would expand scope and require API contract + test updates for
zero user-visible gain.

**Implementation correction (2026-07-12)**: end-to-end validation against the
live API showed `build_citation` did **not** include `document_title` — the
original claim above was wrong. A minimal backend fix was applied test-first:
`SqlChunkRepository.search` now selects `d.title AS document_title` (the
`documents` join already existed) and `build_citation` passes it through as
`citation.document_title` (nullable). The frontend contract is unchanged —
the field was already typed optional.

## R5. Testing approach

**Decision**: Test-first component tests in the existing
`apps/web/tests/search.test.tsx` (Vitest + Testing Library + jsdom), following
the established mock pattern (`vi.mock("@/lib/api")`, mocked `AuthGuard`).
Add a `next/navigation` router mock (pattern already used in other web tests)
to assert navigation. Cover: title above excerpt, fallback title, rendered
formatting (e.g. `**bold**` produces a `<strong>`, no literal `**` visible),
escaped HTML never mounted as elements, score still visible, card click
navigates to `/documents/{id}`, Enter key navigates, excerpt link click does
not navigate elsewhere.

**Rationale**: Constitution IV requires test-first development; the web suite
is the established home for page behavior tests (`search.test.tsx` already
exists for this page). No Python module changes, so the 85% Python coverage
gate is untouched.
