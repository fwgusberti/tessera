# Implementation Plan: Add User on the Company User Management Page

**Branch**: `054-add-company-user` | **Date**: 2026-07-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/054-add-company-user/spec.md`

## Summary

Turn the read-only user-management roster from feature 053 into a page where a
company **administrator of the active company** can add people two ways, each
carrying an admin-chosen company role (`administrator` or `member`, default
`member`):

1. **Invite by email** — creates a pending `Invitation` for the active company and
   sends the invite; the person becomes a member with the chosen role when they
   accept (extends the existing invitation flow).
2. **Direct add of an already-registered user** — the admin searches the global
   user directory, picks a user not yet in the company, and that user becomes a
   member immediately with the chosen role (no acceptance step).

All new write paths are gated by the existing `CompanyAdminContext` dependency and
derive `company_id` **solely** from the authenticated session/JWT (never from
client input), exactly as 053's `GET /companies/members` does. Three new endpoints
are added to the already-registered `companies` router:

- `GET  /v1/companies/addable-users?q=` — search registered users not already in the active company (name/email).
- `POST /v1/companies/members` — direct-add an existing user by `user_id` + role → immediate membership.
- `POST /v1/companies/invitations` — invite by `email` + role for the active company.

The **one schema change** this feature requires: the `invitations` table has no
role column today, but FR-004/FR-011 require an invited person to join with the
role the admin chose at invite time. Migration `0015` adds `invitations.role`
(default `member`) plus a partial unique index on `(company_id, lower(email))
WHERE status = 'pending'` to make the "already-invited" guard race-safe. The
invitation-acceptance path in `POST /companies/{id}/join` is updated to grant
`invitation.role` instead of the currently hard-coded `MEMBER`.

## Technical Context

**Language/Version**: Python 3.12 (apps/api, packages/core), TypeScript/Next.js App Router (apps/web) — no new languages.

**Primary Dependencies**: FastAPI + SQLAlchemy async (asyncpg) on the backend, reusing `CompanyAdminContext` (`tessera_api.auth.oidc.require_company_admin`), the existing `SqlInvitationRepository`, `SqlCompanyRepository`, `SqlUserRepository`, `send_invitation_email` helper, and `write_audit`; React/Tailwind on the frontend, reusing the `api` fetch client, `AuthGuard`, and `CompanyRoleBadge`.

**Storage**: PostgreSQL. Read: `users`, `company_memberships`. Write: `company_memberships` (direct add), `invitations` (invite). One migration (`0015`) adds `invitations.role` and a partial unique index for pending invitations. `company_memberships` already has `uq_company_membership (user_id, company_id)`.

**Testing**: pytest-anyio + `fastapi.testclient.TestClient` for `apps/api/tests/unit/test_company_add_user_router.py`; new cases in `apps/api/tests/test_tenant_isolation.py`; a core-package test (`pytest-asyncio`) for the invitation-role persistence and acceptance-grants-role behavior; Jest/RTL for `apps/web/tests/user-management-add.test.tsx`.

**Target Platform**: Linux server (existing Docker/Kubernetes deployment); modern web browsers.

**Performance Goals**: N/A beyond existing API norms — admin-triggered, infrequent writes and a small, debounced type-ahead search.

**Constraints**: Every new query/mutation MUST be scoped to the `company_id` resolved from `CompanyAdminContext` (Principle VI); non-admins get 403 and unauthenticated callers 401 before any write; the user-directory search returns identity fields only (never the target's other-company memberships) and requires a minimum query length to prevent directory enumeration.

**Scale/Scope**: A company roster and directory search are small (tens to low hundreds); a single scoped `SELECT ... LIMIT` for search and single-row inserts are sufficient. No pagination.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Domain-Driven Architecture** — PASS. Business rules are thin and boundary-enforced: "only an active-company admin may add users, scoped to that company" lives in the `CompanyAdminContext` dependency (same gate 053 uses); "may not add someone already a member" and "may not double-invite an email" are guard checks in the router mirroring the existing `POST /invitations` logic. Direct-add reuses `CompanyRepository.add_membership`; invite reuses `SqlInvitationRepository` + `send_invitation_email`. The domain gains only one field (`Invitation.role`) and one framework-free port method (`search_addable_users`) — no new service is warranted (mirrors how join-request approval writes a membership directly from the router).
- **II. Separation of Concerns** — PASS. The `CompanyRepository` port gains one abstract method (`search_addable_users`) expressed in domain terms; the `Invitation` domain model gains a `role: CompanyRole` field. No Postgres-specific detail leaks into ports or product definitions.
- **III. Data Locality & Consent** — N/A. No new client-side persistence introduced.
- **IV. Test-Driven Development (NON-NEGOTIABLE)** — PASS (plan). Each of: the migration-backed `Invitation.role` round-trip, `search_addable_users` (matches name/email, excludes current members, min-length), the three endpoint contracts (admin success / member 403 / unauth 401 / already-member / already-invited / no-such-user / malformed-email / send-failed), the acceptance-grants-`invitation.role` change, and the cross-tenant isolation cases get failing tests written first. Per the project test-env baseline, the API package's 85% statement-coverage gate sits below the repo's ~73% baseline and is not reachable by this feature alone; new code is fully covered and the suite is validated against the known baseline, not the absolute gate.
- **V. Quality Gates** — PASS (plan). Ruff/Black run as usual; no exemptions.
- **VI. Tenant Data Isolation (NON-NEGOTIABLE)** — PASS, with the explicit Tenant Isolation subsection below.

### Tenant Isolation

- **Tables accessed**:
  - `company_memberships` — read (`get_membership`, `list_members`) and write (`add_membership`), always filtered by the context `company_id`.
  - `invitations` — read (pending lookup) and write (create), always with the context `company_id`.
  - `users` — read only. Users are a **global identity table, not tenant-owned data**: a single user may belong to many companies, and a `user_id` carries no owning `company_id`. Searching it to find someone to add is inherent to the direct-add feature.
- **`company_id` scoping**: `company_id` is resolved by `require_company_admin` from the full-scoped JWT claim / active-company session and validated against a live `company_memberships` ADMIN lookup. It is **never** read from the request path or body. Every membership and invitation this feature creates uses that one `company_id`; the "already a member" and "already invited" guards query with it; and `add_membership` writes it — so an admin can only ever add someone into their own active company (FR-010, SC-003).
- **Directory-search exposure (documented cross-company read)**: `search_addable_users(company_id, query)` selects from the global `users` table, **excluding** users already in `company_id`, and returns **identity fields only** (`user_id`, `display_name`, `email`). It never returns which other companies a candidate belongs to, and it requires a minimum query length (≥ 2 chars) so it cannot be used to enumerate the directory. This is a read of shared identity data, not of another tenant's owned data; it creates no cross-tenant write path.
- **Cross-tenant isolation tests** (in `apps/api/tests/test_tenant_isolation.py`):
  - Admin authenticated for Company A calls `POST /companies/members` for a user; the resulting membership is created in Company A only, never in Company B (verified via `get_membership` on both).
  - A user who is already a member of Company B (but not A) can still be direct-added to A, and the write lands only in A.
  - `GET /companies/addable-users` run as Company A's admin returns only identity fields and excludes A's current members; the response body cannot reveal B's roster.
  - Endpoint contract: a non-admin member of the active company gets 403 (no write) and an unauthenticated caller 401 for all three endpoints (SC-004).

## Project Structure

### Documentation (this feature)

```text
specs/054-add-company-user/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── add-users-endpoints.md
│   └── invitation-acceptance-change.md
├── checklists/          # (pre-existing)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
db/migrations/versions/
└── 0015_invitation_role.py                 # new: add invitations.role (default 'member')
                                            #      + partial unique index on pending (company_id, lower(email))

