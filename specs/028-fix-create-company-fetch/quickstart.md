# Quickstart: Validate "Create Company" Fix

## Prerequisites

- Docker Compose stack running (`docker compose -f deploy/docker-compose.yml up`)
- OR API (`uvicorn tessera_api.main:app --reload`) and Web (`npm run dev`) running locally
- A registered and logged-in user at the onboarding company step

## Scenario 1 — CORS preflight passes (primary fix)

### Setup

```bash
# Confirm the API is accessible
curl -v -X OPTIONS http://localhost:8000/v1/companies \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: authorization, content-type"
```

### Expected response (after fix)

```
HTTP/1.1 200 OK
Access-Control-Allow-Origin: http://localhost:3000   ← exact origin, not *
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: ...
```

### Before fix (broken)

```
Access-Control-Allow-Origin: *   ← wildcard — browser rejects with credentials
Access-Control-Allow-Credentials: true
```

---

## Scenario 2 — End-to-end company creation

1. Navigate to `http://localhost:3000/onboarding/company`
2. Enter a company name (e.g., "Test Corp") and click **Create Company**
3. **Expected**: redirected to `/onboarding/invite`; company visible in DB
4. **Unexpected (bug)**: "Failed to fetch" or "Could not reach the server" error message

### Database verification

```sql
SELECT id, name, industry, team_size FROM companies ORDER BY created_at DESC LIMIT 1;
```

---

## Scenario 3 — User-friendly error on genuine network failure

1. Stop the API server
2. Navigate to `/onboarding/company` in the browser
3. Enter a company name and click **Create Company**
4. **Expected**: form shows "Could not reach the server. Please check your connection
   and try again." — NOT "Failed to fetch"

---

## Scenario 4 — Backend unit / integration tests

```bash
cd apps/api
pytest tests/integration/test_companies.py -v
```

Expected: all tests pass including the new CORS preflight assertion.

---

## Scenario 5 — Frontend unit tests

```bash
cd apps/web
npm test
```

Expected: all tests pass including the new API-client network-error test.

---

## Regression check

Verify no existing flows broke:

```bash
# API
cd apps/api && pytest

# Frontend
cd apps/web && npm test
```

Both suites must pass with 0 failures.
