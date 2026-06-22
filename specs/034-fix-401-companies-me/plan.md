# Implementation Plan: Fix 401 on Companies/Me After Login

**Branch**: `034-fix-401-companies-me` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/034-fix-401-companies-me/spec.md`

## Summary

Two bugs combine to break `GET /v1/companies/me` after login:

1. `require_user` (oidc.py) returns a truthy but incomplete session dict — one with only `active_company_id` and no `sub` — before checking the JWT Bearer token. The `require_onboarding_complete` guard then sees the missing `sub` and raises 401, even though a valid JWT is present in the same request.

2. `GET /v1/companies/me` is not in the `require_onboarding_complete` exempt list, so a mid-onboarding user (no completed onboarding) gets 403 instead of an empty list.

The fix is two targeted changes: (1) add a `sub` presence check in `require_user` before returning the session dict, and (2) add `GET /v1/companies/me` to the onboarding-gate exempt list.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, itsdangerous (SessionMiddleware), joserfc (JWT), pytest, anyio

**Storage**: PostgreSQL (via SQLAlchemy async) — no schema changes required

**Testing**: pytest + anyio; integration tests use `fastapi.testclient.TestClient` (sync)

**Target Platform**: Linux server (Docker/Kubernetes)

**Project Type**: Web service (FastAPI REST API)

**Performance Goals**: No new hot path — existing p95 targets unchanged

**Constraints**: Logic-only fix — no migrations, no new dependencies, no new endpoints

**Scale/Scope**: Two files changed (<10 lines total); two test classes added

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | PASS | Fix is in the API/auth layer; domain entities untouched |
| II. Separation of Concerns | PASS | No cross-layer contamination — auth logic stays in auth module |
| III. Data Locality & Consent | PASS | No new storage; session already stores user identity with consent at login |
| IV. Test-Driven Development | PASS | New failing tests written before fix; 85%+ coverage maintained |
| V. Quality Gates | PASS | Ruff + Black must pass; verified in existing CI |
| VI. Tenant Data Isolation | PASS | `GET /companies/me` already scoped to the authenticated user's own memberships; no cross-tenant data access introduced |

**Tenant Isolation section** (required per Security Requirements):
- Tables accessed: `company_memberships` — filtered by `user_id` in `list_memberships_for_user`; no unscoped query, no change in this fix
- New data-access paths: none
- Cross-tenant isolation tests: not applicable — this fix touches auth priority logic only, not data access

No constitution violations. No complexity tracking required.

## Project Structure

### Documentation (this feature)

```text
specs/034-fix-401-companies-me/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 — N/A (no entity changes)
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (files touched)

```text
apps/api/
├── tessera_api/
│   └── auth/
│       ├── oidc.py               # require_user: fall through to JWT when session lacks 'sub' (FR-001, FR-002)
│       └── bearer.py             # require_onboarding_complete: add GET /v1/companies/me to exempt list (FR-003)
└── tests/
    └── integration/
        ├── test_companies.py      # New: TestGetMyCompaniesAuth (stale session + JWT fallthrough; gate exemption)
        └── test_onboarding_gate.py  # New: TestStaleSessionJwtFallthrough (stale session + no JWT → 401)
```

## Phase 0: Research

### Root Cause Analysis

**Bug 1 — Stale Session Overrides Valid JWT** (`require_user`, oidc.py:51–77)

```python
# CURRENT (broken)
user = get_current_user_from_session(request)
if user:           # ← truthy even when dict is {"active_company_id": "..."}, no 'sub'
    return user    # ← JWT is never checked
```

A stale browser session cookie (created before fix 033 wrote full identity into session) contains only `{"active_company_id": "<uuid>"}`. This is truthy, so `require_user` returns it without ever reaching the JWT Bearer check. The `require_onboarding_complete` guard then calls `require_user` on every request, gets the incomplete dict, detects the missing `sub` (line 81 in bearer.py), and raises HTTP 401 — even though a valid JWT was also present in the same request.

**Bug 2 — companies/me not exempt from onboarding gate** (`require_onboarding_complete`, bearer.py:50–107)

The exempt list in `require_onboarding_complete` does not include `GET /v1/companies/me`. A brand-new user who has not completed onboarding gets HTTP 403 instead of an empty list from that endpoint.

### Fix Design

**Fix 1** — In `require_user`, add `sub` presence check before returning session:

```python
user = get_current_user_from_session(request)
if user and user.get("sub"):   # only valid if identity is complete
    return user
# falls through to JWT Bearer check
```

**Fix 2** — Add `GET /v1/companies/me` to exempt list in `require_onboarding_complete`:

```python
(r"^/v1/companies/me$", {"GET"}),
```

### Alternatives Considered

- **Clear stale session server-side**: Would require database-backed session tracking; far more invasive, adds infrastructure dependency.
- **Accept incomplete session and reconstruct from DB**: Over-engineers the auth layer; the clean answer is "incomplete session = not authenticated via session".
- **Global OIDC middleware rewrite**: Not justified — the fix is surgical and the OIDC path is a minor secondary concern.

### No New Dependencies

No new packages needed. All changes are logic-only in existing files.

## Phase 1: Design & Contracts

### Data Model

No entity changes. No migrations. `GET /companies/me` is already implemented and only requires the two auth fixes above.

### API Contracts

`GET /v1/companies/me` — unchanged response schema; access behavior changes:

| Scenario | Before | After |
|----------|--------|-------|
| Valid JWT + stale incomplete session cookie | 401 (gate rejects incomplete session) | 200 (JWT takes precedence, gate passes) |
| Valid JWT + no session cookie | 200 | 200 (unchanged) |
| Valid JWT + mid-onboarding (incomplete ob) | 403 (not exempt) | 200 with empty list (now exempt) |
| No credentials | 401 | 401 (unchanged) |
| Stale cookie + no JWT | 401 | 401 (unchanged — no valid auth credential) |

Response schema (unchanged):
```json
{
  "companies": [
    { "id": "uuid", "name": "string", "role": "admin|member" }
  ]
}
```

### Implementation Checklist (for tasks.md)

1. **Fix `require_user`** — `apps/api/tessera_api/auth/oidc.py`
   - Change `if user:` → `if user and user.get("sub"):` (line 54)
   - No other changes in this function

2. **Fix `require_onboarding_complete`** — `apps/api/tessera_api/auth/bearer.py`
   - Add `(r"^/v1/companies/me$", {"GET"}),` to `exempt_patterns` list (after line 67)

3. **New tests — `TestGetMyCompaniesAuth`** in `tests/integration/test_companies.py`
   - T1: stale session cookie (no sub) + valid JWT Bearer → GET /companies/me returns 200
   - T2: mid-onboarding user + valid JWT → GET /companies/me returns 200 with empty list

4. **New tests — `TestStaleSessionNoJwt`** in `tests/integration/test_onboarding_gate.py`
   - T3: stale session cookie (no sub) + no JWT → GET /companies/me returns 401 (not 500)
   - This verifies the fix doesn't accidentally allow unauthenticated access

5. **Verify no regression** — existing tests for onboarding gate blocking must still pass:
   - `TestOnboardingGateRegression::test_list_join_requests_blocked_mid_onboarding` → still 403
   - `TestOnboardingGateIncompleteSession::test_incomplete_session_returns_401_not_500` → still 401
