# Quickstart: Fix Onboarding Gate Bypass

**Feature**: `008-fix-onboarding-gate-bypass` | **Date**: 2026-06-18

## Prerequisites

- Python 3.12, `uv` installed
- PostgreSQL running (or test suite running with mocked repos — no DB needed for gate tests)

## Run the guard-specific tests

```bash
cd apps/api
uv run pytest tests/integration/test_onboarding_gate.py -v
```

Expected: all tests pass (4 scenarios — one per exempted path + one regression check).

## Run the full integration suite

```bash
cd apps/api
uv run pytest tests/ -v
```

Expected: ≥85% coverage, no regressions in `test_companies.py` or `test_onboarding.py`.

## Manual end-to-end validation

1. Register a new user and log in.
2. Complete the profile step (`POST /v1/onboarding/profile`).
3. Call `GET /v1/companies/suggestions` — should return `{"invitations": [], "domain_matches": []}` (not 403).
4. Call `POST /v1/companies` with `{"name": "Acme"}` — should return 201 with company data (not 403).
5. Confirm the dashboard is reachable only after completing all onboarding steps.

## Verify regression guard

1. With a fresh mid-onboarding user (profile completed, no company), call `GET /v1/companies/{some-id}/join-requests`.
2. Expected response: HTTP 403 `{"code": "onboarding_required", ...}` — the guard still blocks non-exempt endpoints.
