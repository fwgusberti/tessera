# Implementation Plan: Add Space Membership (Frontend)

**Branch**: `043-add-space-membership` | **Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/043-add-space-membership/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Replace the raw-user-ID "Invite Member" form on the Space Members page with a
searchable "Add Member" flow: a space admin types a name/email fragment, the
frontend queries a new, space-admin-scoped company-member search endpoint,
the admin picks a non-member from the results and a role, and the existing
`POST /v1/spaces/{id}/members` call adds them. The only new backend surface is
the search endpoint (`GET /v1/spaces/{id}/members/search`) and its repository
support; the add/remove/role-change endpoints are reused unchanged.

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript 5 / React 19 (web)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 (async), Pydantic 2 (API); Next.js 15, React 19 (web)

**Storage**: PostgreSQL (existing `users`, `company_memberships`, `space_memberships` tables — no schema change required)

**Testing**: pytest + pytest-asyncio/anyio (API, `apps/api/tests`), vitest + Testing Library (web, `apps/web/tests`)

**Target Platform**: Linux server (API container), browser (Next.js web app)

**Project Type**: Web application (existing `apps/api` + `apps/web` monorepo split)

**Performance Goals**: Search results returned within 1s under normal load (SC-002); debounced client-side queries, indexed `ILIKE` lookup capped to a small result page (20) server-side

**Constraints**: Search endpoint MUST be authorized per-space (caller must be admin of the target space or company admin — same rule as `can_manage_members`), MUST exclude existing space members, MUST NOT return results for fewer than 2 query characters

**Scale/Scope**: One new backend endpoint + one new repository query, one new frontend component (`AddMemberForm`) replacing `InviteMemberForm`, no new tables/migrations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Domain-Driven Architecture**: The new search capability is exposed as a method on the existing `SpaceMembershipRepository`/`CompanyRepository` ports (domain layer), implemented in the SQL adapter. The router calls the existing `can_manage_members` domain permission function — no framework code leaks into `tessera_core`. ✅ PASS
- **II. Separation of Concerns**: `spec.md` describes the feature with no tech references; this plan carries all technology decisions. ✅ PASS
- **III. Data Locality & Consent**: No new client-side persistence is introduced; search results are held in component state only, discarded on unmount. ✅ PASS (N/A)
- **IV. Test-Driven Development**: New repository method, router endpoint, and `AddMemberForm` component will each get a failing test written first (unit tests for the search query/authorization, component tests for the picker states). ✅ PASS (enforced in Tasks)
- **V. Quality Gates**: Ruff/Black (API) and existing lint/typecheck (web) run as part of task completion, consistent with prior features. ✅ PASS
- **VI. Tenant Data Isolation (NON-NEGOTIABLE)** — **Tenant Isolation section**:
  - Tables accessed: `space_memberships` (existing, already `space_id`-scoped via space→company relationship), `company_memberships` + `users` (new read path, scoped by `company_id` from `CompanyMemberContext`).
  - The new search query filters `company_memberships.company_id = :company_id` (from the authenticated session's active company) joined to `users`, then excludes user IDs already present in `space_memberships` for the target `space_id`. No bare entity ID is accepted without the session-derived `company_id`.
  - The target `space_id` is additionally validated against the active company via the existing `validate_space_for_company` helper before any search executes (mirrors `list_members`), so a space ID from another company 404s instead of leaking membership data.
  - Cross-tenant access: none introduced; this is a same-company, same-space read gated by the existing space-admin permission check.
  - Isolation tests to add: (1) a company-A admin searching against a space that belongs to company B gets 404; (2) search results never include users whose only company membership is in a different company than the caller's active company.

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
packages/core/tessera_core/
├── ports/repositories/company.py        # add list_members(company_id, query, limit) to CompanyRepository port
└── domain/                              # CompanyMember(ish) read model lives here if needed (likely reuses User + CompanyMembership)

apps/api/tessera_api/
├── adapters/repositories/company.py     # implement search query (join company_memberships + users, ILIKE, exclude space members)
├── routers/members.py                   # add GET /spaces/{space_id}/members/search, reuse can_manage_members check
└── tests/unit/
    ├── test_members_router.py           # new tests for the search endpoint (auth, exclusion, isolation)
    └── ...

apps/web/
├── components/members/
│   ├── AddMemberForm.tsx                # new: replaces InviteMemberForm.tsx in SpaceMembersPanel
│   └── SpaceMembersPanel.tsx            # swap InviteMemberForm -> AddMemberForm
└── tests/
    └── add-member-form.test.tsx         # new component tests
```

**Structure Decision**: Existing web application split (`apps/api` FastAPI service +
`apps/web` Next.js app, shared domain in `packages/core`) is reused as-is. No new
top-level project or package is introduced — this feature only adds one repository
method, one router endpoint, and one frontend component within the existing
`spaces`/`members` vertical slice.

## Complexity Tracking

*No Constitution Check violations — this section is not applicable.*
