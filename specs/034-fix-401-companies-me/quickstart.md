# Quickstart: Validate Fix for 401 on Companies/Me

## Prerequisites

- API running locally or in Docker: `make dev` or `docker compose up`
- A registered user account (email + password)
- A prior browser session cookie in the browser (from before fix 033 — the stale cookie scenario). To simulate this, clear all app cookies and create a fresh session, or test via the unit tests below.

## Scenario 1 — Returning User with Stale Session Cookie Can Access App (US1)

**Test using the API directly:**

```bash
# 1. Log in and get a JWT
curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "yourpassword"}' | jq .

# 2. Use the access_token from step 1 to call /companies/me
# Even if the browser has a stale session cookie, the JWT must succeed
curl -s http://localhost:8000/v1/companies/me \
  -H "Authorization: Bearer <access_token_from_step_1>" | jq .
# Expected: {"companies": [...]} with HTTP 200
```

**Test using the unit test suite:**

```bash
cd apps/api
uv run pytest tests/integration/test_companies.py::TestGetMyCompaniesAuth -v
```

Expected: both tests pass (200 with empty list).

## Scenario 2 — New User Mid-Onboarding Sees Empty Company List (US2)

```bash
# Register a new user (no onboarding completed)
curl -s -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "new@example.com", "password": "Password1!", "display_name": "New User"}' | jq .

# Log in to get a JWT
curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "new@example.com", "password": "Password1!"}' | jq .

# Call /companies/me — should return empty list, not 403
curl -s http://localhost:8000/v1/companies/me \
  -H "Authorization: Bearer <access_token>" | jq .
# Expected: {"companies": []} with HTTP 200
```

**Test using the unit test suite:**

```bash
cd apps/api
uv run pytest tests/integration/test_onboarding_gate.py -v
```

Expected: all existing tests pass; new stale-session test also passes.

## Regression Verification

Run the full test suite to confirm no regressions:

```bash
cd apps/api
uv run pytest tests/ -v --tb=short
```

Expected:
- `TestOnboardingGateRegression::test_list_join_requests_blocked_mid_onboarding` → 403 (gate still blocks non-exempt endpoints)
- `TestOnboardingGateIncompleteSession::test_incomplete_session_returns_401_not_500` → 401
- All other existing tests → pass

## Success Criteria Checklist

- [ ] SC-001: User who logs in successfully loads main app interface — no redirect to login
- [ ] SC-002: User with stale session cookie can log in and use app without clearing cookies
- [ ] SC-003: `GET /companies/me` returns 200 for any authenticated user (empty list for no memberships)
- [ ] SC-004: Endpoints that were previously blocked before onboarding remain blocked (only companies/me changes)
