# Implementation Plan: Space Rename

**Branch**: `049-space-rename` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/049-space-rename/spec.md`

## Summary

Add a `PATCH /v1/spaces/{space_id}/name` endpoint, gated to space admins via a new
`SpaceHierarchyService.rename` domain method (mirroring the existing `set_parent`/
`remove_parent` admin checks), plus a **Rename** control on each space tile in the
Spaces menu (`FolderTile`, used by both the top-level Spaces page and the per-space
folder view). The control opens a small inline/modal form pre-filled with the
current name, validates non-empty/≤255-char input client- and server-side, and on
success updates the tile in place without a full reload. Renaming touches only the
`spaces.name` column — no schema change, no effect on `slug`, hierarchy, documents,
or permissions.

## Technical Context

**Language/Version**: Python 3.11 (FastAPI backend, `apps/api` + `packages/core`) +
TypeScript/React 19 (Next.js frontend, `apps/web`) — no new language, matches
existing stack.

**Primary Dependencies**: FastAPI (new router handler), SQLAlchemy async (new
repository method + raw `UPDATE`, following `set_parent`/`remove_parent`), existing
`tessera_core.services.space_hierarchy.SpaceHierarchyService` (new `rename` method) —
all reused, no new dependency. Frontend: existing `api` fetch wrapper
(`apps/web/lib/api.ts`, `api.patch` already used by `SetParentModal`), no new
libraries.

**Storage**: PostgreSQL. No schema change — `spaces.name` is already
`String(255) NOT NULL` (`apps/api/tessera_api/adapters/models/space.py`).

**Testing**: pytest (`packages/core/tests/test_space_hierarchy.py`, new
`TestRenameValidations` class following the existing `TestSetParentValidations`
style) and `apps/api/tests/unit/test_spaces_router.py` (new rename endpoint cases,
module-level-import + `unittest.mock.patch` pattern). Frontend: Vitest + Testing
Library, new `apps/web/tests/space-rename.test.tsx`, following the existing
`spaces.test.tsx` / `space-drag-drop.test.tsx` structure.

**Target Platform**: Linux server (existing FastAPI container) + browser (existing
Next.js app). No new infrastructure.

**Project Type**: Web application (existing `apps/api` + `apps/web` split). Backend
adds one endpoint + one domain method; frontend adds one control + small modal
reused across two existing pages.

**Performance Goals**: Rename must complete within a single request/transaction
with no perceptible added latency versus the existing `set_parent`/`remove_parent`
endpoints — one `UPDATE` statement plus one audit insert.

**Constraints**: Name must be validated non-empty (post-trim) and ≤255 chars on
both client and server (FR-004); rejected/failed renames must leave the stored name
byte-for-byte unchanged (FR-007, SC-003) — satisfied by validating before any
`UPDATE` is issued, same as `set_parent`'s pre-checks.

**Scale/Scope**: One new endpoint, one new repository method + port method, one new
domain service method, one new frontend modal component wired into two existing
pages (`/spaces` and `/spaces/[id]`) via the shared `FolderTile`/`FolderGrid`
components. No new tables, no new Celery task, no new page.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Domain-Driven Architecture**: PASS. The admin-check + rename orchestration
  lives in `SpaceHierarchyService.rename` (pure domain logic, no framework/
  persistence imports), alongside `set_parent`/`remove_parent`. The router only
  resolves the actor, calls the service, and maps exceptions to HTTP responses.
- **II. Separation of Concerns**: PASS. Persistence only leaks in via the
  `SpaceRepository.rename` port method, implemented by `SqlSpaceRepository`,
  matching the existing `set_parent`/`remove_parent` pattern exactly.
- **III. Data Locality & Consent**: PASS. No client-side persistence introduced.
- **IV. Test-Driven Development**: PASS (enforced in Phase 2/implementation). New
  failing tests will be written first for: `SpaceHierarchyService.rename`
  (non-admin/empty-name/too-long/success cases) in `packages/core`, the router
  (200/400/403/404 cases) in `apps/api`, and the new modal component in
  `apps/web`, before implementation, following this repo's existing red-green
  pattern.
- **V. Quality Gates**: PASS (enforced in Phase 2/implementation) — Ruff and Black
  run before commit, as for every change in this repo.
- **VI. Tenant Data Isolation**: PASS — see Tenant Isolation section below.

### Tenant Isolation

- **Tables accessed**: `spaces` (read then update), `space_memberships` (read, for
  the admin permission check), `audit_records` (insert). No new tables.
- **`company_id` scoping**: The space is resolved via
  `SqlSpaceRepository.get_by_id_for_company(space_id, company_id)` — identical to
  the existing `get_space` and `set_parent`'s parent-lookup — *before* the rename
  or the permission check runs. A cross-company `space_id` therefore 404s (via the
  same `_not_found()` helper already used elsewhere in `spaces.py`), and the
  `UPDATE spaces SET name = ... WHERE id = :space_id` only ever executes after
  that scoped lookup confirms the space belongs to the caller's company.
- **Cross-tenant operations introduced**: None.
- **Isolation tests**: A new test (mirroring `test_missing_admin_on_child_raises_
  permission_error` in `test_space_hierarchy.py`, and the router's existing
  cross-tenant 404 pattern) will assert that a rename request for a space
  belonging to a different company returns 404, and that the mocked
  `space_repo.rename` is NOT called in that case.

## Project Structure

### Documentation (this feature)

```text
specs/049-space-rename/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── rename-space-endpoint.md   # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
packages/core/
├── tessera_core/
│   ├── ports/repositories/space.py     # + abstract rename(space_id, name) method
│   └── services/space_hierarchy.py     # + rename(actor_id, space_id, name, company_id)
└── tests/
    └── test_space_hierarchy.py         # + TestRenameValidations class

apps/api/
├── tessera_api/
│   ├── adapters/repositories/space.py  # SqlSpaceRepository: + rename()
│   └── routers/spaces.py               # + PATCH /spaces/{space_id}/name handler
└── tests/unit/
    └── test_spaces_router.py           # + rename-endpoint test cases

apps/web/
├── components/spaces/
│   ├── FolderTile.tsx                   # + "Rename" control (admin-only, mirrors "Set parent")
│   └── RenameSpaceModal.tsx             # new file, mirrors SetParentModal.tsx
├── app/spaces/page.tsx                  # + renamingSpace state, wires RenameSpaceModal
├── app/spaces/[id]/page.tsx             # + renamingSpace state, wires RenameSpaceModal
└── tests/
    └── space-rename.test.tsx            # new file
```

**Structure Decision**: No new projects, directories, or top-level files — this is
a localized addition across the three layers already established by the nested-
spaces features (041 hierarchy, 044 folder navigation): a domain service method, a
repository method + router endpoint, and a small frontend modal reused across the
two existing space-browsing pages via the shared `FolderTile` component. No
changes to `db/migrations` or `apps/workers`.

## Complexity Tracking

*No violations — table omitted.*
