# Implementation Plan: UI Compliance with Implemented Functionality

**Branch**: `003-fix-ui-compliance` | **Date**: 2026-06-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-fix-ui-compliance/spec.md`

## Summary

The Tessera backend exposes 8 functional domains via REST API, but the web UI covers only 3 of them (search, proposals, metrics — the last without a nav link). The home page still shows the default Next.js boilerplate. This plan adds a Home dashboard, a Documents browsing/detail section, and enhanced Admin forms for spaces, permissions, connectors, and agent credentials — all wired to the existing API. No backend changes are required.

## Technical Context

**Language/Version**: TypeScript 5, Node 20 (Next.js 14 App Router)

**Primary Dependencies**: Next.js 14, React 18, Tailwind CSS 3, Vitest, @testing-library/react

**Storage**: N/A — all data persisted on the backend; the UI is stateless

**Testing**: Vitest + @testing-library/react + jsdom (existing config at `apps/web/vitest.config.ts`)

**Target Platform**: Web browser, desktop viewport (≥1024px wide)

**Project Type**: Web application (Next.js frontend, App Router)

**Performance Goals**: Standard interactive web app — visual feedback within 300ms of user action; API-dependent renders show loading state within 100ms

**Constraints**:
- No new backend changes
- No new npm dependencies (unless strictly unavoidable)
- All API calls through existing `apps/web/lib/api.ts` helper
- No login page in scope (session auth handled by backend middleware)

**Scale/Scope**: 5 new/modified pages, ~8 new form components, 1 nav change, ~3 new test files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| **I. Domain-Driven Architecture** | ✅ Pass | UI is a presentation layer only. Domain logic stays in `packages/core`. No business logic in frontend. |
| **II. Separation of Concerns** | ✅ Pass | The UI depends on API contracts, not on domain entities directly. All tech-specific code stays in the API layer. |
| **III. Data Locality & Consent** | ✅ Pass | No new client-side persistence. All state is ephemeral React state that clears on navigation. The raw agent credential token shown on creation is displayed in-memory only and never stored client-side. |
| **IV. TDD (NON-NEGOTIABLE)** | ✅ Pass | New pages and components get companion Vitest tests written alongside implementation. Test coverage ≥85% required for all new `app/` and `components/` files. |
| **V. Quality Gates** | ✅ Pass | TypeScript strict mode, Vitest passing — these are enforced by existing CI config. Ruff/Black apply only to Python; the frontend equivalent is TypeScript type checking (`tsc --noEmit`) and Vitest. |
| **Stack: PostgreSQL** | N/A | Frontend does not directly interact with storage. |
| **Stack: Infrastructure as Code** | ✅ Pass | No new containers or services introduced. |
| **Security: Auth (OAuth2/JWT)** | ✅ Pass | All new pages call `require_user` on the backend via the existing session mechanism. The UI itself does not implement auth. |
| **Security: Secret Management** | ✅ Pass | Agent credential tokens are shown once in-memory and never written to localStorage, sessionStorage, or any log. |
| **Security: Audit Logging** | ✅ Pass | All state-changing actions (publish, approve, reject, create, revoke) emit audit records on the backend. No new audit instrumentation needed in the UI. |
| **Documentation Separation** | ✅ Pass | This spec.md is product-only; this plan.md carries all technical decisions. |

**Post-Phase 1 re-check**: All principles remain satisfied. The implementation adds no new dependencies that would affect domain isolation, data locality, or security boundaries.

## Project Structure

### Documentation (this feature)

```text
specs/003-fix-ui-compliance/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── ui-routes.md     # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (web application)

```text
apps/web/
├── app/
│   ├── layout.tsx           # MODIFY: add "Metrics" nav link
│   ├── page.tsx             # REPLACE: home dashboard (replace boilerplate)
│   ├── search/
│   │   └── page.tsx         # unchanged
│   ├── proposals/
│   │   └── page.tsx         # unchanged
│   ├── documents/
│   │   ├── page.tsx         # NEW: document browser (space filter + list)
│   │   └── [id]/
│   │       └── page.tsx     # NEW: document detail + version history + publish
│   ├── admin/
│   │   └── page.tsx         # REPLACE: enhanced with forms for spaces,
│   │                        #          permissions, connectors, credentials
│   └── metrics/
│       └── page.tsx         # unchanged
├── lib/
│   └── api.ts               # unchanged
└── tests/
    ├── setup.ts             # unchanged
    ├── home.test.tsx         # NEW: home dashboard tests
    ├── documents.test.tsx    # NEW: document browser + detail tests
    └── admin.test.tsx        # NEW: enhanced admin form tests
```

