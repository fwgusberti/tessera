# Quickstart: Validate Company Creation Fix

## Prerequisites

- Local dev stack running (`make dev` or `scripts/dev.sh`)
- A registered user account (email + password); note the JWT obtained from `POST /v1/auth/login`

## Validation Scenarios

### SC-001 — Happy path: create company returns 201

```bash
TOKEN="<your_jwt>"
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/v1/companies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Co"}'
```

**Expected**: `201`

Response body must contain `"role": "admin"` and a valid `"id"` UUID.

### SC-002 — Membership stored as company membership (not space membership)

After creating the company, query the database directly:

```sql
SELECT id, user_id, company_id, role
FROM company_memberships
WHERE company_id = '<company_id_from_response>';
```

**Expected**: one row with `role = 'admin'`. No row in `space_memberships` for this company creation.

### SC-003 — No AttributeError in logs

After the request, inspect API logs:

```bash
docker compose logs api --tail=50
```

**Expected**: no `AttributeError: 'CompanyMembershipModel' object has no attribute 'space_id'` line.

## Unit Test Suite

Run the unit tests that cover the company repository mapper:

```bash
cd apps/api
uv run pytest tests/unit/test_company_repo.py -v
```

**Expected**: all tests pass, including tests that explicitly assert `result.company_id` is set and `result.role` is `CompanyRole.ADMIN`.
