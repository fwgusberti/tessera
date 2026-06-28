# Quickstart: Tenant-Scoped Authentication

This guide documents the runnable validation scenarios to confirm feature 039 works end-to-end.

## Prerequisites

```bash
# Start services
docker compose up -d postgres redis

# Apply migrations (including 0011_tenant_scoped_auth)
uv run alembic upgrade head

# Run the API
cd apps/api && uv run uvicorn tessera_api.main:app --reload
```

## Scenario 1 — Single-membership auto-scope (FR-001)

```bash
# Register user, create company, join it (use existing onboarding flow)
# Then:
TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"single@example.com","password":"Test1234!"}' \
  | jq -r .access_token)

# Decode the token and verify:
# - token_kind == "full"
# - company_id is present and matches the user's company
python3 -c "
import base64, json, sys
parts = '$TOKEN'.split('.')
payload = json.loads(base64.b64decode(parts[1] + '=='))
assert payload['token_kind'] == 'full', f'Expected full, got {payload[\"token_kind\"]}'
assert 'company_id' in payload, 'company_id missing from token'
print('PASS: auto-scoped to', payload['company_id'])
"
```

## Scenario 2 — Multi-membership requires tenant selection (FR-001, FR-007)

```bash
# User with memberships in Company A and Company B
TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"multi@example.com","password":"Test1234!"}' \
  | jq -r .access_token)

# Verify token_kind == "select" and no company_id
# Verify data endpoint returns 403
curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8000/v1/spaces \
  -H "Authorization: Bearer $TOKEN"
# Expected: 403

# Select a tenant
FULL_TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/select-tenant \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company_id":"<COMPANY_A_UUID>"}' \
  | jq -r .access_token)

# Verify token_kind == "full" with correct company_id
```

## Scenario 3 — select-tenant refuses non-member company (FR-002)

```bash
# multi@example.com has no membership in Company X
curl -s -X POST http://localhost:8000/v1/auth/select-tenant \
  -H "Authorization: Bearer $SELECT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company_id":"<COMPANY_X_UUID>"}' \
  | jq .
# Expected HTTP 403, error.code == "not_a_member"
```

## Scenario 4 — Revoked membership invalidates credential (FR-006)

```bash
# Hold a valid full token for Company A
# Remove the user's membership in Company A (via admin API or direct DB)
# Make any data-access request
curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8000/v1/spaces \
  -H "Authorization: Bearer $FULL_TOKEN"
# Expected: 403
```

## Scenario 5 — Refresh preserves scope (FR-001, research §2)

```bash
# Perform login (single-membership)
RESP=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"single@example.com","password":"Test1234!"}')
RT=$(echo $RESP | jq -r .refresh_token)

# Refresh
NEW_AT=$(curl -s -X POST http://localhost:8000/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$RT\"}" \
  | jq -r .access_token)

# Decode and verify same token_kind and company_id as original
```

## Scenario 6 — Zero-membership onboarding token (FR-010)

```bash
# User with no memberships
TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"newuser@example.com","password":"Test1234!"}' \
  | jq -r .access_token)

# Verify token_kind == "onboarding", no company_id
# Data endpoints must return 403
curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8000/v1/spaces \
  -H "Authorization: Bearer $TOKEN"
# Expected: 403

# Onboarding endpoint must be accessible
curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8000/v1/companies/suggestions \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200
```

## Running the automated test suite

```bash
cd apps/api

# All auth-related tests (unit + integration)
uv run pytest tests/auth/ tests/test_tenant_auth_isolation.py -v

# Cross-tenant isolation tests
uv run pytest tests/ -k "isolation or cross_tenant" -v

# Full suite
uv run pytest tests/ -v
```

## Expected test outcomes

| Test file | Scenarios covered |
|---|---|
| `tests/auth/test_auth_login.py` | FR-001 single/multi/zero membership token kinds |
| `tests/auth/test_auth_refresh.py` | FR-001 scope preservation; FR-006 revoked membership |
| `tests/auth/test_select_tenant.py` | FR-007 acceptance scenarios; FR-002 non-member rejection |
| `tests/test_tenant_auth_isolation.py` | SC-001–SC-005 cross-tenant enforcement |

## Reference

- Data model: [data-model.md](data-model.md)
- API contracts: [contracts/auth.yaml](contracts/auth.yaml)
- Research decisions: [research.md](research.md)
