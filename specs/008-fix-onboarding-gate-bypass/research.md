# Research: Fix Onboarding Gate Bypass

**Feature**: `008-fix-onboarding-gate-bypass` | **Date**: 2026-06-18

## Root Cause Analysis

### Decision: extend `exempt_patterns` in `require_onboarding_complete`
**Rationale**: The guard in `apps/api/tessera_api/auth/bearer.py` uses a `(pattern, allowed_methods)` check to let certain requests through before checking `completed_at`. Two patterns already exist for the holding screen. The three new exemptions follow the identical pattern — no new mechanism needed.

**File**: `apps/api/tessera_api/auth/bearer.py:63`

Current exempt patterns:
```
r"^/v1/companies/[^/]+/join-status$"   (GET)
r"^/v1/companies/[^/]+/join-request$"  (DELETE)
```

Missing (cause of the bug):
```
r"^/v1/companies/suggestions$"          (GET)   — company step: load suggestions
r"^/v1/companies$"                      (POST)  — company step: create company
r"^/v1/companies/[^/]+/join$"          (POST)  — company step: join via invite/domain
```

**Alternatives considered**:
- Register the three endpoints on a separate router without `_onboarding_guard` (e.g., in `onboarding.py`): rejected — these endpoints are legitimately company-scoped and shouldn't be relocated; the exempt-pattern approach keeps the router boundaries clean.
- Remove `_onboarding_guard` from the companies router entirely and check per-endpoint: rejected — would require touching every post-onboarding company endpoint individually and risks future regressions.

## How `require_onboarding_complete` works

The dependency is added via `dependencies=_onboarding_guard` when the companies router is registered in `main.py:76`. FastAPI runs it before every handler in that router. The function checks the authenticated user's `OnboardingProgress.completed_at`; if `None`, it raises HTTP 403 with `{"code": "onboarding_required", ...}`.

The three onboarding-time endpoints still require a valid JWT (enforced by `require_user` inside the handler) — exempting them from the *onboarding-completion* check does not weaken authentication.

## Test strategy

- New file `tests/integration/test_onboarding_gate.py` (tests the guard itself, not the handler business logic).
- Tests mock `SqlOnboardingRepository.get_by_user_id` to return `None` (simulating a mid-onboarding user with no progress record) and assert the exempted paths return a non-403 status.
- A regression test mocks the same incomplete state and calls a non-exempted endpoint (e.g., `GET /v1/companies/{id}/join-requests`) to confirm 403 is still returned.
- Existing `test_companies.py` continues to use `_bypass_onboarding_guard()` context manager for handler-level tests — no changes needed there.
