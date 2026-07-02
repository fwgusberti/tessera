# Implementation Plan: Modernize Document Page

**Branch**: `045-modernize-document-page` | **Date**: 2026-07-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/045-modernize-document-page/spec.md`

## Summary

Redesign the document detail page (`apps/web/app/documents/[id]/page.tsx`) from its
current dated layout (raw `<pre>`-rendered markdown source, bare HTML table for
version history, ad-hoc inline styling) into a page that is visually and
structurally consistent with the recently modernized Spaces folder browser
(feature 044): a full breadcrumb trail showing the document's location in the
space hierarchy, the current version's markdown rendered as formatted rich text,
a restyled action bar for Publish/Reindex, and a modern scannable version history
list. This is entirely a frontend presentation change — every data operation it
needs (`GET /v1/documents/{id}`, `GET /v1/documents/{id}/versions`,
`POST /v1/documents/{id}/publish`, `POST /v1/documents/{id}/reindex`,
`GET /v1/spaces/{space_id}`, `GET /v1/spaces/{space_id}/ancestors`) already
exists and is already tenant-scoped and authorization-checked server-side; no
backend or database change is required.

## Technical Context

**Language/Version**: TypeScript 5, React 19, Next.js 15.5 (App Router) — frontend only; no change to the Python 3.12 API

**Primary Dependencies**: `react-markdown` + `remark-gfm` (new — renders `content_markdown` as React elements, no raw-HTML passthrough so no new XSS surface), `@tailwindcss/typography` (new, dev-only — provides `prose` article styling for rendered markdown, registered via Tailwind v4's CSS-first `@plugin` directive), Tailwind CSS 4

**Storage**: N/A for this feature — reuses existing PostgreSQL-backed endpoints unchanged; no schema change

**Testing**: Vitest + `@testing-library/react` (`apps/web/tests/`, existing pattern e.g. `documents.test.tsx`, `documents-reindex-admin.test.tsx`)

**Target Platform**: Web browser (existing Next.js app, `apps/web`)

**Project Type**: Web application — frontend-only change (existing `apps/web`; zero `apps/api` or `db/migrations` changes)

**Performance Goals**: No new performance target — markdown rendering happens client-side over the same already-fetched `content_markdown` payload as today; no additional document data is fetched, only two small existing space-lookup calls for the breadcrumb

**Constraints**: MUST NOT change publish/reindex eligibility rules, request/response contracts, or success/error semantics (FR-003 — restyle only); MUST render document content without enabling raw HTML passthrough (no `rehype-raw`), so user-authored markdown cannot inject arbitrary HTML/scripts; MUST reuse existing `GET /v1/spaces/{space_id}/ancestors` and `GET /v1/spaces/{space_id}` endpoints for the breadcrumb rather than introducing new backend endpoints

**Scale/Scope**: One modified route (`app/documents/[id]/page.tsx`), 2 new presentational components (`DocumentContent`, `VersionHistory`), reuse of the existing `SpaceBreadcrumb` component unmodified, 2 new runtime dependencies + 1 new dev dependency, zero new backend endpoints, zero new tables/columns

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Domain-Driven Architecture**: No domain logic is added or changed — this feature only changes how already-fetched document/version/space data is rendered. ✅ PASS (N/A)
- **II. Separation of Concerns**: `spec.md` describes the user-facing modernization with no implementation references; this plan carries the technical decisions (markdown rendering library, breadcrumb composition, styling plugin). ✅ PASS
- **III. Data Locality & Consent**: No new client-side persistence is introduced; no state is stored beyond the existing in-memory component state. ✅ PASS (N/A)
- **IV. Test-Driven Development**: Vitest tests for markdown-to-formatted-output rendering, breadcrumb trail composition (ancestors + own space + document title), version history list (populated, empty, unpaginated-with-many-versions), and action-button restyle parity (publish/reindex eligibility and feedback unchanged) MUST be written before their corresponding component/page changes, mirroring `documents-reindex-admin.test.tsx`. ✅ PASS (enforced in Tasks)
- **V. Quality Gates**: No Python files are touched by this feature, so the Ruff/Black gate does not apply; existing TypeScript/ESLint conventions in `apps/web` are followed. ✅ PASS (N/A)
- **VI. Tenant Data Isolation (NON-NEGOTIABLE)** — **Tenant Isolation section**:
  - Tables accessed: none newly accessed. This feature exclusively consumes existing endpoints — `GET /v1/documents/{id}`, `GET /v1/documents/{id}/versions`, `POST /v1/documents/{id}/publish`, `POST /v1/documents/{id}/reindex`, `GET /v1/spaces/{space_id}`, `GET /v1/spaces/{space_id}/ancestors` — all of which already enforce `company_id` scoping server-side via `CompanyContext` and `list_accessible_by_user(user_id, company_id)` / `get_by_id_for_company(space_id, company_id)`.
  - No new query or mutation is introduced by this feature; the two additional calls used for the breadcrumb (`GET /v1/spaces/{space_id}` and `GET /v1/spaces/{space_id}/ancestors`) are the same endpoints feature 044 already uses, unchanged.
  - Cross-tenant access: none introduced.
  - Isolation tests to add: none required at the API/service layer (no new server-side code path). A frontend test MUST assert that if the space lookup/ancestors call fails (e.g., 403/404 — a defensive case, since document access already implies space access), the page degrades to showing the document without a breadcrumb rather than crashing, so a lookup failure is never silently misrendered as an incorrect location.

No violations requiring justification — Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/045-modernize-document-page/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── reused-endpoints.md   # Phase 1 output — documents existing endpoints this feature reuses (no new endpoints)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/web/
├── app/
│   ├── documents/
│   │   └── [id]/
│   │       └── page.tsx                # modified: modernized layout — breadcrumb, formatted content, restyled actions, restyled version history
│   └── globals.css                     # modified: register @tailwindcss/typography via @plugin directive; override prose link/code colors to indigo-600/700 per constitution
├── components/
│   └── documents/
│       ├── AddDocumentModal.tsx        # unchanged
│       ├── DocumentContent.tsx         # new: renders current version's markdown as formatted rich text (react-markdown + remark-gfm + prose styling); empty state
│       └── VersionHistory.tsx          # new: modern scannable, unpaginated list of versions (number, approved-at, approver); empty state
├── lib/
│   └── types.ts                        # unchanged (Ancestor, Document, DocumentVersion already defined)
└── tests/
    ├── documents.test.tsx              # unchanged
    ├── documents-reindex-admin.test.tsx # extended: mock new GET /v1/spaces/{id} and /v1/spaces/{id}/ancestors calls
    └── document-detail-modernized.test.tsx  # new: markdown rendering, breadcrumb composition, version history states, action-parity checks
```

**Structure Decision**: Frontend-only change confined to `apps/web`. No new
project, package, or backend endpoint — `apps/api` and `db/migrations` are
untouched. Reuses `GET /v1/documents/{id}`, `GET /v1/documents/{id}/versions`,
`POST /v1/documents/{id}/publish`, `POST /v1/documents/{id}/reindex`,
`GET /v1/spaces/{space_id}`, and `GET /v1/spaces/{space_id}/ancestors` exactly
as they exist today (see `contracts/reused-endpoints.md`). The breadcrumb reuses
the existing `SpaceBreadcrumb` component unmodified — the ancestor chain plus the
document's own space are passed as its `ancestors` prop, with the document title
as `currentName`, so no new breadcrumb component or drag-and-drop coupling is
introduced.

## Complexity Tracking

*No Constitution Check violations — this section is not applicable.*
