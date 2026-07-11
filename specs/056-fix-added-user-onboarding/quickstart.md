# Quickstart / Validation: Admin-Added Members Onboarding Trap

Validates that a user added to a company by an admin lands in the app with
document access — never re-onboarded, never forced to create a company — and that
a company-less user is still onboarded normally.

## Prerequisites

- Backend deps installed (`apps/api`, `packages/core`); PostgreSQL reachable.
- Run from repo root.

## Automated checks

```bash
# Core domain predicate (pytest-asyncio package)
pytest packages/core/tests/test_onboarding_progress.py -q

# API gates + admin-add persistence + isolation (anyio + TestClient)
pytest apps/api/tests/integration/test_onboarding.py \
       apps/api/tests/integration/test_companies.py -q
```

Expected: predicate truth table passes; the admin-add → added-user flow returns
`completed=true` and 200 on documents; the no-company user still gets
`completed=false` / `403 onboarding_required`; cross-company request still
`403 not_a_member`. See [contracts/onboarding-gate.md](./contracts/onboarding-gate.md)
for the full matrix.

## Manual end-to-end (mirrors the reporter's steps)

1. Register user **B** (`newuser@example.com`). During onboarding, enter the
   name, reach the "create a company" step, and **stop** (do not create one).
2. As an existing **admin A** of company **Acme**, add **B** via the company user
   management page (or `POST /v1/companies/members` with B's user id).
3. Log out and log in as **B**.

**Expected (fixed):**
- **B** lands directly in the app — **not** redirected to `/onboarding`, and is
  **never** shown the "create a company" step.
- **B** can open **Acme**'s documents.
- `GET /v1/onboarding/status` for **B** returns `completed: true`.
- Audit shows `company.member_added` and `onboarding.completed` for **B**.

**Regression guard:**
- A brand-new user with **no** company still goes through onboarding and is
  offered create/join (company-less users are unaffected).
- **B** requesting another company's resources still gets `403 not_a_member`.

## Recovering already-trapped accounts (FR-006)

No action required. Any account that is already a company member but has null
`completed_at` (e.g., the reporter's existing added user) is admitted on its next
request — the gates derive from live membership. No migration is run.

## Rollback

Revert the changes to `packages/core/tessera_core/domain/onboarding_progress.py`,
`apps/api/tessera_api/auth/bearer.py`, `apps/api/tessera_api/routers/onboarding.py`,
and `apps/api/tessera_api/routers/companies.py`. No data migration to undo.
