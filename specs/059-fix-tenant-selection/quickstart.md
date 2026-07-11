# Quickstart: Company Selection at Sign-In (059)

**Plan**: [plan.md](./plan.md) | **Contracts**: [contracts/company-selection.md](./contracts/company-selection.md)

Web-only feature: validation is Vitest suites plus a manual multi-company
walkthrough against the local stack.

## Prerequisites

```bash
# Web deps
cd apps/web && npm install

# Full stack for manual validation (API + Postgres + Redis)
docker compose up -d          # from repo root, per existing dev setup
cd apps/api && uvicorn tessera_api.main:app --reload   # if running API bare
cd apps/web && npm run dev    # http://localhost:3000
```

## Automated validation

```bash
cd apps/web
npx vitest run                          # full web suite must stay green
npx vitest run tests/select-company.test.tsx \
               tests/tenant-guard.test.tsx \
               tests/auth.test.tsx \
               tests/api.test.tsx \
               tests/login.test.tsx     # feature suites
```

Expected: all pass; no test renders the raw string
"Credential is not scoped to a tenant" (SC-002 assertion lives in the api and
select-company suites).

No Python changes — API/core suites are untouched (see research.md R8 for the
pre-existing baseline; do not re-diagnose those failures here).

## Manual validation scenarios

Setup: create a user who belongs to **two** companies (e.g., register, create
Company A during onboarding, then have a Company B admin add them via
Users → Add existing user — feature 054).

1. **US1 — happy path**: Sign out, sign in as the two-company user →
   company picker appears listing both companies with role badges → pick one
   → lands on `/` (or the original `redirect`), Spaces/Documents/Users pages
   load that company's data, no error banners.
2. **US1 — single company unchanged**: sign in as a one-company user → no
   picker, straight to the app. Zero-company user → onboarding.
3. **US2 — restored unscoped session**: as the two-company user, sign in but
   stop at the picker; open a new tab at `http://localhost:3000/spaces` →
   redirected to `/select-company?redirect=%2Fspaces`; picking a company
   lands on `/spaces`.
4. **US2 — never the raw error**: with the picker open in tab 1, complete
   selection in tab 2, then trigger a fetch in tab 1 (or simulate a stale
   select token) → user is routed to selection/app, the literal
   "Credential is not scoped to a tenant…" text never renders.
5. **US3 — suspended company**: suspend Company B
   (`UPDATE companies SET is_active = false WHERE name = 'Company B';`) →
   picking it shows the "unavailable" message, Company A remains selectable
   and works.
6. **US3 — revoked membership**: remove the user from Company B while the
   picker is open → picking B shows the "no longer have access" message and
   the refreshed list drops B.
7. **US3 — sign out from picker**: Sign out on the picker → back at `/login`,
   `localStorage` has no `tessera_*` tokens.
8. **FR-007 — persistence**: after selecting, reload the page and wait past
   token expiry (or delete `tessera_expires_at` to force a refresh) → still
   scoped to the chosen company, picker not shown again.

## Success criteria mapping

- SC-001 → scenarios 1, 3
- SC-002 → scenario 4 + test assertions
- SC-003 → scenario 1 (one extra step: the picker)
- SC-004 → scenario 2 + existing login/onboarding suites staying green
