# Implementation Plan: Frontend Spaces Page

**Branch**: `040-frontend-spaces-page` | **Date**: 2026-06-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/040-frontend-spaces-page/spec.md`

## Summary

Build a `/spaces` listing page in the Next.js web app that displays all spaces accessible to the authenticated user within their active company, with role badges and navigation links to members and documents. Add a "Spaces" link to the NavBar. No backend changes required — `GET /v1/spaces` already returns company-scoped spaces; role per space is fetched in parallel via the existing `GET /v1/spaces/{id}/members/me` endpoint.

## Technical Context

**Language/Version**: TypeScript 5, React 19, Next.js 15 (App Router)

**Primary Dependencies**: Next.js 15, React 19, Tailwind CSS v4, Vitest 2 + @testing-library/react

**Storage**: N/A (read-only frontend feature consuming existing REST API)

**Testing**: Vitest + @testing-library/react (jsdom); existing test files in `apps/web/tests/`

**Target Platform**: Browser (desktop-first, responsive via existing Tailwind breakpoints)

**Project Type**: Web application (Next.js App Router, client components)

**Performance Goals**: Full page load and space list render under 2 seconds (SC-002); parallel role fetches reduce latency vs. sequential

**Constraints**: Alphabetical sort client-side; no pagination; spaces count per company expected to be small (< 50)

**Scale/Scope**: Single `/spaces` page + one reusable `SpaceCard` component + NavBar update

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. DDD | ✅ PASS | Frontend presentation layer only; no domain model changes |
| II. Separation of Concerns | ✅ PASS | UI consumes existing API contracts; no backend logic touched |
| III. Data Locality | ✅ PASS | No client-side persistence; token already in memory/session |
| IV. TDD | ✅ MUST — tests required | Frontend Vitest tests must be written for all new components and page; coverage target: 85% for new files |
| V. Quality Gates | ✅ PASS | TypeScript compilation + Ruff/Black N/A (no Python changes) |
| VI. Tenant Data Isolation | ✅ PASS — see below | |

### VI. Tenant Data Isolation (mandatory section)

**Tables accessed**: None directly — frontend reads from API.

**API endpoints consumed**:
- `GET /v1/spaces` — backend already enforces `company_id` scoping via JWT company context (implemented in spec 037). Returns only spaces belonging to the authenticated company.
- `GET /v1/spaces/{id}/members/me` — backend validates space belongs to authenticated company before returning membership; returns 404 for cross-company IDs.

**Company context propagation**: Established at the API layer by the backend (JWT token → company context). Frontend passes Bearer token on every request via `api.get()`. No re-derivation from user-supplied input on the frontend.

**Cross-tenant isolation tests**: Frontend tests must assert that only data returned by the (mocked) API is rendered — no frontend logic can bypass the scoping. The backend's cross-tenant isolation tests already cover the API layer (test_space_visibility.py, test_tenant_isolation.py).

**Cross-tenant access exceptions**: None. This is a pure read operation scoped to the active company.

## Project Structure

### Documentation (this feature)

```text
specs/040-frontend-spaces-page/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code

```text
apps/web/
├── app/
│   └── spaces/
│       ├── page.tsx             # NEW — spaces listing page (/spaces route)
│       └── [id]/
│           └── members/
│               └── page.tsx     # EXISTING — no changes
├── components/
│   └── spaces/
│       └── SpaceCard.tsx        # NEW — single space card component
├── components/
│   └── NavBar.tsx               # MODIFIED — add "Spaces" link + active state
└── tests/
    ├── spaces.test.tsx          # NEW — tests for spaces listing page
    ├── space-card.test.tsx      # NEW — tests for SpaceCard component
    └── navbar.test.tsx          # MODIFIED — add Spaces link assertions
```

**Structure Decision**: Web application layout. New files follow the existing `app/<route>/page.tsx` + `components/<domain>/Component.tsx` pattern already used for documents, members, etc.

## Complexity Tracking

No constitution violations — no justification table required.
