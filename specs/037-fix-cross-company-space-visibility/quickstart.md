# Quickstart: Validate Space Visibility Is Confined to the Active Company

Runnable validation for feature 037. Proves the reproduction is fixed (SC-002), the
listing invariant holds on every surface (SC-001/003/004), by-ID access stays
indistinguishable from absent (SC-005), and the operator surface is audited (FR-008/009).

See [data-model.md](data-model.md) for the visibility rule and audit action, and
[contracts/space-visibility-matrix.md](contracts/space-visibility-matrix.md) for the
per-surface contract these scenarios assert.

## Prerequisites

- Monorepo dev env (see `specs/036-company-scoped-admin/plan.md` Technical Context).
- API test deps installed; tests run with `pytest` + anyio under
  `fastapi.testclient.TestClient` (sync).
- Fixtures in `apps/api/tests/conftest.py`: reuse `two_company_setup` and
  `legacy_global_admin_setup`; add a three-company `reproduction_setup` (A,B owned by
  company 1; C owned by company 2; company 3 owns none) for SC-002.

## Run

```bash
# Full API suite
make test            # or: cd apps/api && pytest

# This feature's tests
cd apps/api && pytest tests/test_space_visibility.py -v
cd apps/api && pytest tests/test_tenant_isolation.py -v

# Domain port guard (no list_for_user)
cd packages/core && pytest tests/test_repositories_port.py -v

# Quality gates (must pass before commit)
ruff check . && black --check .
```

## Scenario 1 — The reproduction is fixed (SC-002, US1)

Three companies, three spaces (A,B → Gusba Dev; C → Company 2; Company 3 owns none).
Sign in as each person, call `GET /v1/spaces`:

| Acting as | Expected `spaces` |
| --------- | ----------------- |
| felipe@gusba.dev (Gusba Dev) | exactly {A, B} |
| a@2.com (Company 2) | exactly {C} |
| a@3.com (Company 3, global admin) | {} (empty) |

**Expected**: each set matches exactly; no overlap. The C-leak into Gusba Dev and the
all-spaces leak to the Company 3 admin are both gone; Company 2's own member sees C.

## Scenario 2 — Per-path listing isolation (SC-001, SC-003, US3)

Using `legacy_global_admin_setup` (global `is_admin` in Company A, a space in Company B,
no membership in B). For each surface — `GET /v1/spaces`, search, assistant, documents —
call it while active as Company A:

**Expected**: only Company A's spaces are resolved; Company B's space never appears,
**despite** the legacy global `is_admin` flag. Active as a no-space company → empty.

## Scenario 3 — Member without platform status reaches own spaces (SC-004, US2)

As an ordinary member of Company B (no `is_admin`), call `GET /v1/spaces`.

**Expected**: Company B's spaces are returned in 100% of attempts. Reaching them requires
only membership, not any platform-wide status.

## Scenario 4 — By-ID access is indistinguishable from absent (SC-005, FR-007)

Active as Company A, `GET /v1/spaces/{B_space_id}` and `GET /v1/spaces/{random_uuid}`.

**Expected**: both return `404` with `{"error":{"code":"not_found","message":"Not found"}}`
— byte-identical. The Company B probe writes exactly one `cross_tenant_denied` audit row;
neither response reveals that the Company B space exists.

## Scenario 5 — Operator surface is audited (FR-008, FR-009)

As a global admin, call each of `GET /v1/admin/spaces`,
`PUT /v1/admin/spaces/{id}/retention`, `POST /v1/admin/reindex`.

**Expected**: the call succeeds (documented cross-tenant exception) **and** writes exactly
one `cross_company_admin_access` audit record capturing actor, endpoint, and operation.
A non-admin calling any of these still receives `403`.

## Scenario 6 — Domain port has no unscoped space query (Principle VI, C-006)

```bash
cd packages/core && pytest tests/test_repositories_port.py -v
```

**Expected**: asserts `SpaceRepository` has no `list_for_user` attribute and that the only
multi-tenant space list method without a `company_id` parameter is `list_all()`.

## Web verification (read-only)

Confirm everyday pages call the scoped endpoint and only the admin page uses the operator
surface:

```bash
cd apps/web && grep -rn "/v1/spaces\b\|/v1/admin/spaces" app components --include=*.tsx
# Expect: documents/home pages -> /v1/spaces ; app/admin/page.tsx -> /v1/admin/spaces
cd apps/web && npm test    # existing api/admin/documents suites stay green
```

## Done When

- [ ] Scenarios 1–6 pass.
- [ ] `list_for_user` is absent from the port and `SqlSpaceRepository`.
- [ ] `/v1/admin/*` space endpoints emit `cross_company_admin_access`.
- [ ] Full API suite green (modulo the documented pre-existing baseline failures);
      ruff + black clean.
