# Implementation Plan: Formatted Search Results with Document Navigation

**Branch**: `064-format-search-results` | **Date**: 2026-07-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/064-format-search-results/spec.md`

## Summary

Rework the search-mode result cards on the search page so each card shows the
document title prominently on top and, below it, the matching excerpt rendered
as formatted Markdown (via the existing `MarkdownContent` component) instead of
raw source; make the whole card a click target that navigates to the existing
document detail page (`/documents/{document_id}`). Frontend-only: the existing
`POST /v1/search` response already carries everything needed
(`document_id`, `snippet`, `score`, `citation.document_title`). Technical
decisions in [research.md](./research.md).

## Technical Context

**Language/Version**: TypeScript 5 / React 19.1 / Next.js 15.5 (App Router, client components)

**Primary Dependencies**: `react-markdown` ^9 + `remark-gfm` ^4 (already installed, wrapped by `components/markdown/MarkdownContent.tsx`); Tailwind CSS 4 + `@tailwindcss/typography` ^0.5 (`prose` classes); `next/navigation` router

**Storage**: N/A (no persistence changes; consumes existing `POST /v1/search` API)

**Testing**: Vitest 2 + @testing-library/react 16 + jsdom (existing suite at `apps/web/tests/`, extending `search.test.tsx`)

**Target Platform**: Modern browsers via Next.js web app (`apps/web`)

**Project Type**: Web application (frontend change only within the existing monorepo)

**Performance Goals**: Rendering ≤10 Markdown snippets (≤300 chars each) per search adds no perceptible latency; no extra network requests per result

**Constraints**: Excerpt rendering must be XSS-safe (no raw HTML execution), contained within the card for malformed/truncated Markdown, and visually compact (headings must not render at page scale)

**Scale/Scope**: One page (`app/search/page.tsx`), one shared component extension (`MarkdownContent` optional `components` prop), one test file; search returns `top_k` = 10 results by default

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | ✅ Pass | Presentational frontend change; no domain logic touched, no new domain↔infrastructure coupling. |
| II. Separation of Concerns | ✅ Pass | Spec stays technology-agnostic; all technical choices live in this plan and research.md. |
| III. Data Locality & Consent | ✅ Pass | No client-side persistence introduced (no localStorage/cookies added). |
| IV. Test-Driven Development | ✅ Pass | Component tests written first in `apps/web/tests/search.test.tsx` (failing → implement → green). No Python modules change, so the 85% Python statement-coverage gate is unaffected. |
| V. Quality Gates | ✅ Pass | No Python files touched (Ruff/Black not triggered); web code follows existing lint/TS config. |
| VI. Tenant Data Isolation | ✅ Pass | **No new data-access path.** See Tenant Isolation section below. |

### Tenant Isolation

- **Tables accessed**: none newly. The feature consumes the existing
  `POST /v1/search` endpoint, which scopes results to the authenticated
  company (`SqlSpaceRepository.list_by_company(company_id)` builds the allowed
  space set before `acl_first_search`; verified in
  `apps/api/tessera_api/routers/search.py`). Navigation targets the existing
  `GET /v1/documents/{id}` page, which enforces its own tenant-scoped access
  and renders "not found / no access" for stale or foreign IDs.
- **`company_id` scoping**: unchanged and already present on every query in
  both consumed endpoints; this feature adds zero queries and zero mutations.
- **Cross-tenant isolation tests**: none new required (no new data path).
  Existing coverage: search router tenant tests
  (`apps/api/tests/unit/test_search_router.py`, `apps/api/tests/contract/test_search.py`)
  and document access tests remain the enforcement points. The frontend test
  will assert that navigating to an inaccessible document surfaces the
  document page's existing error handling (mocked), not data.

**Gate result (pre-Phase 0)**: PASS — no violations, Complexity Tracking not needed.

**Gate re-check (post-Phase 1 design)**: PASS — design artifacts introduce no
new endpoints, tables, or client persistence; `MarkdownContent` extension is a
prop addition on an existing shared component.

## Project Structure

### Documentation (this feature)

```text
specs/064-format-search-results/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── search-result-card.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/web/
├── app/
│   ├── search/
│   │   └── page.tsx                      # MODIFIED: result card layout (title on top,
│   │                                     #   rendered snippet, clickable card → router.push)
│   └── documents/[id]/page.tsx           # UNCHANGED: existing navigation target
├── components/
│   └── markdown/
│       └── MarkdownContent.tsx           # MODIFIED: optional `components` prop so callers
│                                         #   can override element rendering (headings, links)
└── tests/
    └── search.test.tsx                   # MODIFIED: new test cases (written first)

apps/api/                                 # UNCHANGED: POST /v1/search already returns
                                          #   document_id, snippet, score, citation
```

**Structure Decision**: Web-application layout already established in the
monorepo (`apps/web` Next.js frontend, `apps/api` FastAPI backend). This
feature touches only `apps/web`: the search page, the shared Markdown
component, and its test file. No backend, worker, or schema changes.

## Design Overview (how the pieces fit)

1. **Result card** (`app/search/page.tsx`): for each `SearchResult`, render a
   card with:
   - Header row: document title (`citation.document_title` or
     `"Untitled document"`) as the prominent element (`text-sm font-semibold
     text-slate-900`), score badge kept on the right (FR-009).
   - Body: `<MarkdownContent content={r.snippet} className="prose prose-sm
     max-w-none ..." components={snippetOverrides} />` — headings downscaled to
     card-appropriate size, links rendered as inert styled text (research R2/R3).
   - Card behavior: `role="link"`, `tabIndex=0`, `cursor-pointer`, hover
     feedback per design system (slate surfaces, indigo accent), `onClick` and
     Enter/Space → `router.push(\`/documents/${r.document_id}\`)`.
   - Containment: `overflow-hidden break-words` on the card body so malformed
     or truncated Markdown cannot break the results-list layout (FR-004).
2. **`MarkdownContent` extension**: add optional `components?: Components`
   prop merged with the existing `openLinksInNewTab` override (caller-provided
   entries win). Existing call sites (document page, chat) are unaffected.
3. **Safety**: no `rehype-raw`; react-markdown escapes embedded HTML by
   default, satisfying FR-003 without a sanitizer.

## Complexity Tracking

> No constitutional violations — table intentionally left empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
