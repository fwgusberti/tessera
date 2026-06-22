# Implementation Plan: Company Menu

**Branch**: `030-company-menu` | **Date**: 2026-06-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/030-company-menu/spec.md`

## Summary

Add a company-context menu to the NavBar that shows the user's active company, allows switching between companies, supports in-menu company creation, and exposes a "Company settings" link for admins. Requires one new API endpoint (`GET /v1/companies/me`), a new React `CompanyContext`, a `CompanyMenu` dropdown component, and a `/settings/company` stub page. No database migrations required.

## Technical Context

**Language/Version**: Python 3.12 (backend) / TypeScript / Next.js 15 (frontend)

**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy (async), Pydantic — all already in use
- Frontend: React 18, Next.js 15, Tailwind CSS (slate/indigo palette), Vitest + Testing Library

**Storage**: PostgreSQL (existing); active company persisted in `localStorage` client-side

**Testing**:
- Backend: pytest-asyncio (core pkg), anyio/pytest.mark.anyio (API pkg), fastapi.testclient.TestClient for integration tests
- Frontend: Vitest + @testing-library/react

**Target Platform**: Browser (desktop + mobile ≤768px)

**Project Type**: Full-stack web application

**Performance Goals**: Company list load < 200ms (small list, single JOIN query)

**Constraints**: Mobile tap targets ≥ 44×44px; no new DB migrations

**Scale/Scope**: Typically 1–5 companies per user; no pagination needed

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. DDD | PASS | New endpoint uses existing domain entities; no framework imports in domain layer |
| II. Separation of Concerns | PASS | Company context is purely UI-layer; domain/API layers unchanged |
| III. Data Locality & Consent | PASS | `localStorage` stores only `tessera_active_company_id` (a UUID the user selects); no PII; user explicitly selects via menu action |
| IV. TDD | PASS | Unit + integration tests required for backend endpoint; component tests required for CompanyMenu |
| V. Quality Gates | PASS | Ruff + Black must pass before commit |
| UI Design System | PASS | slate-* neutrals, indigo-600 primary, no blue-* or gray-* additions |
| Security — Audit logging | PASS | No state-changing company actions in this feature beyond `POST /v1/companies` which already logs |

## Project Structure

### Documentation (this feature)

```text
specs/030-company-menu/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── api.md           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code

```text
apps/api/
├── tessera_api/
│   └── routers/
│       └── companies.py          # add GET /v1/companies/me
└── tests/
    ├── unit/
    │   └── test_company_router.py  # new: unit tests for /me endpoint
    └── integration/
        └── test_companies.py       # existing + add /me contract test

apps/web/
├── lib/
│   ├── company.tsx               # new: CompanyContext + provider
│   └── companies.ts              # add getMyCompanies()
├── components/
│   └── company/
│       ├── CompanyMenu.tsx        # new: dropdown component
│       └── CreateCompanyModal.tsx # new: lightweight create form
├── components/
│   └── NavBar.tsx                # modified: embed CompanyMenu
├── app/
│   ├── layout.tsx                # modified: wrap with CompanyProvider
│   └── settings/
│       └── company/
│           └── page.tsx          # new: stub settings page
└── tests/
    ├── company-menu.test.tsx      # new: CompanyMenu component tests
    └── navbar.test.tsx            # existing: extend with company menu cases
```

## Complexity Tracking

No Constitution violations.

## Design Decisions

### GET /v1/companies/me endpoint

Placed in `apps/api/tessera_api/routers/companies.py` alongside existing company routes.
Implementation:
1. `require_user(request)` → `user_id`
2. `company_repo.list_memberships_for_user(user_id)` → list of `CompanyMembership`
3. For each membership, `company_repo.get_by_id(membership.company_id)` → `Company`
4. Return `{"companies": [{id, name, role}]}` sorted by name

### CompanyContext (`apps/web/lib/company.tsx`)

Mirrors `AuthContext` pattern:
- Loads companies on mount (when `status === "authenticated"`)
- Reads active company ID from `localStorage`; falls back to first company
- Exposes `setActiveCompany(id)` which writes to `localStorage` and updates state
- Exposes `createAndSetActive(data)` which calls `POST /v1/companies`, reloads list, sets new company active
- Re-fetches company list when `status` transitions to `authenticated`

### CompanyMenu component (`apps/web/components/company/CompanyMenu.tsx`)

Behavior:
- **0 companies**: renders "Create or join a company" link
- **1 company**: renders company name as static text (no dropdown trigger)
- **2+ companies**: renders company name as a button; click opens dropdown with list + "Create new company" option
- Admin role: adds "Company settings" link pointing to `/settings/company`
- Closes on Escape key and outside click (same pattern as existing mobile menu)

### NavBar modification

- Import `CompanyMenu` and render it in the left side of the desktop nav (between logo and nav links) and in the mobile menu
- `CompanyProvider` wraps `children` in `app/layout.tsx` (inside `AuthProvider`)

### CreateCompanyModal (`apps/web/components/company/CreateCompanyModal.tsx`)

- Name (required), Industry (optional text), Team size (optional select)
- On submit: calls `companyContext.createAndSetActive({name, industry, team_size})`
- Shows inline error on failure; closes on success
- Uses `slate-*` / `indigo-*` color tokens per constitution

### /settings/company stub page

Minimal: renders a heading "Company Settings" and a note that settings are coming soon. Satisfies FR-007 (navigation target exists). Full settings implementation is a separate feature.

## Phase 0 Artifacts

See [research.md](research.md) — all NEEDS CLARIFICATION items resolved.

## Phase 1 Artifacts

- [data-model.md](data-model.md) — entities and client-side state shape
- [contracts/api.md](contracts/api.md) — new and used API contracts
- [quickstart.md](quickstart.md) — validation scenarios

## Next Step

Run `/speckit-tasks` to generate `tasks.md`.
