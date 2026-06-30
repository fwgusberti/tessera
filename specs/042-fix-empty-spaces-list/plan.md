# Implementation Plan: Fix Empty Spaces List

**Branch**: `042-fix-empty-spaces-list` | **Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/042-fix-empty-spaces-list/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Two fixes close the gap left by feature 041, which made `GET /v1/spaces` (and
everything that calls it) depend entirely on explicit `space_memberships`
rows: (1) `POST /v1/spaces` now grants the creator an admin `SpaceMembership`
in the same transaction as space creation, so every space created from now on
is immediately visible to its creator; (2) a one-time data migration backfills
an admin `SpaceMembership` for each affected company's admin(s) on every space
that currently has zero recorded members, restoring access to spaces created
before this fix existed. No change to the access-checking query itself
(`list_accessible_by_user`'s recursive CTE) — confirmed via the clarification
session, the model introduced by 041 (explicit, recorded membership) is
correct and stays intact; this feature only ensures the records it depends on
are never missing.

## Technical Context

**Language/Version**: Python 3.12 (API + migrations)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 (async), Alembic (migrations)

**Storage**: PostgreSQL — `spaces`, `space_memberships`, `company_memberships` (existing tables, no schema change)

**Testing**: pytest + pytest-asyncio/anyio; migration backfill tested against a real Postgres connection inside a rolled-back transaction (matching the existing `test_migration_0010_backfill.py` pattern) — mocks alone can't prove a bulk `INSERT ... SELECT` is correct

**Target Platform**: Linux server (API container + Alembic migration runner)

**Project Type**: Web application backend fix (existing `apps/api` + `db/migrations`, no frontend code changes — the bug surfaces in the frontend but the fix is entirely in the data the frontend already consumes via `GET /v1/spaces`)

**Performance Goals**: Backfill is a one-time, one-shot migration over existing rows — no ongoing performance target; the creation-time grant adds one `INSERT` to an already-mutating request, negligible latency impact

**Constraints**: Backfill MUST be idempotent (safe to re-run, matching the `0010` precedent) and MUST NOT touch spaces that already have at least one recorded member (FR-003); MUST grant every company admin, not just one, when a company has multiple

**Scale/Scope**: One new migration (`0013`), one endpoint behavior change (`POST /v1/spaces`), zero new tables/columns, zero frontend changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Domain-Driven Architecture**: The creation-time grant reuses the existing `SpaceMembershipRepository` port/adapter and `SpaceMembership` domain entity — no new domain concepts. The backfill is raw SQL inside a migration (infrastructure layer by definition, same as migration 0010), not domain code. ✅ PASS
- **II. Separation of Concerns**: `spec.md` describes the user-facing problem with no implementation references; this plan carries the technical decisions. ✅ PASS
- **III. Data Locality & Consent**: No new client-side persistence. ✅ PASS (N/A)
- **IV. Test-Driven Development**: A failing test for `POST /v1/spaces` (creator gets a membership) and a failing real-DB test for the migration's backfill SQL (mirroring `test_migration_0010_backfill.py`) are written before each respective implementation. ✅ PASS (enforced in Tasks)
- **V. Quality Gates**: Ruff/Black run on all touched Python files. ✅ PASS
- **VI. Tenant Data Isolation (NON-NEGOTIABLE)** — **Tenant Isolation section**:
  - Tables accessed: `spaces`, `space_memberships`, `company_memberships` — all already `company_id`-scoped (`spaces.company_id`; `space_memberships` scoped transitively via `spaces.company_id`; `company_memberships.company_id`).
  - Creation-time grant: the membership row is created for `space.company_id`'s own creator, using the same `company_id` already validated by the `CompanyContext` dependency on `POST /v1/spaces` — no cross-tenant write is possible.
  - Backfill migration: the `INSERT ... SELECT` joins `spaces` to `company_memberships` strictly `ON cm.company_id = s.company_id`, so an admin can only ever be backfilled onto spaces inside their own company — no cross-tenant grant is possible by construction.
  - Cross-tenant access: none introduced.
  - Isolation tests to add: (1) creation-time grant test confirms the membership's `space_id`/implicit `company_id` match the creating user's active company; (2) migration backfill test confirms an admin of company A never receives a membership on a company B space, using two companies with orphaned spaces in the same test run.

No violations requiring justification — Complexity Tracking is not needed.

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

```text
db/migrations/versions/
└── 0013_backfill_space_memberships.py   # new: idempotent backfill, mirrors 0010's pattern

apps/api/tessera_api/
├── routers/spaces.py                    # create_space: add SpaceMembership(ADMIN) for creator after space creation
└── tests/
    ├── test_migration_0013_backfill_space_memberships.py  # new, real-DB, rolled back (mirrors test_migration_0010_backfill.py)
    └── unit/test_spaces_router.py       # extend (or create) with creation-grant test
```

**Structure Decision**: No new project or package. This is a two-file change
(`routers/spaces.py` + one new migration) within the existing `apps/api` +
`db/migrations` layout, following the exact precedent already set by
migration `0010` for this kind of "backfill missing access records" fix.

## Complexity Tracking

*No Constitution Check violations — this section is not applicable.*
