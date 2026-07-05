# Implementation Plan: Add Space

**Branch**: `051-add-space` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/051-add-space/spec.md`

## Summary

Extend the existing `POST /v1/spaces` endpoint so `slug`, `sector`, and
`parent_space_id` become optional: the slug is auto-derived from the name (with a
collision-safe suffix), the sector defaults to `"General"`, and an optional
`parent_space_id` lets the same endpoint create a space directly as a sub-space,
reusing `SpaceHierarchyService`'s existing parent-admin and depth-limit checks
(mirroring `set_parent`) instead of a separate create-then-reparent round trip.
On the frontend, add an "Add Space" button + `AddSpaceModal` (name-only form,
mirroring `RenameSpaceModal`) to both the top-level Spaces page (creates a root
space) and the per-space folder view (creates a sub-space nested under the space
being viewed), wired through the shared `FolderGrid`/`FolderTile` pages so the new
tile appears immediately without a reload.

## Technical Context

**Language/Version**: Python 3.11 (FastAPI backend, `apps/api` + `packages/core`)
+ TypeScript/React 19 (Next.js frontend, `apps/web`) — no new language, matches
existing stack.

**Primary Dependencies**: None new. FastAPI + SQLAlchemy async (extends the
existing `POST /spaces` handler and `SqlSpaceRepository`), the existing
`tessera_core.services.space_hierarchy.SpaceHierarchyService` (new `create`
method, reusing its private `_MAX_DEPTH` constant and parent-admin check
pattern), and Python's stdlib `unicodedata`/`re` for slug generation (no
third-party slugify package). Frontend: existing `api` fetch wrapper
(`apps/web/lib/api.ts`, `api.post` already used by the admin console's create
form), no new libraries.

**Storage**: PostgreSQL. No schema change — `spaces.slug` is already
`String(100) UNIQUE NOT NULL` and `spaces.sector` is already `String NOT NULL`
(`apps/api/tessera_api/adapters/models/space.py`); both already tolerate any
non-empty string, so defaulting/auto-generating them at the service layer
requires no migration.

**Testing**: pytest (`packages/core/tests/test_space_hierarchy.py`, new
`TestCreateValidations` class following the existing `TestRenameValidations`
style; `apps/api/tests/unit/test_spaces_router.py`, extending
`TestCreateSpaceGrantsCreatorMembership` with parent/slug/sector cases;
`apps/api/tests/test_space_hierarchy_isolation.py`, new cross-tenant
create-with-parent case). Frontend: Vitest + Testing Library, new
`apps/web/tests/space-add.test.tsx`, following the existing
`space-rename.test.tsx` / `space-folder-view.test.tsx` structure.

**Target Platform**: Linux server (existing FastAPI container) + browser
(existing Next.js app). No new infrastructure.

**Project Type**: Web application (existing `apps/api` + `apps/web` split).
Backend extends one endpoint + one domain service method + one repository port
method; frontend adds one control + one modal wired into two existing pages.

**Performance Goals**: Creation must complete within a single request/transaction
with no perceptible added latency versus the existing create/set-parent/rename
endpoints — one slug-uniqueness lookup (only when the slug is auto-derived), one
`INSERT` for the space, one `INSERT` for the creator's admin membership, and two
audit inserts.

**Constraints**: Name must be validated non-empty (post-trim) and ≤255 chars on
both client and server (FR-003), reusing the exact validation already written for
rename (FR-004 of 049). Auto-derived slugs must fit the existing 100-char column
and stay unique without ever surfacing the concept of a "slug" to the user
(spec Assumptions). Sub-space creation must never leave an orphaned root-level
space if the parent-nesting step fails — creation and parent assignment happen in
one service call/transaction, not two sequential requests (FR-008).

**Scale/Scope**: One extended endpoint (no new route), one new domain service
method (`SpaceHierarchyService.create`), one new pure helper (`slugify`), one new
repository port method (`slug_exists`), one new frontend modal component wired
into two existing pages (`/spaces` and `/spaces/[id]`) via the shared
`FolderGrid`. No new tables, no new Celery task, no new page.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Domain-Driven Architecture**: PASS. Name validation, slug resolution,
  and the parent-admin/depth-limit checks all live in
  `SpaceHierarchyService.create` (pure domain orchestration), alongside
  `set_parent`/`remove_parent`/`rename`. Slug uniqueness is checked via a new
  `SpaceRepository.slug_exists` **port** method (abstract), not by catching a
  SQLAlchemy `IntegrityError` in the service — persistence exceptions never leak
  into domain code. The router only resolves the actor, calls the service, grants
  the creator's admin membership, and maps exceptions to HTTP responses.
- **II. Separation of Concerns**: PASS. Persistence only leaks in via
  `SqlSpaceRepository.slug_exists` (new) and the existing `create` method,
  matching the `set_parent`/`remove_parent`/`rename` pattern exactly.
- **III. Data Locality & Consent**: PASS. No client-side persistence introduced.
- **IV. Test-Driven Development**: PASS (enforced in Phase 2/implementation). New
  failing tests will be written first for: `SpaceHierarchyService.create`
  (empty/too-long name, root creation, sub-space creation, non-admin-of-parent,
  cross-company parent, depth-limit, slug auto-generation, slug-collision
  suffixing, explicit-slug passthrough) in `packages/core`; the router (parent/
  slug/sector default cases, audit assertions) in `apps/api`; the new
  `AddSpaceModal` and its wiring into both pages in `apps/web` — before
  implementation, following this repo's existing red-green pattern.
- **V. Quality Gates**: PASS (enforced in Phase 2/implementation) — Ruff and
  Black run before commit, as for every change in this repo.
- **VI. Tenant Data Isolation**: PASS — see Tenant Isolation section below.

### Tenant Isolation

- **Tables accessed**: `spaces` (insert; read for parent lookup, ancestor chain,
  and slug-uniqueness check), `space_memberships` (insert for the creator's admin
  grant; read for the parent-admin check), `audit_records` (two inserts). No new
  tables.
- **`company_id` scoping**: The new space's `company_id` always comes from the
  authenticated `CompanyContext`, never from the request body (FR-011) — the
  request schema has no `company_id` field, mirroring every other endpoint in
  this router. When `parent_space_id` is supplied, it is resolved via the
  existing `SqlSpaceRepository.get_by_id_for_company(parent_space_id,
  company_id)` — identical to `set_parent`'s parent lookup — *before* any write.
  A `parent_space_id` belonging to another company therefore resolves to `None`
  and is rejected exactly like `set_parent`'s `cross_company` case, with no
  space or membership row created.
- **Cross-tenant operations introduced**: None.
- **Isolation tests**: A new test in `apps/api/tests/test_space_hierarchy_isolation.py`
  (mirroring `test_set_parent_rejects_cross_company_parent`) asserts that
  creating a space with a `parent_space_id` belonging to a different company is
  rejected and that neither `SpaceRepository.create` nor the membership insert
  is called.

## Project Structure

### Documentation (this feature)

```text
specs/051-add-space/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── create-space-endpoint.md   # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
packages/core/
├── tessera_core/
│   ├── ports/repositories/space.py     # + abstract slug_exists(slug) method
│   ├── services/slug.py                # new: slugify(name) -> str (pure helper)
│   └── services/space_hierarchy.py     # + create(actor_id, company_id, name, sector,
│                                        #   slug=None, parent_space_id=None, ...)
└── tests/
    ├── test_slug.py                    # new: slugify() unit tests
    └── test_space_hierarchy.py         # + TestCreateValidations class

