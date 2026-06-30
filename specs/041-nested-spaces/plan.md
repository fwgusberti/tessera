# Implementation Plan: Nested Spaces

**Branch**: `041-nested-spaces` | **Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/041-nested-spaces/spec.md`

## Summary

Add parent-child hierarchy to Spaces: a Space gains an optional `parent_space_id` FK pointing to another Space in the same company. Access is computed dynamically — a user who holds a direct membership in any ancestor of a space is considered to have effective access to that space, inheriting the role from the nearest ancestor where the direct membership exists. Permission does not flow upward (child membership never grants parent access). The implementation requires a DB migration, a new domain service in `tessera_core`, extended repository port and SQLAlchemy adapter, updated API endpoints, and a hierarchy-aware frontend listing.

## Technical Context

**Language/Version**: Python 3.12 (backend core + API), TypeScript 5 / React 18 / Next.js 14 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2, pytest + anyio, Next.js, Tailwind CSS

**Storage**: PostgreSQL — recursive CTEs (`WITH RECURSIVE`) used for ancestor/descendant traversal

**Testing**: pytest-asyncio (`@pytest.mark.asyncio`) for core package; anyio (`@pytest.mark.anyio`) for API package; `fastapi.testclient.TestClient` (sync) for integration tests

**Target Platform**: Linux server

**Project Type**: Web application — FastAPI backend + Next.js frontend

**Performance Goals**: Access checks must complete within the same response-time envelope as flat-space checks; recursive CTE on depth ≤ 10 is constant-bounded

**Constraints**: Max nesting depth = 10 levels; parent must be in same company; no circular chains; parent removal (→ root) requires admin only in child

**Scale/Scope**: Single company tenant, bounded hierarchy depth, same performance envelope as existing flat queries

## Constitution Check

### I. Domain-Driven Architecture ✅
Cycle detection, depth limit enforcement, role permission checks, and "effective membership" derivation all live in `tessera_core/services/space_hierarchy.py`. The SQLAlchemy repository handles recursive SQL — it does not leak into domain logic. The domain service depends only on port abstractions.

### II. Separation of Concerns ✅
`Space` domain model gains `parent_space_id` with no framework imports. Repository and adapter change independently.

### III. Data Locality & Consent — N/A
No local client persistence introduced.

### IV. Test-Driven Development ✅
All domain service logic (cycle detection, depth, role inheritance, upward isolation) written test-first. API integration tests written before router handlers. Isolation tests written alongside cross-tenant checks. 85% coverage gate applies.

### V. Quality Gates ✅
Ruff + Black enforced on all new Python files. TypeScript ESLint on frontend.

### VI. Tenant Data Isolation ✅ (mandatory section)

**Tables accessed**:
- `spaces` — read/write with `company_id` filter on all queries
- `space_memberships` — read-only for effective membership computation

**company_id scoping**:
- `parent_space_id` FK resolves within the `company_id` boundary enforced by the service layer: the service calls `get_by_id_for_company` before accepting a proposed parent — a parent from a different company is invisible and treated as absent (FR-007).
- The recursive CTE for descendant expansion includes `WHERE company_id = :company_id` in both the base and recursive legs.
- `list_accessible_by_user` is always called with `(user_id, company_id)` from the authenticated session.

**Cross-tenant isolation tests required**:
1. `test_set_parent_rejects_cross_company_parent` — Company A space cannot be set as parent of Company B space.
2. `test_list_accessible_by_user_never_leaks_across_companies` — User in Company A cannot see Company B spaces even if Company B has a space with the same parent ID pattern.
3. `test_inherited_access_stays_within_company` — Even if parent_space_id FK were somehow set to a cross-company space, the recursive CTE's company_id filter stops propagation.

## Project Structure

### Documentation (this feature)

```text
specs/041-nested-spaces/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── spaces.md        # Phase 1 REST API contracts
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
packages/core/tessera_core/
├── domain/
│   ├── space.py                  # ADD: parent_space_id field
│   └── space_access.py           # NEW: SpaceAccess value object (space + effective_role + is_direct)
├── ports/repositories/
│   └── space.py                  # ADD: get_ancestor_chain, set_parent, remove_parent, list_accessible_by_user
└── services/
    └── space_hierarchy.py        # NEW: SpaceHierarchyService (all business rules)

packages/core/tests/
└── test_space_hierarchy.py       # NEW: unit tests for service (cycle detection, depth, role inheritance, isolation)

apps/api/tessera_api/
├── adapters/
│   ├── models/
│   │   └── space.py              # ADD: parent_space_id FK column + self-referential relationship
│   └── repositories/
│       └── space.py              # ADD: SQL implementations of new port methods (recursive CTE)
└── routers/
    └── spaces.py                 # ADD: PATCH/DELETE /spaces/{id}/parent; UPDATE GET /spaces (user-filtered)

apps/api/tests/
├── test_space_hierarchy.py       # NEW: integration tests (inheritance, isolation, cycle rejection)
└── test_space_hierarchy_isolation.py  # NEW: cross-tenant isolation tests

db/migrations/versions/
└── 0012_space_parent.py          # NEW: add parent_space_id FK to spaces table

apps/web/
├── lib/
│   └── types.ts                  # ADD: parent_space_id to Space type; SpaceAccess type
├── app/spaces/
│   └── page.tsx                  # UPDATE: render hierarchy-aware listing
└── components/spaces/
    ├── SpaceCard.tsx             # UPDATE: show indentation + breadcrumb when parent not visible
    ├── SpaceHierarchyView.tsx    # NEW: tree-rendering component from flat list
    ├── SpaceBreadcrumb.tsx       # NEW: ancestor path display for orphaned child spaces
    └── SetParentModal.tsx        # NEW: admin UI to assign/change/remove parent
```

## Complexity Tracking

No constitution violations.
