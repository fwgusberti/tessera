# Implementation Plan: Fix Missing User Identity in Session After Company Activation

**Branch**: `033-fix-session-missing-sub` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/033-fix-session-missing-sub/spec.md`

## Summary

A JWT-only user calling `POST /v1/companies/{id}/activate` receives back a company-scoped token, but the endpoint also writes `{"active_company_id": "..."}` into the encrypted session cookie without including `sub` (or any user identity fields). On the next request, `require_user` sees the truthy — but incomplete — session dict and returns it; the onboarding guard then crashes with `KeyError: 'sub'`. The fix is a targeted two-part change: (1) populate the full identity when creating a new session user record in `activate_company`, and (2) add a defensive guard in `require_onboarding_complete` so any residual malformed session yields 401/403 instead of a 500.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, itsdangerous (session middleware), joserfc (JWT), pytest, anyio

**Storage**: PostgreSQL (via SQLAlchemy async) — no schema changes required

**Testing**: pytest-anyio; integration tests use `fastapi.testclient.TestClient` (sync)

**Target Platform**: Linux server (Docker/Kubernetes)

**Project Type**: Web service (FastAPI REST API)

**Performance Goals**: No new hot path — existing p95 targets unchanged

**Constraints**: Logic-only fix — no migrations, no new dependencies, no new endpoints

**Scale/Scope**: Two files changed (<20 lines total); two test classes added

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | PASS | Fix is in the API/auth layer; domain entities untouched |
| II. Separation of Concerns | PASS | No cross-layer contamination — auth logic stays in auth module |
| III. Data Locality & Consent | PASS | Session already stores user identity with user's consent at login; fix only ensures completeness |
| IV. Test-Driven Development | PASS | New failing tests written before fix; 85%+ coverage maintained |
| V. Quality Gates | PASS | Ruff + Black must pass; verified in existing CI |
| VI. Tenant Data Isolation | PASS | No multi-tenant data access; `activate_company` already validates membership before writing to session |

**Tenant Isolation section** (required per Security Requirements):
- Tables accessed by this change: none (logic-only; `activate_company` already does a DB read to verify membership — unchanged)
- New data-access paths: none
- Cross-tenant isolation tests: not applicable (session contents are per-user, not per-tenant data)

No constitution violations. No complexity tracking required.

## Project Structure

### Documentation (this feature)

```text
specs/033-fix-session-missing-sub/
├── plan.md              # This file
├── research.md          # Phase 0 — no external research needed (see below)
├── data-model.md        # Phase 1 — N/A (no entity changes)
├── quickstart.md        # Phase 1 — validation guide
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (files touched)

```text
apps/api/
├── tessera_api/
│   ├── routers/
│   │   └── companies.py          # activate_company: write full identity to session (FR-001, FR-002)
│   └── auth/
│       └── bearer.py             # require_onboarding_complete: defensive sub-key guard (FR-003)
└── tests/
    ├── integration/
    │   ├── test_companies.py      # New: TestActivateCompanySession class
    │   └── test_onboarding_gate.py  # New: TestOnboardingGateIncompleteSession class
    └── (no new files)
```

## Phase 0: Research

All unknowns are resolved by direct codebase inspection. No external research required.

**Decision log:**

| Question | Answer | Source |
|----------|--------|--------|
| Where is the bug? | `activate_company` in `routers/companies.py:711-713` creates an empty dict and writes only `active_company_id` | Code inspection |
| Why does the crash happen? | `require_user` returns the truthy but `sub`-less session dict; subsequent `user_info["sub"]` raises `KeyError` | `auth/oidc.py:53-55`, `auth/bearer.py:81` |
| What fields does a valid session user record need? | At minimum: `sub`, `email`, `is_admin`. All are available in `user_info` returned by `require_user` at `activate_company` call time | `auth/oidc.py:65-69` |
| Does the fix require a DB migration? | No — session contents are opaque; the cookie is rewritten on the next request automatically | Logic-only |
| What is the session priority order? | Session cookie first, then JWT Bearer — must not be changed | `auth/oidc.py:51-77` |
| How should the guard handle a missing `sub`? | Return early (treat as unauthenticated) so the JWT bearer guard handles the 401 — or raise 401 directly. The spec allows either 401 or 403. Raising 401 is cleaner (session without identity = not authenticated). | spec.md FR-003, SC-004 |

