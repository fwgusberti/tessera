# Implementation Plan: Space Access Management for Company Members

**Branch**: `058-member-space-access` | **Date**: 2026-07-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/058-member-space-access/spec.md`

## Summary

A person added to a company (direct add, invitation, or email-domain match) has
zero space memberships, so `GET /v1/spaces` returns nothing and the UI shows a
misleading "No spaces available in your company." Administrators have no
member-centric way to grant space access — the only path is the per-space
"Members" link, and company admins can't even see spaces they don't personally
belong to because `list_spaces` is membership-only.

**Technical approach**: The permission layer already grants company admins
implicit `SpaceRole.ADMIN` on every space of their company
(`effective_space_role(..., is_company_admin=True)` — feature 036), so the
existing per-space member endpoints (`POST/PUT/DELETE /v1/spaces/{id}/members…`)
already authorize the grant/change/revoke operations correctly. What's missing
is **visibility** and a **member-centric surface**:

1. **Admin-wide space listing** — `GET /v1/spaces`, `GET /v1/spaces/{id}` and
   `GET /v1/spaces/{id}/ancestors` gain a company-admin path that includes every
   space of the active company (implicit admin role), not just membership-derived
   ones. Implemented in the core `SpaceHierarchyService` behind the existing
   `list_by_company` port method.
2. **Member-centric access read model** — new admin-gated endpoint
   `GET /v1/companies/members/{user_id}/space-access` returns every space of the
   company annotated with the target member's direct role / effective role /
   none. Assembled in a new core `MemberAccessService` from existing port
   methods (`list_by_company`, `list_accessible_by_user`, `list_by_user`).
3. **UI** — the Users page (`/users`) gets a per-row "Spaces" action opening a
   `MemberSpaceAccessPanel` that lists all company spaces with the member's
   current access and lets the admin grant (role select), change role, and
   revoke, calling the existing per-space member endpoints.
4. **Empty state fix** — the Spaces page distinguishes "no spaces shared with
   you yet — ask a company administrator" (member of a company, zero accesses)
   from a company that genuinely has no spaces (admins, who now see all spaces).

No schema changes; `space_memberships` is reused as-is.

## Technical Context

**Language/Version**: Python 3.12 (FastAPI) for the API and `tessera_core`
domain package; TypeScript 5 (Next.js 15 App Router, React 19) for the web app.

**Primary Dependencies**: FastAPI, SQLAlchemy async, joserfc (api); Next.js,
React, Tailwind CSS (web). No new dependencies introduced.

**Storage**: PostgreSQL (system of record). **No schema changes** — reuses
`spaces`, `space_memberships`, `company_memberships`, `users`, `audit_log`.

**Testing**: pytest-asyncio (`@pytest.mark.asyncio`) for `packages/core`;
pytest + anyio (`@pytest.mark.anyio`) with unit tests patching module-level
router imports and integration tests via `fastapi.testclient.TestClient` for
`apps/api`; Vitest + Testing Library for `apps/web`.

**Target Platform**: Linux-hosted API (Docker/K8s); modern browsers, desktop
and mobile viewports.

**Project Type**: Web application — monorepo with `apps/api` (FastAPI),
`apps/web` (Next.js), `packages/core` (framework-free domain).

**Performance Goals**: Member space-access view assembles from three indexed
queries (spaces by company, memberships by user, recursive-CTE access) — no
N+1; company-scale (tens of spaces, hundreds of members) renders in one
round-trip.

**Constraints**: Least-privilege default preserved (company membership grants
no space access). Admin-wide visibility applies to company admins only.
All new queries tenant-scoped by `company_id` (Constitution VI).

**Scale/Scope**: 2 modified + 1 new API endpoints, 1 new core service, 1 core
service extension, 1 new web panel component + Users page wiring + Spaces page
empty-state change. No migrations.

## Constitution Check

*GATE: evaluated against Constitution v1.4.0 — PASS (initial and post-design).*

**I. Domain-Driven Architecture — PASS.** Access-assembly logic (which spaces,
which effective role, admin-wide listing) lives in `tessera_core` services
(`MemberAccessService`, `SpaceHierarchyService`) against repository ports;
routers stay thin adapters. No framework imports enter the domain.

**II. Separation of Concerns — PASS.** New behavior expressed via existing
ports (`SpaceRepository`, `SpaceMembershipRepository`); no storage or transport
details leak into domain definitions.

**III. Data Locality & Consent — PASS.** No client-side persistence introduced.

**IV. TDD (non-negotiable) — PASS.** Core services written test-first in
`packages/core/tests/`; router behavior covered by API unit + integration
tests; web panel covered by Vitest. Note: repository-wide 85% API coverage gate
is currently unreachable (~73% pre-existing baseline); new/changed modules
themselves must be fully covered (see research.md → Test Environment Baseline).

**V. Quality Gates — PASS.** Ruff + Black on Python; existing lint setup on web.

**VI. Tenant Data Isolation (non-negotiable) — PASS.** See dedicated section
below.

**Audit logging — PASS.** Grant/change/revoke reuse `MembershipService`
(`member_invited`, `member_role_changed`, `member_removed` audit records) —
no new state-changing paths are added, so no new audit writes are needed; the
new endpoint is read-only.

### Tenant Isolation (required section)

**Tables accessed**: `spaces`, `space_memberships`, `company_memberships`,
`users` (read); `space_memberships` + `audit_log` (write, via existing
endpoints only).

**Scoping guarantees**:

- `GET /v1/companies/members/{user_id}/space-access`: caller resolved via
  `CompanyAdminContext` (company from authenticated session). Target user is
  validated as a member of the caller's active company before any space data is
  read; a non-member / cross-company `user_id` returns a generic 404
  (indistinguishable from absent, matching feature 053/054 convention). Space
  queries use `list_by_company(company_id)` and
  `list_accessible_by_user(user_id, company_id)` — both already scoped.
- Admin-wide space listing: the company-admin branch uses
  `list_by_company(company_id)` with `company_id` from session context only.
  `is_company_admin` is derived from the caller's `company_memberships` row for
  the active company (existing `CompanyMemberContext`), never from input.
- Grant/change/revoke reuse existing endpoints which validate
  `validate_space_for_company` / `_require_space_in_company` and audit
  cross-tenant probes (`cross_tenant_denied`).

**Isolation tests to write** (in `apps/api/tests/test_tenant_isolation.py` or
feature integration tests):

1. Company A admin requests space-access of a Company B member → 404, no data.
2. Company A admin's space listing never contains Company B spaces (even as
   admin-wide listing).
3. Company A admin cannot grant a Company A member access to a Company B space
   (existing test, re-affirmed) and cannot grant a Company B user access to a
   Company A space (search + POST both refuse).
4. Non-admin Company A member calling the new endpoint → 403.

## Project Structure

### Documentation (this feature)

```text
specs/058-member-space-access/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── member-space-access.md   # New + modified endpoint contracts
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
packages/core/
├── tessera_core/
│   ├── domain/
│   │   └── member_space_access.py        # NEW: MemberSpaceAccess read model
│   ├── services/
│   │   ├── member_access.py              # NEW: MemberAccessService
│   │   └── space_hierarchy.py            # MODIFIED: company-admin listing path
│   └── ports/repositories/space.py       # unchanged (reuses list_by_company)
└── tests/
    ├── test_member_access_service.py     # NEW (pytest-asyncio)
    └── test_space_hierarchy_admin.py     # NEW (pytest-asyncio)

