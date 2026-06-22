# Implementation Plan: Fix Create Company Button Network Error

**Branch**: `028-fix-create-company-fetch` | **Date**: 2026-06-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/028-fix-create-company-fetch/spec.md`

## Summary

Fix the "Failed to fetch" error on the company creation form by correcting a CORS
misconfiguration in the FastAPI backend (wildcard origin + credentials is rejected by
browsers), and improve network error messaging on the frontend so raw `TypeError`
strings are never shown to users.

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript / Next.js 15 (frontend)

**Primary Dependencies**: FastAPI ≥ 0.115 (Starlette CORSMiddleware), React 19, Next.js 15

**Storage**: PostgreSQL via SQLAlchemy (no schema changes required)

**Testing**: pytest + anyio (API); Vitest (frontend)

**Target Platform**: Linux server (API); browser / Next.js SSR (web)

**Project Type**: Web application (FastAPI backend + Next.js frontend)

**Performance Goals**: N/A — bug fix; no new latency budget

**Constraints**: Must not break existing authenticated routes; zero regression on all
existing company, onboarding, and auth flows.

**Scale/Scope**: Single-endpoint bug fix affecting all users who attempt company creation.

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. DDD / separation of concerns | ✅ PASS | CORS is infrastructure config; no domain logic touched |
| II. Tech-agnostic product definitions | ✅ PASS | No spec-level change; purely infrastructure fix |
| III. Data locality & consent | ✅ PASS | No new client-side storage |
| IV. Test-Driven Development | ✅ PASS | Tests for CORS headers and error messaging written first |
| V. Quality gates (Ruff/Black) | ✅ PASS | Two-line change to `main.py`; no new complexity |
| UI design system | ✅ PASS | Error copy already uses existing `red-*` semantic colours |
| Security (JWT auth) | ✅ PASS | Fix uses explicit allowed origin; does not weaken auth |
| Audit logging | ✅ PASS | No state-changing logic altered |

**No violations. Proceed to Phase 0.**

## Project Structure

### Documentation (this feature)

```text
specs/028-fix-create-company-fetch/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (no schema change — records that)
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
apps/api/
└── tessera_api/
    └── main.py                     ← CORS config fix (2 lines)

apps/api/tests/
└── integration/
    └── test_companies.py           ← add CORS preflight assertion

apps/web/
└── lib/
    └── api.ts                      ← catch TypeError, throw friendly error
└── components/onboarding/
    └── CompanyForm.tsx             ← no changes required (error prop already exists)

apps/web/tests/
└── (new test file for api.ts network error handling)
```

**Structure Decision**: Option 2 (web app) — backend fix in `apps/api`, frontend fix in
`apps/web`. No new files beyond one test file.

## Complexity Tracking

> No constitution violations to justify.
