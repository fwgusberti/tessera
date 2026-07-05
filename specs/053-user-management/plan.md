# Implementation Plan: Company User Management Page

**Branch**: `053-user-management` | **Date**: 2026-07-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/053-user-management/spec.md`

## Summary

Add a read-only "User Management" page for company administrators that lists every member of the admin's **active company** together with that member's company role (`administrator` or `member`). The page is backed by a single new endpoint, `GET /v1/companies/members`, gated by the existing `CompanyAdminContext` dependency (full-scoped token + active-company admin). The company is derived entirely from the authenticated session/JWT — never from client input — so tenant scoping is structural. The endpoint returns the joined `company_memberships × users` rows for that one company via a new `CompanyRepository.list_members()` method. No schema migration, no new service, and no write paths: this mirrors how `GET /v1/companies/{id}/join-requests` already reads admin-only company data (router → `_require_company_admin` → repository), and reuses the same join shape already proven in `SqlCompanyRepository.search_members_for_space`.

## Technical Context

**Language/Version**: Python 3.12 (apps/api, packages/core), TypeScript/Next.js App Router (apps/web) — no new languages.

**Primary Dependencies**: FastAPI + SQLAlchemy async (asyncpg) on the backend, reusing the existing `CompanyAdminContext` auth dependency (`tessera_api.auth.oidc.require_company_admin`); React/Tailwind on the frontend, reusing the existing `api` fetch client and `AuthGuard`.

**Storage**: PostgreSQL — existing tables `company_memberships` (read) joined to `users` (read). No schema migration: both tables already exist and the join is identical in shape to `search_members_for_space`.

**Testing**: pytest-anyio + `fastapi.testclient.TestClient` for `apps/api/tests/unit/test_company_members_router.py` and a cross-tenant case in `apps/api/tests/test_tenant_isolation.py`; Jest/RTL for `apps/web/tests/user-management.test.tsx`.

**Target Platform**: Linux server (existing Docker/Kubernetes deployment); modern web browsers.

**Performance Goals**: N/A beyond existing API norms — an admin-triggered, infrequent read of a single company's roster.

**Constraints**: The member query MUST be scoped to the `company_id` resolved from the authenticated context (Principle VI); the endpoint MUST reject non-admins (403) and unauthenticated callers (401) before returning any roster data.

**Scale/Scope**: A company roster is small (tens to low hundreds of members) for the current scale; a single joined `SELECT` ordered by display name is sufficient — no pagination in this first version (spec explicitly defers very-large-list handling).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Domain-Driven Architecture** — PASS. The only rule this feature carries is "company admin may read the active company's roster," enforced at the request boundary by the existing `CompanyAdminContext` dependency — the same boundary-level admin gate used by the join-request read endpoints. The SQL join stays entirely in `SqlCompanyRepository.list_members()` (apps/api adapter); the domain layer gains only a framework-free value object (`CompanyMemberListing`) to carry a member row. No new domain service is warranted for a gated read (mirrors `list_join_requests`, which goes router → repo directly).
- **II. Separation of Concerns** — PASS. The `CompanyRepository` port gains one abstract method (`list_members`) expressed in domain terms; no Postgres-specific detail leaks into the port or any product definition.
- **III. Data Locality & Consent** — N/A. No new client-side persistence introduced.
- **IV. Test-Driven Development** — PASS (plan). The repository method, the endpoint contract (admin 200 / member 403 / unauthenticated 401), and the cross-tenant isolation case each get failing tests written first, following the `TestSearchMembersContract` structure in `apps/api/tests/unit/test_members_router.py` and the harness in `apps/api/tests/test_tenant_isolation.py`. Note (per the project test-env baseline): the API package's 85% statement-coverage gate sits below the repo's ~73% baseline and is not reachable by this feature in isolation; new code is fully covered, and the suite is validated against the known baseline rather than the absolute gate.
- **V. Quality Gates** — PASS (plan). Ruff/Black run as usual; no exemptions needed.
- **VI. Tenant Data Isolation (NON-NEGOTIABLE)** — PASS, with explicit Tenant Isolation subsection below.

### Tenant Isolation

- **Tables accessed**: `company_memberships` (read) joined to `users` (read). No writes.
- **`company_id` scoping**: The `company_id` is resolved by `require_company_admin` from the full-scoped JWT claim (or session `active_company_id`) and validated against a live `company_memberships` lookup that also confirms the caller is an `ADMIN`. It is **never** taken from the request path or body. `SqlCompanyRepository.list_members(company_id)` filters `CompanyMembershipModel.company_id == company_id` on the join, so only the active company's rows are ever selected. A member who belongs solely to another company cannot appear.
- **Cross-tenant isolation tests**: A new case in `apps/api/tests/test_tenant_isolation.py` — an admin authenticated for Company A calls `GET /v1/companies/members` and receives exactly Company A's members; a member who belongs only to Company B never appears in the result, even when that member's user record exists. Plus the endpoint contract test asserting a non-admin member of the active company receives 403 (no roster leaked) and an unauthenticated caller receives 401.

## Project Structure

### Documentation (this feature)

```text
specs/053-user-management/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
packages/core/tessera_core/
├── domain/company_member_listing.py     # new: CompanyMemberListing value object (user_id, display_name, email, role)
├── domain/entities.py                   # + re-export CompanyMemberListing
└── ports/repositories/company.py        # + list_members() abstract method

apps/api/tessera_api/
├── routers/companies.py                 # + GET /companies/members (CompanyAdminContext-gated)
├── adapters/repositories/company.py     # + list_members() (company_memberships ⋈ users, ordered)
└── tests/
    ├── unit/test_company_members_router.py   # new: admin 200 / member 403 / unauth 401
    └── test_tenant_isolation.py              # + cross-company roster isolation case

apps/web/
├── lib/companies.ts                     # + getCompanyMembers() + CompanyMember type
├── components/company/CompanyRoleBadge.tsx   # new: admin/member badge (indigo/slate)
├── app/users/page.tsx                   # new: User Management page (AuthGuard-wrapped)
├── components/NavBar.tsx                # + "Users" link (desktop + mobile)
└── tests/user-management.test.tsx       # new
```

**Structure Decision**: Existing three-package layout (`packages/core` domain/ports, `apps/api` FastAPI adapters/routers, `apps/web` Next.js) is unchanged. This feature adds one port method, one repository method, one endpoint on the already-registered `companies` router, one domain value object, and one new frontend page + small badge component — following the read-only, admin-gated pattern established by the company join-request endpoints and the frontend table pattern in `SpaceMembersPanel`.

## Complexity Tracking

*No constitution violations — section left empty.*

## Post-Design Constitution Re-check

Re-evaluated after Phase 1 (data-model.md, contracts/, quickstart.md): no new
violations. The final design keeps the SQL join entirely in `SqlCompanyRepository`
(adapter), the admin gate in the existing `CompanyAdminContext` boundary
dependency, and adds only a framework-free `CompanyMemberListing` value object to
the domain. `company_id` is sourced solely from the authenticated context. All
gates still PASS.
