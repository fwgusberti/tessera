# Implementation Plan: Add Document Button in Space

**Branch**: `061-add-document-button` | **Date**: 2026-07-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/061-add-document-button/spec.md`

## Summary

Add an "Add Document" button to the space folder page (`apps/web/app/spaces/[id]/page.tsx`), visible only to users whose effective role in that space is `editor` or `admin`. Clicking it opens the existing `AddDocumentModal` with the current space preselected as the destination. On success, the new document is inserted into the page's in-memory `documents` state so it appears in the grid (replacing the empty state if needed) without a reload.

This is a **frontend-only** feature. The API already provides everything needed: `POST /v1/documents` enforces company scoping and editor/admin role server-side, and `GET /v1/spaces` already returns `effective_role` per space, which the folder page already loads. The only component change outside the page is a new optional `initialSpaceId` prop on `AddDocumentModal`.

## Technical Context

**Language/Version**: TypeScript 5 (frontend, the only layer changed); Python 3.11+ backend untouched

**Primary Dependencies**: Next.js 15 (App Router, client components), React 19, Tailwind CSS 4; existing `@/lib/api` client, `AddDocumentModal`, `mapSpaceAccesses`

**Storage**: N/A — no schema or persistence changes; existing PostgreSQL tables are accessed only through existing endpoints

**Testing**: Vitest + @testing-library/react (jsdom) in `apps/web/tests/`; existing suites `documents.test.tsx`, `space-add.test.tsx`, `document-create-ai-assist.test.tsx` are the reference patterns and regression guards

**Target Platform**: Web (desktop + responsive mobile), modern evergreen browsers

**Project Type**: Web application (monorepo: `apps/web` Next.js frontend, `apps/api` FastAPI backend, `packages/core` domain)

**Performance Goals**: New document visible in the grid within 2s of save (SC-003) — achieved by local state update, no refetch or reload

**Constraints**: No changes to the document creation API contract, fields, or validation (FR-003, FR-007); global Documents page entry point must keep working unchanged

**Scale/Scope**: 1 page modified, 1 component modified (one new optional prop), 1 new test file; no backend changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | ✅ PASS | No domain code touched; UI-only change consuming existing endpoints. |
| II. Separation of Concerns | ✅ PASS | Spec stays technology-agnostic; all technical decisions live in this plan. |
| III. Data Locality & Consent | ✅ PASS | No client-side persistence introduced; dialog state is in-memory only. |
| IV. Test-Driven Development | ✅ PASS | New Vitest suite written first for the space-page button, gating, preselection, grid update, and error paths. No Python modules change, so the 85% Python coverage gate is unaffected. |
| V. Quality Gates | ✅ PASS | Ruff/Black not applicable (no Python changes); ESLint/TypeScript apply to the web changes. |
| VI. Tenant Data Isolation | ✅ PASS | See Tenant Isolation section below. No new queries, endpoints, or data paths are introduced. |

### Tenant Isolation

- **Tables accessed** (all via *existing, unchanged* endpoints): `spaces`, `space_memberships`, `documents`, `document_versions`, `audit_log`.
- **Scoping confirmation**: `POST /v1/documents` (`apps/api/tessera_api/routers/documents.py:96`) resolves the target space with `space_repo.get_by_id_for_company(body.space_id, company_id)`, writes a `cross_tenant_denied` audit entry and returns 404 on mismatch, then enforces editor/admin via `can_write_document` (403 otherwise). `GET /v1/documents?space_id=` performs the same company-scoped space check. `GET /v1/spaces` lists only company-scoped accesses. No query is added or modified by this feature.
- **Isolation tests**: Existing backend isolation tests for document creation and listing remain the enforcement proof; no new data-access path means no new isolation test is required. The new frontend tests cover the UI-level gating (viewer never sees the button) and the 403-error surface in the dialog (FR-006, US2-AC3).
- **Cross-tenant operations**: None introduced.

**Post-design re-check (after Phase 1)**: ✅ PASS — design artifacts introduce no new endpoints, tables, or cross-tenant paths.

## Project Structure

### Documentation (this feature)

```text
specs/061-add-document-button/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── ui-and-api.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/web/
├── app/
│   ├── spaces/[id]/page.tsx          # MODIFIED: "Add Document" button (role-gated) + modal wiring + grid state update
│   └── documents/page.tsx            # UNCHANGED: regression guard only (FR-007)
├── components/
│   └── documents/AddDocumentModal.tsx # MODIFIED: new optional `initialSpaceId` prop for destination preselection
├── lib/
│   ├── spaces.ts                     # UNCHANGED: mapSpaceAccesses/directChildren already used by the page
│   └── types.ts                      # UNCHANGED: SpaceAccess.effective_role already typed
└── tests/
    ├── space-add-document.test.tsx   # NEW: US1 + US2 acceptance scenarios and edge cases
    └── documents.test.tsx            # UNCHANGED: must keep passing (FR-007)

apps/api/                             # UNCHANGED — no backend work in this feature
packages/core/                        # UNCHANGED
```

**Structure Decision**: Web-application layout of the existing monorepo. All changes are confined to `apps/web`: one page (`app/spaces/[id]/page.tsx`), one shared component (`components/documents/AddDocumentModal.tsx`, additive prop only), and one new test file.

## Complexity Tracking

No constitution violations — table intentionally left empty.
