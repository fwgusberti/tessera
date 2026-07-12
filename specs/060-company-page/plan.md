# Implementation Plan: Company Page

**Branch**: `060-company-page` | **Date**: 2026-07-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/060-company-page/spec.md`

## Summary

Members need a dedicated page showing their active company's profile (name,
industry, team size, creation date), with in-place editing for company admins.
Today the API exposes **no endpoint to read or update the active company's
details** (`GET /v1/companies/me` returns only id/name/role entries), and the
web app ships a placeholder at `/settings/company` ("Full company settings are
coming soon") that is already linked from the company menu.

**Technical approach** (full-stack, small):

1. **Backend — two new endpoints on the existing companies router**
   (`apps/api/tessera_api/routers/companies.py`):
   - `GET /v1/companies/current` — any active-company member
     (`CompanyMemberContext`); returns id, name, industry, team_size,
     created_at, plus the caller's role so the client can decide whether to
     offer edit controls.
   - `PATCH /v1/companies/current` — admin only (`CompanyAdminContext`);
     updates name/industry/team_size with the same validation rules as
     `POST /v1/companies` (name 1–255, industry ≤100, team_size ∈
     `VALID_TEAM_SIZES`), writes a `company.updated` audit record with the
     changed fields, returns the updated profile. Last-write-wins (per spec
     assumption).
   - The company is addressed as the singleton `current`, derived exclusively
     from the authenticated company context — no company id in the URL, so
     cross-tenant addressing is impossible by construction (Principle VI,
     FR-009).
2. **Repository** — add `update_details(company_id, *, name, industry,
   team_size) -> Company | None` to the `CompanyRepository` port
   (`packages/core`) and its SQL adapter (`apps/api`). Scoped
   `WHERE id = :company_id`; returns `None` when the row doesn't exist.
3. **Web — replace the `/settings/company` placeholder** with the real page:
   read-only profile card for every member (with explicit "Not provided" for
   empty optional fields, FR-003), Edit/Save/Cancel flow for admins reusing
   the onboarding form's INDUSTRIES/TEAM_SIZES option sets (extracted to a
   shared module). After a successful save, `reloadCompanies()` from the
   existing `CompanyProvider` refreshes the company menu so the new name shows
   everywhere immediately (FR-007). The `CompanyMenu` link to
   `/settings/company` is currently admin-gated — un-gate it and relabel
   "Company" so every member can reach the page (FR-001, SC-001).

No schema changes, no migrations (`companies` already has `industry`,
`team_size`, `created_at`, `updated_at`), no new dependencies.

## Technical Context

**Language/Version**: Python 3.12 (FastAPI backend `apps/api`, domain package
`packages/core`); TypeScript 5 / Next.js 15 (App Router) / React 19
(`apps/web`).

**Primary Dependencies**: FastAPI, SQLAlchemy (async) + Pydantic v2 on the
backend; Next.js, React, Tailwind CSS on the web. No new dependencies.

**Storage**: PostgreSQL — existing `companies` table only. No migrations: all
displayed/edited columns (`name`, `industry`, `team_size`, `created_at`,
`updated_at`) already exist; audit records go to the existing audit table via
`write_audit`.

**Testing**: pytest for `apps/api` (unit + integration; async tests use the
**anyio** marker; integration tests use sync `fastapi.testclient.TestClient`);
pytest-asyncio conventions for `packages/core` (only if core tests are
touched); Vitest + Testing Library (jsdom) in `apps/web/tests/`. TDD: tests
written first per Constitution IV.

**Target Platform**: Linux server (API), modern browsers desktop + mobile
(web).

**Project Type**: Web application — monorepo (`apps/api`, `apps/web`,
`packages/core`).

**Performance Goals**: Page renders after one fetch
(`GET /v1/companies/current`); save is one `PATCH` round-trip (SC-001/SC-002
human-time budgets are comfortably met by single-request flows).

**Constraints**: Tenant isolation by construction — company id is never
accepted from the client (Principle VI). Non-admin PATCH must return 403 with
data unchanged (FR-008, SC-003). Failed saves must not clear the admin's
entered values (edge case). Last-write-wins concurrency; no locking.

**Scale/Scope**: 2 new endpoints, 1 port method + 1 adapter method, 1 rebuilt
page, 1–2 new components, 1 shared-options module, ~2 modified web modules,
~4 new/extended test suites. Zero migrations.

## Constitution Check

*GATE: evaluated against Constitution v1.4.0 — PASS (initial and
post-design).*

**I. Domain-Driven Architecture — PASS.** The only domain-layer change is a
new abstract method on the `CompanyRepository` port; the `Company` domain
model already carries every field involved. Domain code gains no framework,
transport, or persistence imports.

**II. Separation of Concerns — PASS.** Validation limits live at the API
boundary (mirroring `POST /v1/companies`); persistence details stay in the
SQL adapter; the spec remains technology-agnostic.

**III. Data Locality & Consent — PASS.** No new client-side persistence. The
page reads via the existing authenticated API; form state is in-memory React
state only.

**IV. TDD (non-negotiable) — PASS.** All behavior written test-first: failing
API unit tests (router happy paths, 403 non-admin, 422 validation, audit
write), repository tests, integration + isolation tests, and Vitest suites
(view, not-provided rendering, edit/save/cancel, non-admin read-only, save
failure preserves input). 85% statement coverage applies to the Python
modules touched; note the pre-existing repo-wide coverage baseline is tracked
separately (see quickstart for how to validate this feature without false
alarms).

**V. Quality Gates — PASS.** Ruff + Black on all Python changes; existing
ESLint/TS strictness on web changes.

**VI. Tenant Data Isolation (non-negotiable) — PASS.** See dedicated section
below.

**Audit logging — PASS.** The single state-changing action
(`PATCH /v1/companies/current`) writes a `company.updated` audit record with
actor id, timestamp (audit table default), affected company id, and a
changed-fields metadata map (FR-010, SC-004). Reads are not state-changing.

**UI Design System — PASS.** Page uses `slate-*` neutrals, `indigo-600/700`
actions, `red-*` errors, existing Geist typography — same vocabulary as the
Users page and onboarding CompanyForm it mirrors.

### Tenant Isolation (required section)

**Tables accessed**: `companies` (read + update), `company_memberships`
(read, via the auth dependency), audit table (insert).

**Scoping**: For the `companies` table the tenant key *is* the row's own
`id`. Both endpoints derive `company_id` exclusively from
`CompanyMemberContext` / `CompanyAdminContext` (JWT `company_id` claim →
`_resolve_company_membership`, which re-validates membership and company
activeness on every request). The request URL and body carry **no company
id** — a client cannot even express a cross-tenant read or write. The new
repository method takes `company_id` as a required parameter and updates
`WHERE id = :company_id` only. Membership checks
(`get_membership(user_id, company_id)`) gate both role tiers; no method
accepts a bare entity id without the tenant key.

**Cross-tenant access**: none — no super-admin or cross-company operation is
introduced.

**Isolation tests** (to be written):

1. Member of Company A calls `GET /v1/companies/current` with an A-scoped
   token → sees only A's details; the response never contains another
   company's data (structural: id comes from the token).
2. Admin of Company A holding a token whose membership in A was revoked →
   403 `not_a_member` on both endpoints (existing dependency behavior,
   asserted for the new routes).
3. Non-admin member PATCH → 403 `forbidden`, and a follow-up GET proves the
   stored values are unchanged (FR-008, SC-003).
4. Two companies seeded; an update by A's admin leaves B's row untouched
   (repository-level assertion).

## Project Structure

### Documentation (this feature)

```text
specs/060-company-page/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── company-profile.md   # GET/PATCH /v1/companies/current + page contract
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
packages/core/
└── tessera_core/ports/repositories/company.py   # MODIFIED: update_details() abstract method

