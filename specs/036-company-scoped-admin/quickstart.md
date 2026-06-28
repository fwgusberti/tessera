# Quickstart: Validating Company-Scoped Admin Privileges

Runnable validation that proves admin authority is confined to the active company.
For the authority model and denial shapes, see [research.md](research.md); for
per-endpoint behavior see [contracts/authorization-matrix.md](contracts/authorization-matrix.md).

## Prerequisites

- Repo set up per the monorepo dev flow (`apps/api`, `packages/core`).
- Test deps installed (pytest + anyio for `apps/api`; pytest-asyncio for
  `packages/core`).
- Migrations applied through **0010** (`make migrate` or the project's Alembic
  upgrade command).

## Test fixtures

- Extend `apps/api/tests/conftest.py` `two_company_setup` with an **admin-role
  variant**: the mocked `get_membership` must return `CompanyRole.ADMIN` for the
  caller in Company A (today it returns `MEMBER` for both). Add a helper such as
  `admin_in_a_member_in_b` returning the same `(token_a, company_a_id, token_b,
  company_b_id)` tuple but with Alice = ADMIN in A and MEMBER in B (US3).
- Domain-level checks use `packages/core/tests/test_permissions.py` directly
  against `AccessContext(is_company_admin=...)` and the space predicates — no DB.

## Scenario 1 — Admin authority confined to the active company (US1, P1)

1. As **admin of Company A** (A active), perform each admin action against a
   Company A resource → **succeeds** (member invite/role/remove, create
   permission, create/sync connector, issue/revoke agent credential, read
   metrics, approve/reject proposal, reindex/edit document).
2. As the **same admin**, repeat each action against an equivalent **Company B**
   resource referenced by ID → **HTTP 404**, generic not-found body, target data
   unchanged, **exactly one** `cross_tenant_denied` audit record per attempt.
3. Request each listing (members, documents, metrics) → results contain **only**
   Company A data; no `cross_tenant_denied` record for listings.

Expected: all step-1 calls 2xx; all step-2 calls 404 + audit; step-3 lists
exclude Company B (SC-001, SC-002, SC-003, SC-004).

## Scenario 2 — No cross-company visibility from admin status (US2, P1)

1. As admin of Company A, `GET /v1/documents/{company_b_doc_id}` → **404**,
   identical status/body to requesting a random non-existent UUID.
2. Confirm no Company B field appears in any response body.

Expected: cross-company read is byte-identical to genuine not-found; one
`cross_tenant_denied` record exists (SC-003).

## Scenario 3 — Per-company authority for multi-company members (US3, P2)

Using `admin_in_a_member_in_b`:

1. With **Company A active**, perform an admin-only action on a Company A
   resource → **succeeds**.
2. With **Company B active**, perform the same admin-only action → **403**
   (non-admin in own active company — not a cross-tenant 404).

Expected: authority follows the active company (SC-006).

## Scenario 4 — Tenant protected from outside admins, incl. legacy global flag (US4, P2)

1. Create data in Company B as its own member.
2. With a Company A admin who **also** carries the legacy `users.is_admin = True`
   flag (but no Company B membership), attempt to edit/delete the Company B
   document → **404**, document unchanged.

Expected: the global flag confers no authority over Company B (FR-002, FR-007).

## Migration check (FR-009 / SC-007)

After `0010`:

```sql
-- every owner has an explicit admin membership
SELECT c.id
FROM companies c
LEFT JOIN company_memberships m
  ON m.company_id = c.id AND m.user_id = c.admin_user_id AND m.role = 'admin'
WHERE m.id IS NULL;          -- expect 0 rows

-- nobody who was only a member became admin (run before+after; admin count never drops)
SELECT count(*) FROM company_memberships WHERE role = 'admin';
```

Re-running the migration is a no-op (idempotent).

## Run the suites

```bash
# domain permission unit tests (per-company admin)
pytest packages/core/tests/test_permissions.py

# API cross-company isolation + per-company authority
pytest apps/api/tests/test_company_scoped_admin.py

# full regression (confirm 035 by-ID denials updated 403 -> 404; happy paths green)
pytest apps/api/tests packages/core/tests
```

Expected: new per-company and cross-company cases pass; existing in-company admin
happy paths still pass (SC-005); previously-403 cross-tenant by-ID assertions now
assert 404.
