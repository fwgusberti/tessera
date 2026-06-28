# Implementation Plan: Confine Space Visibility to the Active Company

**Branch**: `037-fix-cross-company-space-visibility` | **Date**: 2026-06-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/037-fix-cross-company-space-visibility/spec.md`

## Summary

The everyday "my company's spaces" view (`GET /v1/spaces`) was already scoped to the
active company via `SqlSpaceRepository.list_by_company(company_id)` since feature 031,
and feature 036 closed the by-ID and management-authority gaps (404-indistinguishable
cross-company denial, per-company admin). What remains is the **listing / visibility**
half of the invariant plus the removal of the one latent mechanism that still encodes
the exact leak the user reported.

The smoking gun is `SpaceRepository.list_for_user(user)` (declared in the domain port
`packages/core/.../ports/repositories.py` and implemented in
`apps/api/.../adapters/repo.py`):

```python
async def list_for_user(self, user: User) -> list[Space]:
    if user.is_admin:
        return await self.list_all()          # every company's spaces
    if not user.groups:
        return []
    # join RolePermission by idp_group across ALL companies — no company_id filter
```

Its three branches reproduce the bug table verbatim: a global-admin sees **all** spaces
(a@3.com → A, B, C), a group-matched user leaks into other companies' spaces
(felipe → C), and a member with no matching groups sees **nothing** (a@2.com → none).
It is a standing violation of Constitution Principle VI (unscoped multi-tenant query +
`is_admin` cross-tenant shortcut). It is currently **dead code** (no caller outside its
own definition and the port), but a loaded gun in the domain contract.

This feature:

1. **Removes `list_for_user`** from the `SpaceRepository` port and its SQL
   implementation, deleting the only unscoped, `is_admin`-driven space query. The
   everyday visibility path is then `list_by_company(company_id)` with no alternative
   (FR-001, FR-003, FR-004, root cause of the reproduction).
2. **Locks the visibility invariant with tests**: a three-user reproduction test
   (SC-002) and per-path cross-company *listing* isolation tests for every surface that
   resolves a company's space set — `GET /v1/spaces`, search, assistant, documents —
   asserting 100%-own / 0%-other (SC-001, SC-003, SC-004). 036 covered by-ID + mutation;
   037 covers the list path it did not.
3. **Makes the platform-operator surface explicitly audited** (FR-008, FR-009): the
   `/v1/admin/*` space endpoints (`GET /admin/spaces`, `PUT /admin/spaces/{id}/retention`,
   `POST /admin/reindex`) read across companies under the global `is_admin` gate — the
   single documented cross-tenant exception. They currently emit no record of that
   cross-company read. We add a `cross_company_admin_access` audit emission so the
   exception is auditable and visibly separate from the everyday view.
4. **No schema change, no migration.** Spaces already carry `company_id`; expressing
   correct scoping is purely a query/contract concern (spec Assumption 3).

## Technical Context

**Language/Version**: Python 3.12 (API + domain); TypeScript / Next.js (web, read-only verification)

**Primary Dependencies**: FastAPI, SQLAlchemy (async), joserfc (JWT),
itsdangerous (SessionMiddleware), Alembic, pytest + anyio

**Storage**: PostgreSQL (async SQLAlchemy). **No schema/DDL change and no migration** —
`spaces.company_id` already exists and is indexed; this feature only removes an unscoped
query and adds audit rows to the existing `audit_records` table.

**Testing**: pytest + anyio; integration tests use `fastapi.testclient.TestClient`
(sync). Cross-company visibility tests extend the existing `two_company_setup` and
`legacy_global_admin_setup` fixtures in `apps/api/tests/conftest.py` (the latter already
models the global-admin-in-A / space-in-B leak scenario). Domain-port shape is unit-checked
in `packages/core/tests`. Per memory: core pkg uses `@pytest.mark.asyncio`, API pkg uses
`@pytest.mark.anyio` — do not mix.

**Target Platform**: Linux server (Docker / Kubernetes)

**Project Type**: Web — monorepo: `apps/api` (FastAPI transport), `packages/core`
(pure domain), `apps/web` (Next.js). This feature is backend-centric; the web side is
verification only (confirm the everyday pages call `/v1/spaces`, never `/v1/admin/spaces`).

**Performance Goals**: No new hot path. `list_by_company` is a single indexed lookup on
`spaces.company_id` and is unchanged. Removing `list_for_user` deletes a query, not adds one.

**Constraints**: Domain (`packages/core`) MUST stay free of transport/persistence imports.
The everyday space-visibility path MUST have exactly one query shape — `list_by_company`.
Cross-company by-ID denial stays byte-identical to genuine not-found (404 + generic body,
carried from 036). Any cross-company read MUST occur only on the audited platform-operator
surface.

**Scale/Scope**: 1 domain port edit (remove `list_for_user`), 1 repo edit (remove impl),
3 admin endpoints gain an audit emission, ~4 listing isolation tests + 1 reproduction
test. No new tables, no DDL, no migration, no new resource types.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | PASS | Change is removal of an unscoped method from the domain port + its adapter impl. No framework/transport/persistence import enters the domain. |
| II. Separation of Concerns | PASS | Company scoping stays at the API boundary (`require_company_context` → `company_id`) and is threaded into the one remaining query. No product/domain definition changes with technology. |
| III. Data Locality & Consent | PASS | No client-side persistence; no new user data captured. |
| IV. Test-Driven Development | PASS (planned) | Reproduction + per-path listing isolation tests written failing-first against the pre-removal behavior, then `list_for_user` removed. 85%+ coverage maintained (removal reduces uncovered surface). |
| V. Quality Gates | PASS (planned) | Ruff + Black must pass before commit. |
| VI. Tenant Data Isolation | **PASS — this feature's purpose** | Deletes the last unscoped multi-tenant space query and the last `is_admin` cross-tenant read shortcut over the everyday view. See Tenant Isolation section. |

**Tenant Isolation section** (required per Security Requirements):

- **Tables accessed & scoping**:
  - `spaces` → everyday visibility via `list_by_company(company_id)` only
    (`WHERE spaces.company_id = :active_company`); by-ID via `get_by_id_for_company`
    (404 on miss). The unscoped `list_for_user` join is **removed**. `list_all()` is
    retained but reachable **only** from the audited `/v1/admin/*` surface.
  - `role_permissions` → no longer joined for visibility (the group-based join lived
    only inside the removed `list_for_user`). Still read per-space for in-space role
    resolution, which is already space/company-scoped.
  - `audit_records` → append-only; gains `cross_company_admin_access` rows on the
    operator surface and continues to receive `cross_tenant_denied` rows on by-ID misses.
- **New data-access paths**: none. No method gains a bare entity ID. A query shape is
  removed, not added.
- **Cross-tenant isolation tests** (visibility/listing focus, complementing 036's by-ID
  + mutation tests):
  - **Reproduction (SC-002)**: three companies, three spaces; felipe(Gusba)→{A,B},
    a@2(Co2)→{C}, a@3(Co3, global admin)→{} — asserted against the live `GET /v1/spaces`.
  - **Per-path listing isolation (SC-001, SC-003)**: for each of `GET /v1/spaces`,
    search, assistant, documents — a caller active as Company A receives only A's spaces;
    Company B's spaces never appear, even when the caller carries the legacy global
    `is_admin` flag (`legacy_global_admin_setup`).
  - **Member-without-platform-status (SC-004, US2)**: an ordinary member of Company B
    (no `is_admin`) sees B's spaces in 100% of attempts.
  - **By-ID indistinguishability (SC-005)**: probing a Company B space id while active as
    A returns the same 404 + generic body as a non-existent id (regression guard over 036).
- **Intentional cross-tenant exception (FR-008)**: the global `is_admin` capability is
  retained ONLY for the platform-operator endpoints in `admin.py`
  (`GET /v1/admin/spaces`, `PUT /v1/admin/spaces/{id}/retention`, `POST /v1/admin/reindex`).
  After this feature these endpoints emit a `cross_company_admin_access` audit record so
  the exception is auditable and provably distinct from the everyday company-member view.
  Building or expanding operator tooling is out of scope; this is the single documented
  exception, carried forward from 035/036.

No constitution violations. Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/037-fix-cross-company-space-visibility/
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Phase 0 — root-cause & operator-surface audit decisions
├── data-model.md        # Phase 1 — visibility query model, audit action, no schema change
├── quickstart.md        # Phase 1 — reproduction + per-path isolation validation
├── contracts/
│   └── space-visibility-matrix.md   # Phase 1 — per-surface visibility source before/after
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (files touched)

```text
packages/core/tessera_core/
└── ports/repositories.py          # REMOVE abstract list_for_user from SpaceRepository

apps/api/tessera_api/
├── adapters/repo.py               # REMOVE SqlSpaceRepository.list_for_user (keep
│                                  #   list_by_company / list_all / get_by_id_for_company)
└── routers/admin.py               # add cross_company_admin_access audit emission to
                                   #   list_all_spaces / update_retention_policy / bulk_reindex

apps/api/tests/
├── conftest.py                    # add a three-company reproduction fixture (A,B,C)
├── test_space_visibility.py       # NEW — reproduction (SC-002) + per-path listing isolation
│                                  #   (SC-001/003/004) + operator-surface audit assertion
└── test_tenant_isolation.py       # extend: list path never leaks under legacy is_admin
packages/core/tests/
└── test_repositories_port.py      # NEW/extend — assert SpaceRepository has no list_for_user

apps/web/                          # VERIFICATION ONLY (no functional change expected):
                                   #   confirm everyday pages call /v1/spaces, admin page
                                   #   alone calls /v1/admin/spaces
```

**Structure Decision**: Existing monorepo layout (031/035/036 precedent). The active-company
decision stays at the API boundary; the remaining space-visibility query is the pure,
company-scoped `list_by_company`. No new packages, tables, top-level dirs, or migration.

## Complexity Tracking

> No Constitution Check violations — section intentionally empty.