apps/api/
├── tessera_api/
│   ├── adapters/repositories/company.py         # MODIFIED: SqlCompanyRepository.update_details()
│   └── routers/companies.py                     # MODIFIED: GET/PATCH /companies/current,
│                                                #   CompanyProfileResponse, UpdateCompanyRequest
└── tests/
    ├── unit/test_company_profile_router.py      # NEW: both endpoints — roles, validation, audit
    ├── unit/test_company_repo.py                # MODIFIED: update_details scoping + None case
    └── integration/test_company_profile.py      # NEW: end-to-end + isolation tests 1–4

apps/web/
├── app/settings/company/page.tsx                # REWRITTEN: real company page (view + admin edit)
├── lib/
│   ├── companies.ts                             # MODIFIED: CompanyProfile type,
│   │                                            #   getCurrentCompany(), updateCurrentCompany()
│   └── companyOptions.ts                        # NEW: INDUSTRIES + TEAM_SIZES (extracted)
├── components/
│   ├── company/CompanyMenu.tsx                  # MODIFIED: un-gate link, label "Company"
│   └── onboarding/CompanyForm.tsx               # MODIFIED: import options from lib/companyOptions
└── tests/
    ├── company-page.test.tsx                    # NEW: view / not-provided / edit / cancel /
    │                                            #   validation / non-admin read-only / save failure
    └── company-menu.test.tsx                    # MODIFIED: link visible to non-admin members
```

**Structure Decision**: Existing monorepo layout; backend changes ride the
established router/port/adapter seams, web changes fill the already-routed
`/settings/company` placeholder. No new packages, no migrations.

## Design Decisions (summary — details in research.md)

1. **Singleton `current` resource, not `/companies/{id}`** — the company id
   comes only from the token context, making FR-009 unviolable at the URL
   level and matching the 053/054 convention (`/companies/members` etc.).
2. **Reuse `/settings/company`** — the placeholder page and its CompanyMenu
   link already exist; the link's admin gate is removed (spec gives all
   members read access). No new route or redirect.
3. **Validation mirrors company creation** — same `VALID_TEAM_SIZES` set,
   same length limits; client trims the name and re-uses the onboarding
   INDUSTRIES select (spec assumption: same accepted values as onboarding).
   `industry`/`team_size` accept `null` to clear a value.
4. **Explicit-field PATCH semantics** — all three editable fields are always
   sent by the form; the response echoes the saved profile, which the page
   swaps in atomically (edge case: never a mix of two concurrent edits on
   screen).
5. **Audit via existing `write_audit`** — action `company.updated`,
   entity `company`, metadata `{company_id, changed: {field: {from, to}}}`
   (FR-010/SC-004 without a new audit mechanism).
6. **Name propagation via `reloadCompanies()`** — the existing
   `CompanyProvider` already owns the company list shown in the nav; one call
   after save satisfies FR-007 with no new state channel.

## Complexity Tracking

No constitution violations — table intentionally empty.
