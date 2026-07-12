# Quickstart: Company Page (060)

**Plan**: [plan.md](./plan.md) | **Contracts**: [contracts/company-profile.md](./contracts/company-profile.md)

Validation guide — how to prove the feature works end-to-end.

## Prerequisites

```bash
make infra      # Postgres/Redis containers
make migrate    # apply migrations (none new for this feature)
make api        # FastAPI on :8000
make web        # Next.js on :3000
```

You need one company with at least two members: an **admin** and a plain
**member** (create via onboarding, then add the second user from the Users
page — feature 054).

## Automated validation

Scoped test runs (avoid the repo-wide coverage gate and known pre-existing
failures — `test_ports`, `migration_0002`, `tessera_mcp` — which are not this
feature's signal):

```bash
# API — new/extended suites only
cd apps/api && uv run pytest \
  tests/unit/test_company_profile_router.py \
  tests/unit/test_company_repo.py \
  tests/integration/test_company_profile.py \
  --no-cov

# Web — new/extended suites only
cd apps/web && npx vitest run tests/company-page.test.tsx tests/company-menu.test.tsx

# Quality gates on touched Python
cd apps/api && uv run ruff check . && uv run black --check .
```

Expected: all listed suites pass. Full runs (`make test`) should show no
regressions beyond the documented pre-existing baseline.

## Manual scenarios

### US1 — View (member, P1)

1. Sign in as the plain **member**; open the company dropdown in the nav →
   click **Company** (link must be visible to non-admins).
2. Expect: company name, industry, team size, creation date. If industry or
   team size was never set, the field shows **"Not provided"** — not blank.
3. Expect: no Edit button anywhere on the page.

### US2 — Edit (admin, P2)

1. Sign in as the **admin**; open `/settings/company` → click **Edit**.
2. Change the name, pick a different team size → **Save**.
3. Expect: view mode shows the new values; the company name in the nav
   dropdown updates without a reload; a fresh sign-in still shows the new
   values (persistence).
4. Click **Edit**, clear the name → **Save**. Expect: rejection message,
   stored name unchanged.
5. Click **Edit**, change something → **Cancel**. Expect: original values,
   nothing saved.
6. Audit (SC-004): `psql` →
   `SELECT action, actor_id, entity_id, metadata FROM audit_records
   WHERE action = 'company.updated' ORDER BY created_at DESC LIMIT 1;`
   shows the admin, the company, and the changed fields.
   (Table name per existing audit adapter.)

### US3 — Non-admin refusal (P3)

1. As the **member**, confirm the page is read-only (no edit controls).
2. Forge a direct call:

   ```bash
   curl -s -X PATCH http://localhost:8000/v1/companies/current \
     -H "Authorization: Bearer <member-token>" \
     -H "Content-Type: application/json" \
     -d '{"name":"Hacked","industry":null,"team_size":null}'
   ```

   Expect: `403` with code `forbidden`; a follow-up GET shows unchanged data.

### Tenant isolation (SC-003)

1. Sign in as a user who belongs to **two** companies; select Company A.
2. `/settings/company` must show only A. Select Company B (company menu /
   select-company flow) → page now shows only B.
3. There is no way to request another company's profile: the endpoint takes
   no company id (verify `curl .../v1/companies/current` ignores any attempt
   to smuggle an id — there is no parameter to send).

### Signed-out access (FR-011)

`curl -s http://localhost:8000/v1/companies/current` → `401`. Opening
`/settings/company` signed out redirects to `/login`.