apps/api/
├── tessera_api/
│   ├── adapters/repositories/space.py  # SqlSpaceRepository: + slug_exists()
│   └── routers/spaces.py               # CreateSpaceRequest: slug/sector optional,
│                                        #   + parent_space_id; create_space() calls
│                                        #   svc.create(...); + "space_created" audit
└── tests/
    ├── unit/test_spaces_router.py      # + parent/slug/sector default cases
    └── test_space_hierarchy_isolation.py  # + cross-tenant create-with-parent case

apps/web/
├── components/spaces/
│   ├── FolderGrid.tsx / FolderTile.tsx  # unchanged (Add Space is a page-level
│   │                                     #   action, not a per-tile control)
│   └── AddSpaceModal.tsx                # new file, mirrors RenameSpaceModal.tsx
├── app/spaces/page.tsx                  # + "Add Space" button, addingSpace state,
│                                        #   wires AddSpaceModal (no parent)
├── app/spaces/[id]/page.tsx             # + "Add Space" button (rendered even when
│                                        #   the folder is empty), wires AddSpaceModal
│                                        #   with parentSpaceId={folderId}
└── tests/
    └── space-add.test.tsx               # new file
```

**Structure Decision**: No new projects, directories, or top-level files — this
is a localized extension across the three layers already established by the
nested-spaces features (041 hierarchy, 044 folder navigation, 049 rename): one
new pure domain helper, one new repository port method, one extended domain
service method, one extended router endpoint, and one small frontend modal
reused across the two existing space-browsing pages. No changes to
`db/migrations` or `apps/workers`.

## Complexity Tracking

*No violations — table omitted.*
