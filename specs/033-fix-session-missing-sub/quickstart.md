# Quickstart Validation Guide: Fix Missing User Identity in Session

## Prerequisites

- Tessera API running locally or in test mode
- Python test environment: `cd apps/api && source .venv/bin/activate`
- PostgreSQL and session middleware configured (or mocked as per test patterns)

## Validate Manually

The simplest end-to-end proof of the fix:

```bash
# 1. Authenticate via the JWT (email/password) login path and get a Bearer token
TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"..."}' \
  | jq -r '.access_token')

# 2. Activate a company — this is where the session user record is created
COMPANY_ID="<your-company-uuid>"
curl -s -X POST "http://localhost:8000/v1/companies/$COMPANY_ID/activate" \
  -H "Authorization: Bearer $TOKEN" \
  -c /tmp/tessera-cookies.txt   # save session cookie

# 3. Hit any protected route using only the session cookie (no Bearer token)
# Before the fix: 500 KeyError. After the fix: correct response.
curl -s "http://localhost:8000/v1/onboarding/status" \
  -b /tmp/tessera-cookies.txt

# Expected: {"completed": true/false, "current_step": "...", ...}
# NOT: {"detail": "Internal Server Error"} (500)
```

## Validate via Tests

```bash
cd apps/api

# Run the new session-identity regression tests
python -m pytest tests/integration/test_companies.py::TestActivateCompanySession -v

# Run the guard resilience tests
python -m pytest tests/integration/test_onboarding_gate.py::TestOnboardingGateIncompleteSession -v

# Run the full existing gate/company test suite to confirm no regressions
python -m pytest tests/integration/test_onboarding_gate.py tests/integration/test_companies.py -v
```

## Expected Outcomes

| Scenario | Before fix | After fix |
|----------|-----------|-----------|
| JWT user activates company, hits protected route | 500 `KeyError: 'sub'` | 200 (or 403 if onboarding incomplete) |
| Session dict with no `sub` hits guarded route | 500 `KeyError: 'sub'` | 401 `invalid_session` |
| OIDC session user activates company | Unaffected (existing `sub` preserved) | Unaffected (session fields not overwritten) |
| Unauthenticated request to guarded route | 401 (unchanged) | 401 (unchanged) |

## What Not to Test Here

- Full onboarding flow end-to-end (covered by `test_onboarding.py`)
- Company membership validation (covered by `test_companies.py` existing tests)
- JWT token generation/verification (covered by `test_jwt_helpers.py`)