## Phase 1: Design & Contracts

### Data Model

No changes to domain entities or database schema. The "Session User Record" is a plain Python dict written to the encrypted cookie — not persisted in PostgreSQL.

**Session User Record contract** (existing, documented here for clarity):

```python
# Minimum valid session user record
{
    "sub": str,           # UUID of the authenticated user (canonical identity)
    "email": str,         # User email (may be empty string)
    "is_admin": bool,     # Platform admin flag
    # Optional fields added by OIDC login (e.g., "name", "picture")
    "active_company_id": str | None,  # UUID of the currently active company
}
```

**Before fix** — what `activate_company` wrote for a JWT-only user:
```python
{"active_company_id": "<uuid>"}  # ← missing sub, email, is_admin
```

**After fix** — what `activate_company` will write for a JWT-only user:
```python
{
    "sub": "<user-uuid>",
    "email": "<user-email>",
    "is_admin": False,
    "active_company_id": "<company-uuid>",
}
```

### Code Changes

#### Change 1 — `routers/companies.py` (FR-001, FR-002)

**Current code** (lines 711–713):
```python
if "user" not in request.session:
    request.session["user"] = {}
request.session["user"]["active_company_id"] = str(company_id)
```

**Replacement**:
```python
if "user" not in request.session:
    request.session["user"] = {
        "sub": user_info["sub"],
        "email": user_info.get("email", ""),
        "is_admin": user_info.get("is_admin", False),
    }
request.session["user"]["active_company_id"] = str(company_id)
```

**Why**: `user_info` is already resolved by `require_user` at the top of `activate_company` (line 684). Populating the session from it is safe and idempotent. The `if "user" not in` guard (FR-002) preserves existing session fields for OIDC users who already have a complete session.

#### Change 2 — `auth/bearer.py` (FR-003)

**Current code** (lines 76–81, inside `require_onboarding_complete`):
```python
try:
    user_info = await require_user(request)
except HTTPException:
    return  # No authenticated user — JWT/OIDC guard will handle 401

user_id = UUID(user_info["sub"])  # ← crashes if sub missing
```

**Replacement**:
```python
try:
    user_info = await require_user(request)
except HTTPException:
    return  # No authenticated user — JWT/OIDC guard will handle 401

if "sub" not in user_info:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": "invalid_session", "message": "Incomplete session — re-authenticate"}},
    )

user_id = UUID(user_info["sub"])
```

**Why**: Defense-in-depth per FR-003. Even after Change 1 prevents this from occurring in normal flow, a malformed or legacy session cookie should yield a structured 401, never a 500. The `status` import is already present in the file.

### Contracts

No new REST endpoints. No contract files needed.

### Test Plan

#### `tests/integration/test_companies.py` — `TestActivateCompanySession` (new class)

| Test | Scenario | Expected |
|------|----------|----------|
| `test_jwt_user_activate_stores_complete_identity` | JWT-only user, no prior session; calls `POST /v1/companies/{id}/activate` | Session `"user"` dict contains `sub`, `email`, `is_admin`, and `active_company_id` |
| `test_activate_company_preserves_existing_session_fields` | User already has a session cookie with `sub` and extra fields; calls activate | Existing fields preserved; `active_company_id` updated; no existing field overwritten |

Both tests use `TestClient` with session cookie inspection via `client.cookies` or by mocking `request.session` as a dict and asserting its contents.

#### `tests/integration/test_onboarding_gate.py` — `TestOnboardingGateIncompleteSession` (new class)

| Test | Scenario | Expected |
|------|----------|----------|
| `test_incomplete_session_returns_401_not_500` | Session cookie has `{"active_company_id": "..."}` but no `sub`; hits a guarded route | HTTP 401 with `invalid_session` code |
| `test_complete_session_after_activate_passes_guard` | JWT user activates company (session now has `sub`); hits a guarded route with onboarding complete | HTTP 200 (no crash, no 500) |

The second test is the regression test for SC-001 and SC-002.

## Key Rules

- Only touch `companies.py` and `bearer.py` — no other files modified
- Preserve the session priority order in `require_user` (session first, JWT second)
- No new imports required
- No migrations
- Ruff + Black must pass before commit
