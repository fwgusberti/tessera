# Quickstart: Validate Tenant Data Isolation (031)

## Prerequisites

- Local stack running: `make dev` (PostgreSQL + API + workers)
- Two test companies and users available (see setup below)
- `httpie` or `curl` for API calls

---

## Test Environment Setup

### Create two isolated companies

```bash
# Register User A (Company Alpha)
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@alpha.test","password":"secret1","display_name":"Alice"}' | jq .

# Login as Alice → get TOKEN_A
TOKEN_A=$(curl -s -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@alpha.test","password":"secret1"}' | jq -r .access_token)

# Create Company Alpha
COMPANY_A=$(curl -s -X POST http://localhost:8000/companies \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{"name":"Alpha Corp"}' | jq -r .id)

# Activate Company Alpha context → get scoped TOKEN_A
TOKEN_A=$(curl -s -X POST http://localhost:8000/companies/$COMPANY_A/activate \
  -H "Authorization: Bearer $TOKEN_A" | jq -r .token)

# Repeat for User B / Company Beta
TOKEN_B=...   # similar flow
COMPANY_B=...
```

---

## Scenario 1: Space Isolation (US-1, FR-002)

```bash
# Alice creates a space in Company Alpha
SPACE_A=$(curl -s -X POST http://localhost:8000/spaces \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{"slug":"alpha-space","name":"Alpha Space","sector":"tech","default_language":"en"}' \
  | jq -r .space.id)

# Bob lists spaces — should see ZERO spaces from Alpha
curl -s -X GET http://localhost:8000/spaces \
  -H "Authorization: Bearer $TOKEN_B" | jq '.spaces | length'
# Expected: 0

# Bob tries to create a document in Alpha's space — should get 403
curl -s -X POST http://localhost:8000/documents \
  -H "Authorization: Bearer $TOKEN_B" \
  -H "Content-Type: application/json" \
  -d "{\"space_id\":\"$SPACE_A\",\"title\":\"Stolen Doc\",\"content_markdown\":\"secret\"}" \
  | jq .error.code
# Expected: "forbidden"
```

---

## Scenario 2: Document Isolation (US-2, FR-003)

```bash
# Alice creates and publishes a document
DOC_A=$(curl -s -X POST http://localhost:8000/documents \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d "{\"space_id\":\"$SPACE_A\",\"title\":\"Alpha Secret\",\"content_markdown\":\"top secret\"}" \
  | jq -r .document.id)

# Bob tries to get Alice's document by ID — should get 403, not 404
curl -s -X GET http://localhost:8000/documents/$DOC_A \
  -H "Authorization: Bearer $TOKEN_B" | jq .error.code
# Expected: "forbidden" (not 404 — presence must not be revealed)
```

---

## Scenario 3: Search Isolation (US-2, FR-005)

```bash
# Alice publishes a document (triggers reindex)
curl -s -X POST http://localhost:8000/documents/$DOC_A/publish \
  -H "Authorization: Bearer $TOKEN_A" | jq .document.state
# Expected: "published"

# Bob searches for keywords from Alice's document — should get zero results
curl -s -X POST http://localhost:8000/search \
  -H "Authorization: Bearer $TOKEN_B" \
  -H "Content-Type: application/json" \
  -d '{"query":"top secret","top_k":5}' | jq '.results | length'
# Expected: 0

# Bob queries the assistant — should get no citation from Alpha
curl -s -X POST http://localhost:8000/assistant/answer \
  -H "Authorization: Bearer $TOKEN_B" \
  -H "Content-Type: application/json" \
  -d '{"query":"top secret"}' | jq '.citations'
# Expected: [] or null — no Alpha citations
```

---

## Scenario 4: Context Switch (US-4, FR-008)

```bash
# Create a user that belongs to BOTH companies
# Register Charlie
TOKEN_C_INIT=...  # login as charlie

# Charlie joins Alpha and Beta
curl -s -X POST http://localhost:8000/companies/$COMPANY_A/activate \
  -H "Authorization: Bearer $TOKEN_C_INIT" | jq .token
# → TOKEN_C_AS_ALPHA (only sees Alpha spaces)

curl -s -X POST http://localhost:8000/companies/$COMPANY_B/activate \
  -H "Authorization: Bearer $TOKEN_C_INIT" | jq .token
# → TOKEN_C_AS_BETA (only sees Beta spaces)

# Verify no cross-contamination
curl -s -X GET http://localhost:8000/spaces \
  -H "Authorization: Bearer $TOKEN_C_AS_ALPHA" | jq '[.spaces[].company_id] | unique'
# Expected: ["<COMPANY_A_UUID>"]

curl -s -X GET http://localhost:8000/spaces \
  -H "Authorization: Bearer $TOKEN_C_AS_BETA" | jq '[.spaces[].company_id] | unique'
# Expected: ["<COMPANY_B_UUID>"]
```

---

## Automated Test Suite

All the above scenarios are encoded as integration tests in:

```
apps/api/tests/test_tenant_isolation.py
```

Run with:

```bash
cd apps/api && uv run pytest tests/test_tenant_isolation.py -v
```

Expected: all tests green before merging.

---

## Definition of Done

- [ ] `GET /spaces` returns only the authenticated company's spaces
- [ ] `GET /documents/{id}` returns 403 (not 404) for a different company's document
- [ ] `POST /search` returns zero results for cross-company keywords
- [ ] `POST /assistant/answer` returns no citations from another company's documents
- [ ] `POST /companies/{id}/activate` → 403 for a company the user does not belong to
- [ ] All automated isolation tests in `test_tenant_isolation.py` pass
- [ ] Existing tests in `test_assistant_history.py` still pass (no regression)
