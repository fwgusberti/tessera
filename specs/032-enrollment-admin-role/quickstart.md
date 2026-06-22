# Quickstart Validation: Enrollment Admin Role Assignment (032)

## Prerequisites

- API server running (`make dev` or `make start`)
- PostgreSQL migration 0008 applied (`make migrate`)
- At least one user registered in the system (or use test fixtures)

## Scenario 1 — Creator receives admin role at enrollment completion (Golden Path)

**Goal**: Prove that a user who creates a company via enrollment has admin membership after calling `/onboarding/complete`.

```bash
# 1. Authenticate (obtain JWT for a fresh user)
TOKEN=$(curl -s -X POST /v1/auth/token -d '{"email":"alice@test.com","password":"..."}' | jq -r '.access_token')

# 2. Complete profile step
curl -s -X POST /v1/onboarding/profile \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"full_name": "Alice Test"}'

# 3. Create company (admin membership + company_id stored in progress)
COMPANY=$(curl -s -X POST /v1/companies \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "Alice Corp"}')
COMPANY_ID=$(echo $COMPANY | jq -r '.id')

# 4. Complete enrollment
curl -s -X POST /v1/onboarding/complete \
  -H "Authorization: Bearer $TOKEN"

# 5. Verify: GET /companies/me must show role=admin
COMPANIES=$(curl -s /v1/companies/me -H "Authorization: Bearer $TOKEN")
echo $COMPANIES | jq '.companies[] | select(.id == "'$COMPANY_ID'") | .role'
# Expected output: "admin"
```

**Expected outcome**: `role` is `"admin"` for Alice's company.

---

## Scenario 2 — Idempotent completion (no duplicate memberships)

**Goal**: Calling `/onboarding/complete` twice does not create duplicate memberships or raise errors.

```bash
# After Scenario 1:
curl -s -X POST /v1/onboarding/complete -H "Authorization: Bearer $TOKEN"
# Expected: 200, same response body — no error

# Verify membership count (direct DB check)
psql $DATABASE_URL -c "SELECT COUNT(*) FROM company_memberships WHERE user_id='<alice_id>' AND company_id='$COMPANY_ID';"
# Expected: count = 1
```

---

## Scenario 3 — Joiner does NOT receive admin

**Goal**: A user who joins via invitation receives `member` role, not `admin`.

```bash
# Bob joins Alice's company via invitation
BOB_TOKEN=$(...)
curl -s -X POST /v1/companies/$COMPANY_ID/join \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -d '{"method": "invitation", "invitation_id": "<inv_id>"}'

curl -s -X POST /v1/onboarding/complete -H "Authorization: Bearer $BOB_TOKEN"

# Verify
curl -s /v1/companies/me -H "Authorization: Bearer $BOB_TOKEN" | jq '.companies[0].role'
# Expected: "member"
```

---

## Scenario 4 — Enrollment interrupted mid-flow (admin still assigned on retry)

**Goal**: If the user closes the browser after company creation but before completion, the admin role is correctly assigned when they return and complete.

```bash
# Step 1–3 same as Scenario 1
# Step 4: simulate interruption — do NOT call /onboarding/complete

# Return in a new session, complete enrollment
curl -s -X POST /v1/onboarding/complete -H "Authorization: Bearer $TOKEN"

# Verify admin
curl -s /v1/companies/me -H "Authorization: Bearer $TOKEN" | jq '.companies[0].role'
# Expected: "admin" (was already assigned at company creation, idempotent path at completion)
```

---

## Automated Test Commands

```bash
# Run all onboarding-related tests
cd apps/api
uv run pytest tests/integration/test_onboarding.py tests/integration/test_onboarding_gate.py -v

# Full test suite
uv run pytest tests/ -v
```

**Expected**: All tests pass, coverage ≥ 85%.
