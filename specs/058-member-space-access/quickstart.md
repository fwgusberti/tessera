# Quickstart: Space Access Management for Company Members (058)

Validation guide — proves the feature end-to-end. Contracts:
[contracts/member-space-access.md](./contracts/member-space-access.md);
entities: [data-model.md](./data-model.md).

## Prerequisites

- Stack running (PostgreSQL + API + web), e.g. `docker compose up -d` then
  `uvicorn`/`next dev` per repo README, or the existing dev compose setup.
- A company admin account (e.g. `felipe@gusba.dev` in the `gusba.dev` company)
  and a member with **no space access** (e.g. `felipe+1@gusba.dev`, the
  reported account). The company must have at least one space.

## Automated validation

Run the feature-scoped suites (global 85% API coverage gate and the
pre-existing `test_ports` / `migration_0002` / `tessera_mcp` failures are
known-unrelated — see research.md R7):

```bash
# Core domain (pytest-asyncio)
cd packages/core && python -m pytest tests/test_member_access_service.py tests/test_space_hierarchy_admin.py -q

# API unit + integration (anyio, TestClient)
cd apps/api && python -m pytest tests/unit/test_member_space_access_router.py \
  tests/integration/test_member_space_access.py \
  tests/integration/test_admin_space_visibility.py \
  tests/test_tenant_isolation.py -q --no-cov

# Web
cd apps/web && npx vitest run tests/member-space-access-panel.test.tsx tests/spaces-empty-state.test.tsx
```

Expected: all pass, including the new tenant-isolation cases (cross-company
member → 404; foreign spaces never listed; non-admin → 403).

## Manual scenario walkthrough

### 1. Admin grants access from the Users page (User Story 1 / SC-001)

1. Sign in as the company admin → open **Users** (`/users`).
2. On the row for `felipe+1@gusba.dev`, click **Spaces** → panel opens listing
   **every** company space, each marked "No access".
3. Grant access to one space (role `viewer`) → row updates in place to show
   the role; nested child spaces show inherited access.
4. Change the role to `editor`, then revoke on a second test space — both
   reflect immediately (FR-003, FR-008).

### 2. The member now sees the space (User Story 1 / SC-004)

1. Sign in as `felipe+1@gusba.dev` (no re-login needed if already signed in —
   just reload **Spaces**).
2. The granted space (and its children) appear; its documents open with
   viewer/editor capabilities per the granted role.

### 3. Honest empty state (User Story 3 / SC-005)

1. Before granting anything (or after revoking all), as `felipe+1@gusba.dev`
   open **Spaces** → message reads that no spaces have been **shared with you
   yet** and an administrator can grant access — not "no spaces available in
   your company".

### 4. Admin sees every company space (User Story 2 / SC-003)

1. As a second user, create a space **without** adding the admin as a member.
2. As the company admin, open **Spaces** → the new space is visible with admin
   controls; open its **Members** link and grant `felipe+1@gusba.dev` access —
   succeeds (implicit admin).

### 5. Join-path parity (User Story 4 / SC-002)

1. Create one member per path: direct add, invitation acceptance, and a fresh
   sign-up with a matching email domain.
2. Each appears on `/users` and in the panel/member search, and can be granted
   access with the same result as steps 1–2.

### 6. Tenant isolation spot-check (SC-006)

1. As an admin of a *different* company, call
   `GET /v1/companies/members/{felipe+1-user-id}/space-access` → `404`, and
   confirm an audit `cross_tenant_denied` record.
2. Confirm that company's space list contains none of `gusba.dev`'s spaces.

## Quality gates

```bash
ruff check apps/api packages/core && black --check apps/api packages/core
```