**Structure Decision**: Single Next.js App Router project (`apps/web`). No new components directory for this feature; components are co-located with their pages or extracted into the app directory if used on more than one page. If a component (e.g., `SpaceSelector`) is used on both `/documents` and `/admin`, it goes in `apps/web/components/`.

## Implementation Design

### Home Dashboard (`/`)

Replace `apps/web/app/page.tsx` with a dashboard that:

1. Fetches `GET /v1/spaces` and `GET /v1/metrics` in parallel using `Promise.all`.
2. Displays three stat cards: Space Count, Total Queries, Documents with Drift.
3. Renders quick-nav links to `/search`, `/proposals`, `/metrics`, `/admin`.
4. Handles fetch errors by showing "–" in stat cards (no crash).

### Documents Browser (`/documents`)

New page `apps/web/app/documents/page.tsx`:

1. On mount: fetch `GET /v1/spaces` to populate space dropdown.
2. On space selection: fetch `GET /v1/documents?space_id={id}`.
3. Render a table: title, state badge (color: ingested=yellow, published=green, archived=gray), confidentiality.
4. Each row is a link to `/documents/{id}`.

### Document Detail (`/documents/[id]`)

New page `apps/web/app/documents/[id]/page.tsx` (client component):

1. On mount: fetch `GET /v1/documents/{id}` and `GET /v1/documents/{id}/versions` in parallel.
2. Render document metadata (title, state badge, confidentiality, tags).
3. Render current version content in a `<pre>` or prose block.
4. Render version history table (version number, approved_at, approver_user_id).
5. Show "Publish" button only when `state === "ingested"`:
   - `POST /v1/documents/{id}/publish` on click.
   - Disable during request; on success update local state (state → "published", hide button).
   - On error: show inline error message, re-enable button.

### Navigation Update (`layout.tsx`)

Add `<a href="/metrics">Metrics</a>` to the flex nav row, between "Proposals" and "Admin".

### Enhanced Admin Page (`/admin`)

Replace `apps/web/app/admin/page.tsx` with a multi-section page:

**Section 1 – Spaces** (same as before + form):
- Table: name, slug, sector.
- "Create Space" form: slug, name, sector, default_language.
- Client-side validation: slug and name required before POST.
- `POST /v1/spaces` → append to list, reset form, show inline success.

**Section 2 – Space Permissions**:
- Space selector (same `spaces` state from Section 1).
- Form: idp_group (text), role (select: viewer/editor/admin), max_confidentiality (select).
- `POST /v1/spaces/{id}/permissions` → show success/error inline.

**Section 3 – Connectors**:
- Space selector.
- On space select: fetch connectors (Note: no GET /v1/connectors endpoint exists — show only connectors created this session, or list them from the create response).
- Form: type (text), config (textarea, raw JSON), schedule (text, optional).
- `POST /v1/spaces/{id}/connectors` → add to local list, "Sync Now" button.
- "Sync Now": `POST /v1/connectors/{id}/sync` → display `{ job_id }` inline.

> **Note on Connectors listing**: The backend does not expose a `GET /v1/spaces/{id}/connectors` list endpoint. The UI will maintain a local session list of connectors created during the current admin session. Connectors created in previous sessions are not shown. This is acceptable for the current scope; adding a list endpoint is a backend task outside this feature.

**Section 4 – Agent Credentials**:
- Fetch existing credentials: no GET endpoint exists either — same pattern as connectors (session list).
- Form: name, scoped_space_ids (multi-select checkboxes from spaces list), max_confidentiality.
- `POST /v1/agent-credentials` → display raw token in highlighted alert box with copy button + warning "This token will not be shown again." Add credential to local list.
- "Revoke": `POST /v1/agent-credentials/{id}/revoke` → mark item in list as revoked.

### Testing Strategy

Each new page/component gets a companion test file following the existing setup:

**`tests/home.test.tsx`**:
- Mock `api.get` for `/v1/spaces` (returns 3 spaces) and `/v1/metrics` (returns stats).
- Assert: stat cards rendered with correct values.
- Mock failure: assert stat cards show "–".

**`tests/documents.test.tsx`**:
- Mock spaces list.
- Mock documents list for a selected space.
- Assert: selecting space triggers document fetch and renders list.
- Mock document detail + versions.
- Assert: detail page renders title, state badge, version count.
- Assert: "Publish" button present for ingested doc, absent for published doc.

**`tests/admin.test.tsx`**:
- Assert: "Create Space" form rejects empty slug.
- Mock `POST /v1/spaces` success → assert new row in table, form reset.
- Mock `POST /v1/agent-credentials` success → assert token display with copy button.

## Complexity Tracking

No constitution violations. No complexity justifications required.