apps/api/
├── tessera_api/routers/
│   ├── companies.py                      # MODIFIED: GET /companies/members/{user_id}/space-access
│   └── spaces.py                         # MODIFIED: admin-wide list/get/ancestors
└── tests/
    ├── unit/test_member_space_access_router.py   # NEW (patched module-level imports)
    ├── integration/test_member_space_access.py   # NEW (TestClient, anyio)
    ├── integration/test_admin_space_visibility.py# NEW
    └── test_tenant_isolation.py                  # MODIFIED: new isolation cases

apps/web/
├── app/users/page.tsx                    # MODIFIED: per-row "Spaces" action
├── app/spaces/page.tsx                   # MODIFIED: honest empty state
├── components/members/
│   └── MemberSpaceAccessPanel.tsx        # NEW: grant/change/revoke panel
├── lib/members.ts                        # NEW: getMemberSpaceAccess + space-member calls
└── tests/
    ├── member-space-access-panel.test.tsx # NEW (Vitest)
    └── spaces-empty-state.test.tsx        # NEW (Vitest)
```

**Structure Decision**: Existing monorepo layout — domain logic in
`packages/core`, HTTP adapters in `apps/api`, UI in `apps/web`. No new
packages, no migrations.

## Design Decisions (summary — details in research.md)

1. **Reuse per-space member endpoints for writes.** Company admins already pass
   `can_manage_members` on any company space (implicit admin, feature 036), so
   the new panel calls `POST /v1/spaces/{id}/members`,
   `PUT/DELETE /v1/spaces/{id}/members/{user_id}` — one authoritative write
   path, both views stay consistent (FR-011).
2. **One new read endpoint** (`GET /v1/companies/members/{user_id}/space-access`)
   instead of client-side joins across N spaces — avoids N+1 HTTP calls and
   keeps tenant validation server-side.
3. **Admin-wide visibility implemented in `GET /v1/spaces` itself** (plus
   `get_space` / `ancestors`), not a separate "admin spaces" endpoint — the
   Spaces page, FolderTile "Members" links, and SetParent/Delete flows all
   inherit full visibility with zero extra UI work (FR-005). Spaces the admin
   doesn't belong to are returned with `effective_role: "admin"` (implicit),
   `is_direct: false`.
4. **`list_spaces` switches `CompanyContext` → `CompanyMemberContext`** to know
   whether the caller is a company admin; non-admin behavior is unchanged.
5. **Empty-state copy decided client-side**: after (3), a non-admin with zero
   accesses sees "No spaces have been shared with you yet…"; an admin with an
   empty list means the company truly has no spaces (existing copy + Add Space).
6. **No auto-grant on company join** (spec assumption): least privilege stands.

## Complexity Tracking

No constitution violations — table intentionally empty.
