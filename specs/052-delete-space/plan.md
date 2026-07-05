# Implementation Plan: Delete Space

**Branch**: `052-delete-space` | **Date**: 2026-07-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/052-delete-space/spec.md`

## Summary

Add a cascading, permanently-destructive space deletion capability, triggered from a "Delete" action on space tiles (spaces page and folder sub-view), gated by a two-step client flow (confirm scope → re-enter password) and enforced server-side by a new `DELETE /v1/spaces/{space_id}` endpoint. The endpoint requires ADMIN role on the target space (or company-admin), re-verifies the caller's current password, then deletes the space and its full descendant subtree in one transaction. Because `spaces.parent_space_id` uses `ON DELETE SET NULL` (not CASCADE), the descendant subtree must be resolved explicitly via a recursive CTE before deletion — everything else (documents, versions, drafts, chunks, memberships, role permissions, connectors) already cascades automatically via existing `ON DELETE CASCADE` foreign keys once the owning space rows are removed.

## Technical Context

**Language/Version**: Python 3.12 (apps/api, packages/core), TypeScript/Next.js App Router (apps/web) — no new languages.

**Primary Dependencies**: FastAPI + SQLAlchemy async (asyncpg) on the backend; existing `tessera_api.auth.jwt_auth.verify_password` for password re-verification (already used by `/v1/auth/change-password`, no new crypto dependency); React/Tailwind on the frontend, reusing the existing `api` fetch client.

**Storage**: PostgreSQL — existing tables `spaces`, `documents`, `document_versions`, `document_drafts`, `chunks`, `space_memberships`, `role_permissions`, `connectors`, `audit_records`. No schema migration needed: all cascades required by this feature already exist except the space-to-space parent link, which is handled in application code (see Summary).

**Testing**: pytest-asyncio for `packages/core/tests/test_space_hierarchy.py`; pytest-anyio + `fastapi.testclient.TestClient` for `apps/api/tests/unit/test_spaces_router.py` and `apps/api/tests/test_space_hierarchy_isolation.py`; Jest/RTL for `apps/web/tests/space-delete.test.tsx`.

**Target Platform**: Linux server (existing Docker/Kubernetes deployment); modern web browsers.

**Project Type**: Web application (existing monorepo: `apps/api` + `apps/web` + `packages/core`).

**Performance Goals**: N/A beyond existing API norms — deletion is an infrequent, admin-triggered action, not a hot path.

**Constraints**: The full subtree deletion (space rows + everything FK-cascaded from them) MUST happen inside a single DB transaction — no partial deletion on failure. Every space lookup MUST stay scoped to the caller's `company_id` (Principle VI).

**Scale/Scope**: Space nesting is capped at depth 10 (existing `_MAX_DEPTH` in `space_hierarchy.py`), so subtree size is always small; a single recursive CTE plus one bulk `DELETE ... WHERE id IN (...)` is sufficient with no batching/pagination.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Domain-Driven Architecture** — PASS. Authorization (ADMIN-or-company-admin check) and orchestration live in `SpaceHierarchyService.delete()` (packages/core, framework-free). The recursive-CTE subtree resolution and bulk delete are pure persistence mechanics and live entirely in `SqlSpaceRepository` (apps/api adapter), matching how `get_ancestor_chain`/`list_accessible_by_user` already keep SQL out of the domain layer. Password hashing/verification is an API-layer auth concern (`tessera_api.auth.jwt_auth`) and is never passed into or handled by the domain service.
- **II. Separation of Concerns** — PASS. No product/domain definition depends on Postgres-specific syntax; the `SpaceRepository` port gains one new abstract method (`delete_subtree`) that any adapter could implement differently.
- **III. Data Locality & Consent** — N/A. No new client-side persistence introduced.
- **IV. Test-Driven Development** — PASS (plan). New service method, repository method, and router endpoint each get failing tests written first, mirroring the existing `TestCreateValidations` / `TestRenameValidations` structure in `packages/core/tests/test_space_hierarchy.py` and the `TestCreateSpaceValidationErrors` structure in `apps/api/tests/unit/test_spaces_router.py`.
- **V. Quality Gates** — PASS (plan). Ruff/Black run as usual; no exemptions needed.
- **VI. Tenant Data Isolation (NON-NEGOTIABLE)** — PASS, with explicit Tenant Isolation subsection below.

### Tenant Isolation

- **Tables accessed**: `spaces` (read + delete), and — purely as cascade side effects of deleting `spaces` rows, never queried directly by this feature's code — `documents`, `document_versions`, `document_drafts`, `chunks`, `space_memberships`, `role_permissions`, `connectors`.
- **`company_id` scoping**: The target space is resolved via the existing `get_by_id_for_company(space_id, company_id)` (same call used by `rename`/`set_parent`) before anything else — a space outside the caller's company is indistinguishable from a nonexistent one (404). The descendant-subtree CTE additionally filters every recursive step on `s.company_id = :company_id` (defense-in-depth, mirroring the double-scoped pattern already used in `list_accessible_by_user`), so even a hypothetical data-integrity slip (a cross-company `parent_space_id`) cannot pull a foreign-tenant space into the deletion.
- **Cross-tenant isolation tests**: New tests in `apps/api/tests/test_space_hierarchy_isolation.py` mirroring the existing `TestCrossTenantIsolation` class — Company A admin attempting to delete a Company B `space_id` gets 404 and Company B's space/documents remain fully intact; a nested case where a Company A subtree contains no Company B nodes even under a crafted/inconsistent `parent_space_id`.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
packages/core/tessera_core/
├── ports/repositories/space.py        # + delete_subtree() abstract method
├── services/space_hierarchy.py        # + delete() — auth + orchestration
└── (tests) ../../tests/test_space_hierarchy.py   # + TestDeleteValidations

apps/api/tessera_api/
├── routers/spaces.py                       # + DELETE /v1/spaces/{space_id}
├── adapters/repositories/space.py          # + delete_subtree() (recursive CTE + bulk delete)
└── tests/
    ├── unit/test_spaces_router.py          # + TestDeleteSpace*
    └── test_space_hierarchy_isolation.py   # + cross-tenant delete isolation tests

apps/web/
├── lib/api.ts                              # api.delete() gains optional body param
├── components/spaces/
│   ├── FolderTile.tsx                      # + onDelete prop, "Delete" action (isAdmin-gated)
│   └── DeleteSpaceModal.tsx                # new: confirm-scope step → password step
├── app/spaces/page.tsx                     # wire deletingSpace state + modal
├── app/spaces/[id]/page.tsx                # wire deletingSpace state + modal
└── tests/space-delete.test.tsx             # new
```

**Structure Decision**: Existing three-package layout (`packages/core` domain/services, `apps/api` FastAPI adapters/routers, `apps/web` Next.js) is unchanged — this feature adds one repository method, one service method, one endpoint, and one new frontend modal, following the exact file layout established by the `rename`/`set_parent` space-hierarchy features (049, 041) and the `delete_document` feature (048).

## Complexity Tracking

*No constitution violations — section left empty.*

## Post-Design Constitution Re-check

Re-evaluated after Phase 1 (data-model.md, contracts/, quickstart.md): no new
violations. The final design keeps SQL/cascade mechanics entirely in
`SqlSpaceRepository` (adapter), authorization + orchestration in
`SpaceHierarchyService` (domain), and password verification in the router via
the existing `verify_password` auth helper — matching what the Constitution
Check above already assumed. All gates still PASS.
