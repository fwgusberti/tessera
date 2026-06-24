# Quickstart: Validate Company & User Scope Gaps Are Closed

A run/validation guide proving every hardened flow refuses cross-company access.
Implementation details live in [plan.md](plan.md), [data-model.md](data-model.md),
and [contracts/scope-gaps.md](contracts/scope-gaps.md).

## Prerequisites

- Repo bootstrapped per README; Python 3.12 + `uv` env active.
- PostgreSQL reachable (the migration and integration tests need it).
- From repo root.

## Setup

```bash
# Apply the new schema (agent_credentials.company_id)
make migrate            # or: alembic -c db/alembic.ini upgrade head

# Confirm migration 0009 is present
alembic -c db/alembic.ini history | grep 0009
```

## Cross-tenant test fixture

Reuse `two_company_setup` in `apps/api/tests/conftest.py` — it returns
`(token_a, company_a_id, token_b, company_b_id)` with scoped JWTs and patches the
membership check. For US6 admin cases, an `admin`-role variant of the fixture
(or a per-test `create_access_token(..., is_admin=False)` with an ADMIN
`CompanyMembership`) exercises per-company admin vs. cross-company admin.

## Run the isolation suite

```bash
# All new cross-tenant cases for this feature
cd apps/api
pytest tests/test_tenant_isolation.py -k "US1 or US2 or US3 or US4 or US5 or US6" -v

# Full regression (must stay green; coverage >= 85%)
pytest --cov=tessera_api --cov=tessera_core
```

## Scenarios & expected outcomes

| # | Story | Action as Company B against Company A | Expected |
|---|-------|----------------------------------------|----------|
| 1 | US1 | `GET /v1/proposals` | A's proposals **absent** from list |
| 2 | US1 | `GET /v1/proposals/{A_id}` | **403**, no document content |
| 3 | US1 | `POST /v1/proposals/{A_id}/approve` | **403**; A's doc + versions unchanged |
| 4 | US1 | `POST /v1/proposals/{A_id}/reject` | **403**; proposal state unchanged |
| 5 | US1 | In-company member without publish role approves | **403** (role) |
| 6 | US2 | `POST /v1/spaces/{A_space}/connectors` | **403**; no connector created |
| 7 | US2 | `POST /v1/connectors/{A_id}/sync` | **403**; no Celery job enqueued |
| 8 | US3 | `POST /v1/agent-credentials` scoped to A's space | **403**; no token |
| 9 | US3 | `POST /v1/agent-credentials/{A_id}/revoke` | **403**; token still active |
| 10 | US4 | invite / change-role / remove on A's space | **403** each |
| 11 | US4 | `GET /v1/spaces/{A_space}/members/me` | **403/404**, no A data |
| 12 | US4 | `POST /v1/spaces/{A_space}/permissions` | **403** |
| 13 | US5 | Company B admin `GET /v1/metrics` | totals exclude A's queries/proposals |
| 14 | US6 | Admin-of-A, member-of-B → any admin action on B | **403** |
| 15 | US6 | Admin-of-A → admin action on A | **succeeds** |

For every denial (2–4,6–12,14), assert a `cross_tenant_denied` audit record with
the actor, action, and targeted `entity_id` exists (SC-006). Assert that 403
bodies are identical for "missing" vs "other company" targets (SC-005).

## Manual smoke (optional)

```bash
# As Company B, attempt to read a Company A proposal id -> expect 403 generic body
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $TOKEN_B" \
  http://localhost:8000/v1/proposals/$COMPANY_A_PROPOSAL_ID      # -> 403

# As Company B, metrics reflect only B
curl -s -H "Authorization: Bearer $TOKEN_B" http://localhost:8000/v1/metrics
```

## Done when

- All scenarios 1–15 pass as an automated test (one per hardened flow → SC-001/2).
- No flow returns aggregate data spanning >1 company (SC-003).
- Migration 0009 applied; full suite green; Ruff + Black clean.