packages/core/tessera_core/
├── domain/invitation.py                    # + role: CompanyRole = CompanyRole.MEMBER
└── ports/repositories/company.py           # + search_addable_users() abstract method

apps/api/tessera_api/
├── adapters/models/invitation.py           # + role mapped_column (String(20), default "member")
├── adapters/repositories/invitation.py     # persist/read role in create + create_bulk + _invitation_from_model
├── adapters/repositories/company.py        # + search_addable_users() (users ⋈ NOT in company_memberships)
├── routers/companies.py                    # + GET  /companies/addable-users
│                                           # + POST /companies/members        (direct add, CompanyAdminContext)
│                                           # + POST /companies/invitations     (invite by email + role)
│                                           # ~ POST /companies/{id}/join: grant invitation.role on acceptance
└── tests/
    ├── unit/test_company_add_user_router.py    # new: all endpoint contracts + outcomes
    └── test_tenant_isolation.py                # + add-user cross-company isolation cases

apps/web/
├── lib/companies.ts                        # + searchAddableUsers(), addCompanyMember(), inviteCompanyMember() + types
├── components/company/AddUserPanel.tsx     # new: add-by-email | add-existing toggle, role select, outcome messaging
├── app/users/page.tsx                      # + admin-only "Add user" affordance; append new member to roster on success
└── tests/user-management-add.test.tsx      # new
```

**Structure Decision**: The existing three-package layout (`packages/core` domain/ports, `apps/api` FastAPI adapters/routers, `apps/web` Next.js) is unchanged. This feature adds one domain field, one port method + adapter query, one small migration, three endpoints on the existing `companies` router, and one frontend panel + roster wiring — following the admin-gated, active-company-scoped pattern established by 053 and the invitation/membership write patterns already present in `routers/companies.py` and `routers/invitations.py`.

## Complexity Tracking

*No constitution violations — section left empty.*

## Post-Design Constitution Re-check

Re-evaluated after Phase 1 (data-model.md, contracts/, quickstart.md): no new
violations. The final design keeps all writes in the `apps/api` adapters, the
admin gate in the existing `CompanyAdminContext` boundary dependency, and derives
`company_id` solely from the authenticated context. The only domain additions are
a framework-free `Invitation.role` field and one `search_addable_users` port
method. The single cross-company read (global user directory) is documented,
identity-only, min-length-gated, and creates no cross-tenant write. All gates
still PASS.
