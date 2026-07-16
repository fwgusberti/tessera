# Implementation Plan: Human-Readable Member Identity in User Management

**Branch**: `065-fix-member-display` | **Date**: 2026-07-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/065-fix-member-display/spec.md`

## Summary

`GET /v1/spaces/{space_id}/members` returns bare `SpaceMembership` dumps
(`user_id`, `role`, timestamps — no name, no email), so the space members
panel (`apps/web/components/members/SpaceMembersPanel.tsx:87`) falls back to
rendering the raw `user_id` UUID and shows no email line. Fix by enriching the
endpoint with each member's `display_name` and `email` via a single SQL JOIN
to the `users` table — mirroring the existing company-members precedent
(`CompanyMemberListing` + `SqlCompanyRepository.list_members`) — and by
hardening the frontend label fallback chain to
`display_name → email → "Unknown user"` (never a UUID) across all
member-listing surfaces. Additive API change, no schema migration.
Technical decisions in [research.md](./research.md).

## Technical Context

**Language/Version**: Backend: Python 3.12 (apps/api, packages/core). Frontend: TypeScript 5 / React 19.1 / Next.js 15.5 App Router (apps/web)

**Primary Dependencies**: FastAPI ≥0.115, SQLAlchemy 2 (async), Pydantic 2 (backend); Tailwind CSS 4, existing `api` client wrapper (frontend). No new dependencies.

**Storage**: PostgreSQL — read-only JOIN across existing tables `space_memberships`, `users`, `spaces`. No migrations, no new tables or columns.

**Testing**: API: pytest + anyio markers + `fastapi.testclient.TestClient` (integration/contract suites at `apps/api/tests/`). Core: pytest (+ pytest-asyncio where async). Web: Vitest 2 + @testing-library/react (extends `apps/web/tests/members.test.tsx`).

**Target Platform**: Linux server (API), modern browsers via Next.js (web)

**Project Type**: Web application — monorepo with `apps/api` (FastAPI), `apps/web` (Next.js), `packages/core` (domain)

**Performance Goals**: Members list served in one JOIN query (replaces the current memberships-only query — no N+1); no additional frontend requests

**Constraints**: Additive response change only (existing membership fields preserved) so mutation endpoints and other consumers keep working; new repository read path MUST be tenant-scoped per Constitution VI; raw identifiers must never render as a person's label

**Scale/Scope**: Member lists are small (tens of rows per space). Scope: 1 domain value object, 1 port method, 1 repository method, 1 router change, 2–3 frontend files, 3 test files touched.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | ✅ Pass | New `SpaceMemberListing` value object lives in `packages/core/tessera_core/domain/` (no framework imports, mirrors `CompanyMemberListing`); the abstract port method goes on `tessera_core.ports.repositories.space_membership.SpaceMembershipRepository`; SQL JOIN lives in the adapter (`apps/api/.../repositories/space_membership.py`). |
| II. Separation of Concerns | ✅ Pass | Spec stays technology-agnostic; all technical decisions live here and in research.md. Domain/port change is persistence-agnostic. |
| III. Data Locality & Consent | ✅ Pass | No client-side persistence introduced. |
| IV. Test-Driven Development | ✅ Pass | Tests written first at all three layers: core value-object test, API integration/contract tests (identity fields, ordering, isolation), web component tests (fallback chain, no-UUID assertion). Coverage note: the API package's 85% gate is unreachable at its ~73% pre-existing baseline; validation follows the established baseline procedure (run targeted suites, assert zero new failures) while new code itself ships fully covered. |
| V. Quality Gates | ✅ Pass | Ruff + Black on all touched Python; existing ESLint/TS config for web. |
| VI. Tenant Data Isolation | ✅ Pass | New read path is company-scoped; see Tenant Isolation below. |

### Tenant Isolation

- **Tables accessed** (all read-only in the new path):
  `space_memberships` (rows for the space), `users` (display_name, email via
  JOIN), `spaces` (JOIN target used to enforce the company scope).
- **`company_id` scoping**: the new repository method
  `list_by_space_with_identity(space_id, company_id)` requires `company_id`
  and enforces it inside the query with a JOIN on
  `spaces.id = space_memberships.space_id AND spaces.company_id = :company_id`
  — it does not rely solely on the route's upstream
  `validate_space_for_company` check (defense in depth; satisfies the "no bare
  entity ID without company_id" rule, which the legacy `list_by_space` method
  predates). `company_id` is derived from the authenticated
  `CompanyMemberContext` at the route boundary and passed down unchanged.
- **Identity exposure audience is unchanged (FR-007)**: the endpoint keeps its
  existing authorization (`can_read_space_document` — caller must be a member
  of the space or a company admin), and the same audience can already see
  these users' names/emails via `GET /v1/companies/members` and
  `GET /v1/spaces/{id}/members/search`. No new audience is granted.
- **Cross-tenant isolation tests** (written first):
  1. Company A admin requests `GET /v1/spaces/{B_space_id}/members` →
     generic 404, response body contains no member identity of Company B
     (extends existing pattern in `apps/api/tests/integration/test_members.py`).
  2. Repository-level test: `list_by_space_with_identity(space_id,
     wrong_company_id)` returns an empty list even though the space has
     members.

**Gate result (pre-Phase 0)**: PASS — no violations, Complexity Tracking not needed.

**Gate re-check (post-Phase 1 design)**: PASS — design artifacts add one
tenant-scoped read method, one additive response change, and frontend label
logic; no new endpoints, tables, migrations, or client persistence.

## Project Structure

### Documentation (this feature)

```text
specs/065-fix-member-display/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── space-members-api.md   # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
packages/core/
├── tessera_core/
│   ├── domain/
│   │   └── space_member_listing.py        # NEW: value object (membership + identity)
│   └── ports/repositories/
│       └── space_membership.py            # MODIFIED: add list_by_space_with_identity()
└── tests/
    └── test_space_member_listing.py       # NEW: value-object test (mirrors test_company_member_listing.py)

apps/api/
├── tessera_api/
│   ├── adapters/repositories/
│   │   └── space_membership.py            # MODIFIED: SQL impl (JOIN users + spaces, ORDER BY display_name)
│   └── routers/
│       └── members.py                     # MODIFIED: list_members returns identity-enriched rows
└── tests/
    ├── integration/test_members.py        # MODIFIED: identity fields, ordering, isolation tests
    └── contract/test_members.py           # MODIFIED: response-shape contract for enriched list

apps/web/
├── components/members/
│   └── SpaceMembersPanel.tsx              # MODIFIED: label fallback chain, email line, truncation; drop user_id fallback
├── app/users/page.tsx                     # MODIFIED (sweep): add "Unknown user" terminal fallback
├── components/members/AddMemberForm.tsx   # MODIFIED (sweep): same fallback for search-result labels
└── tests/
    └── members.test.tsx                   # MODIFIED: fallback chain, no-UUID-rendered, actions still target user_id
```

**Structure Decision**: Existing monorepo layout (web application). The fix
follows the codebase's DDD split: value object + port in `packages/core`,
SQL adapter + router in `apps/api`, presentation in `apps/web`. No new
projects or directories beyond one domain file and one core test file.

## Complexity Tracking

> No constitution violations — table intentionally left empty.
