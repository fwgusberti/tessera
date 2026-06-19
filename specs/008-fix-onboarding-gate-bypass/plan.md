# Implementation Plan: Fix Onboarding Gate Bypass

**Branch**: `008-fix-onboarding-gate-bypass` | **Date**: 2026-06-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/008-fix-onboarding-gate-bypass/spec.md`

## Summary

Add three missing exemptions to the `require_onboarding_complete` dependency so users can create a company, retrieve suggestions, and join an existing company while they are mid-onboarding. The guard already exempts the holding-screen polling endpoints; this fix extends the same pattern to the company-step action endpoints.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI 0.115, joserfc, structlog (no new dependencies)

**Storage**: No schema or migration changes required

**Testing**: pytest (≥85% coverage, TDD-first)

**Target Platform**: Linux server (FastAPI API)

**Project Type**: Full-stack web application — this fix is API-only; no frontend changes needed

**Performance Goals**: No change — exempt-path matching is a cheap regex check

**Constraints**: Fix must not relax the guard for any endpoint that should require completed onboarding; changes are isolated to `apps/api/tessera_api/auth/bearer.py` and a test file

**Scale/Scope**: Single-file change + companion tests; no new tables, routes, or dependencies

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | ✅ PASS | No domain entities changed. Fix is in the infrastructure/auth layer only. |
| II. Separation of Concerns | ✅ PASS | The guard lives in `auth/bearer.py` (infrastructure); domain and ports untouched. |
| III. Data Locality & Consent | ✅ PASS | No client-side persistence introduced. |
| IV. Test-Driven Development | ✅ PASS | Tests written first: one test per exempted endpoint verifying it works mid-onboarding, plus a regression test confirming non-exempt endpoints still block. |
| V. Quality Gates | ✅ PASS | Ruff + Black enforced; no new lint surface. |
| Stack — Persistent storage | ✅ N/A | No storage changes. |
| Stack — Caching/transport | ✅ N/A | No Redis usage. |
| Stack — IaC | ✅ N/A | No infrastructure change. |
| Security — Auth | ✅ PASS | Exemptions are narrowly scoped to three onboarding-time paths (exact method + regex match). JWT authentication still required for all three endpoints via `require_user`. |
| Security — Secrets | ✅ PASS | No secrets involved. |
| Security — Audit log | ✅ PASS | Audit logging on `company.created` and `company.joined_via_*` actions already exists in the router handlers; this fix does not change that. |
| Docs separation | ✅ PASS | This plan holds all technical decisions. Spec holds WHAT/WHY only. |

**Post-design re-check**: All principles maintained. The fix is additive (extends an existing exempt list) and does not introduce new architectural concepts.

## Project Structure

### Documentation (this feature)

```text
specs/008-fix-onboarding-gate-bypass/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — not yet created)
```

### Source Code

```text
apps/api/tessera_api/
└── auth/
    └── bearer.py          # Add 3 exempt patterns to require_onboarding_complete

apps/api/tests/integration/
└── test_onboarding_gate.py   # New: tests for exempted and non-exempted paths
```

**Structure Decision**: Single-file fix in the existing API auth module. No new routers, models, or packages. Test file is new (existing `test_companies.py` bypasses the guard globally via `dependency_overrides`; the new file tests the guard itself).

## Complexity Tracking

> No constitution violations requiring justification.
