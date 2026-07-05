# Quickstart & Validation: Company User Management Page

Validates the feature end-to-end against the acceptance scenarios in
[spec.md](./spec.md). See [contracts/company-members.openapi.yaml](./contracts/company-members.openapi.yaml)
for the endpoint contract and [data-model.md](./data-model.md) for the query/shape.

## Prerequisites

- API and web dev servers running (see repo `Makefile` targets).
- A company (Company A) with at least two members of mixed roles: one `admin`
  (the viewer) and one `member`.
- A second company (Company B) with its own members, sharing no member with A that
  is *B-only*, to prove tenant scoping.

## Automated tests (authoritative)

Backend (from repo root):

```bash
# Endpoint contract: admin 200 / member 403 / unauthenticated 401
pytest apps/api/tests/unit/test_company_members_router.py

# Cross-tenant isolation: Company A admin sees only Company A members
pytest apps/api/tests/test_tenant_isolation.py -k company_members

# Repository + port
pytest packages/core/tests -k company_member
```

Frontend:

```bash
cd apps/web && npx jest user-management
```

Validate the suite against the known baseline (do not treat the pre-existing API
85% coverage gate or the known-failing baseline tests as regressions).

## Manual validation scenarios

### Scenario 1 — Admin views the roster (US1, FR-002/003/004)
1. Sign in as the Company A admin; ensure Company A is the active company.
2. Open **Users** in the nav (`/users`).
3. **Expect**: every Company A member listed, each with name + email and a role
   badge reading "administrator" or "member". No row is blank or role-less.

### Scenario 2 — Single-member company (US1 scenario 2, FR-007)
1. Sign in as an admin whose active company has only themselves.
2. Open `/users`.
3. **Expect**: exactly one row — the admin — marked "administrator". No empty/broken
   state.

### Scenario 3 — Non-admin is denied (US2, FR-005)
1. Sign in as a non-admin **member** of the active company.
2. Navigate to `/users`.
3. **Expect**: access-denied state; the roster is never rendered. (API returns 403.)
4. Repeat unauthenticated → not shown any membership data (API returns 401).

### Scenario 4 — Scoped to the active company (US3, FR-006, Principle VI)
1. Sign in as an admin whose account also belongs to Company B.
2. With Company A active, open `/users` → **Expect**: only Company A members.
3. Switch the active company to Company B (company menu) → reload `/users` →
   **Expect**: only Company B members. No member appears across both unless they are
   genuinely a member of both.

## Success check

- SC-001: complete, correct roster with roles in a single view — Scenario 1.
- SC-002: 100% of listed users belong to the active company — Scenario 4 + isolation test.
- SC-003: 100% of non-admin/unauthenticated attempts denied, no data revealed — Scenario 3.
- SC-004: every listed member shows exactly "administrator" or "member" — Scenario 1.
- SC-005: a known member is locatable within seconds (roster ordered by name) — Scenario 1.
