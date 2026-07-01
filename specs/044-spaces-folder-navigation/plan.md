# Implementation Plan: Spaces as Drive-Style Folders (UI)

**Branch**: `044-spaces-folder-navigation` | **Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/044-spaces-folder-navigation/spec.md`

## Summary

Redesign the Spaces page (`apps/web`) from a flat, fully-expanded, indented
tree into a Google Drive-style folder browser: a top-level grid of folder
tiles, drill-down navigation into a folder's direct sub-folders and its
directly-assigned documents shown together, a clickable breadcrumb trail, and
drag-and-drop reparenting (with the existing explicit "Set parent" action
kept as a non-drag fallback). This is entirely a frontend presentation and
navigation change — every data operation it needs (`GET /v1/spaces`,
`GET /v1/documents?space_id=`, `GET /v1/spaces/{id}/ancestors`, `PATCH`/
`DELETE /v1/spaces/{id}/parent`) already exists and is already tenant-scoped
and authorization-checked server-side from features 040/041/043; no backend
or database change is required.

## Technical Context

**Language/Version**: TypeScript 5, React 19, Next.js 15.5 (App Router) — frontend only; no change to the Python 3.12 API

**Primary Dependencies**: Next.js App Router (file-based dynamic routes), native HTML5 Drag and Drop API (no new package — see `research.md` §1), Tailwind CSS 4

**Storage**: N/A for this feature — reuses existing PostgreSQL-backed endpoints unchanged; no schema change

**Testing**: Vitest + `@testing-library/react` (`apps/web/tests/`, existing pattern e.g. `spaces.test.tsx`, `space-card.test.tsx`)

**Target Platform**: Web browser (existing Next.js app, `apps/web`)

**Project Type**: Web application — frontend-only change (existing `apps/web`; zero `apps/api` or `db/migrations` changes)

**Performance Goals**: No new performance target — `GET /v1/spaces` already returns the full accessible set unpaginated at current scale; client-side filtering into top-level/children is O(n) over that same already-fetched list

**Constraints**: MUST NOT bypass or reimplement the server-side reparent checks (self-parent, cross-company, admin-in-both-spaces, cycle, depth ≤ 10) already enforced in `SpaceHierarchyService.set_parent` — drag-and-drop MUST call the existing `PATCH`/`DELETE /v1/spaces/{id}/parent` endpoints, not introduce new ones; MUST keep a non-drag reparenting path available (FR-014)

**Scale/Scope**: One new dynamic route (`app/spaces/[id]/page.tsx`), 2-3 new components (folder/document tile rendering + drag-and-drop), extension of `SpaceBreadcrumb` to act as a drop target, retirement of `SpaceHierarchyView`'s full-tree-flattening role on this page; zero new backend endpoints, zero new tables/columns

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Domain-Driven Architecture**: No domain logic is added or changed — this feature only changes how already-fetched data is rendered and navigated in the frontend. ✅ PASS (N/A)
- **II. Separation of Concerns**: `spec.md` describes the user-facing folder-browsing behavior with no implementation references; this plan carries the technical decisions (routing, drag-and-drop mechanism, data reuse). ✅ PASS
- **III. Data Locality & Consent**: No new client-side persistence is introduced; navigation state lives in the URL route (`/spaces/[id]`), not in local storage or any persisted client store. ✅ PASS (N/A)
- **IV. Test-Driven Development**: Vitest tests for the top-level grid, drill-down/mixed-contents rendering, breadcrumb navigation (including deep-link), and each drag-and-drop path (success, self/descendant rejection, permission rejection, non-drag fallback) MUST be written before their corresponding component/handler, mirroring the existing `spaces.test.tsx` / `space-card.test.tsx` pattern. ✅ PASS (enforced in Tasks)
- **V. Quality Gates**: No Python files are touched by this feature, so the Ruff/Black gate does not apply; existing TypeScript/ESLint conventions already used in `apps/web` are followed. ✅ PASS (N/A)
- **VI. Tenant Data Isolation (NON-NEGOTIABLE)** — **Tenant Isolation section**:
  - Tables accessed: none newly accessed. This feature exclusively consumes existing endpoints — `GET /v1/spaces`, `GET /v1/documents?space_id=`, `GET /v1/spaces/{id}/ancestors`, `PATCH /v1/spaces/{id}/parent`, `DELETE /v1/spaces/{id}/parent` — all of which already enforce `company_id` scoping server-side via `CompanyContext`, `list_accessible_by_user(user_id, company_id)`, and `get_by_id_for_company(space_id, company_id)`.
  - No new query or mutation is introduced by this feature; it only changes how already-scoped data already returned to the client is rendered and how existing, already-scoped mutations are triggered (via drag-and-drop instead of only a modal).
  - Drag-and-drop reparenting calls the exact same `PATCH`/`DELETE /v1/spaces/{id}/parent` endpoints already used by `SetParentModal`, which already enforce admin-role-in-both-spaces, same-company target (`cross_company` rejection on cross-tenant attempts), cycle rejection, and depth limit in `SpaceHierarchyService.set_parent` — the UI has no direct data access and cannot bypass these checks.
  - Cross-tenant access: none introduced.
  - Isolation tests to add: none required at the API/service layer (no new server-side code path is introduced by this feature). Frontend tests will assert that a `cross_company` / `403 forbidden` response from the existing endpoint is surfaced to the user as an error (not silently ignored or treated as success), so tenant-isolation enforcement remains visibly correct through the new UI.

No violations requiring justification — Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/044-spaces-folder-navigation/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── reused-endpoints.md   # Phase 1 output — documents existing endpoints this feature reuses (no new endpoints)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/web/
├── app/
│   └── spaces/
│       ├── page.tsx                    # existing: becomes the top-level (root) folder grid entry point
│       └── [id]/
│           ├── page.tsx                # new: folder-contents view for a specific space (drill-down target, FR-009 deep link)
│           └── members/page.tsx        # existing: unchanged
├── components/
│   └── spaces/
│       ├── FolderGrid.tsx              # new: renders the mixed grid of FolderTile + DocumentTile for a folder's contents
│       ├── FolderTile.tsx              # new: draggable/droppable folder card (replaces indented SpaceCard rendering on this page)
│       ├── DocumentTile.tsx            # new: document card within an opened folder
│       ├── SpaceBreadcrumb.tsx         # extended: adds a "Root" crumb, each crumb becomes a drop target
│       ├── SpaceHierarchyView.tsx      # retired from the Spaces page (full-tree flattening no longer used here)
│       └── SetParentModal.tsx          # unchanged: kept as the non-drag fallback (FR-014)
├── lib/
│   ├── types.ts                       # extended: promote the Ancestor interface out of SpaceBreadcrumb.tsx
│   └── spaces.ts                       # new: shared client-side helpers (topLevelSpaces, directChildren of a FolderContents view — see data-model.md)
└── tests/
    ├── spaces.test.tsx                 # extended: top-level grid rendering, empty state
    ├── space-folder-view.test.tsx      # new: drill-down, mixed contents, breadcrumb navigation, deep link
    └── space-drag-drop.test.tsx        # new: reparent success, self/descendant rejection, permission rejection, non-drag fallback
```

**Structure Decision**: Frontend-only change confined to `apps/web`. No new
project, package, or backend endpoint — `apps/api` and `db/migrations` are
untouched. Reuses `GET /v1/spaces`, `GET /v1/documents?space_id=`,
`GET /v1/spaces/{id}/ancestors`, and `PATCH`/`DELETE /v1/spaces/{id}/parent`
from features 040/041/043 exactly as they exist today (see
`contracts/reused-endpoints.md`).

## Complexity Tracking

*No Constitution Check violations — this section is not applicable.*
