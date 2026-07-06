# Quickstart & Validation: Domain-Based Company Matching

Validates the reported scenario end-to-end: a second user on an existing
company's email domain is routed to **request approval to join**, not to create a
duplicate company.

## Prerequisites

- Backend deps installed for `apps/api` and `packages/core`; PostgreSQL running
  with migrations applied (including this feature's backfill migration).
- Standard local run per repo tooling (`apps/api` FastAPI service + `apps/web`
  Next.js). No frontend changes are needed for this feature.

## Automated validation (authoritative)

Run the new + affected suites:

```bash
# Core: public-domain classifier (pure unit tests)
pytest packages/core/tests/test_email_domain.py -q

# API: create_company auto-association + domain-policy guard + full loop
pytest apps/api/tests/integration/test_companies.py -q
pytest apps/api/tests/unit -k "company and domain" -q
```

Expected: all pass. Per `project_test_env_baseline`, ignore the pre-existing
unrelated failures (test_ports, migration_0002, tessera_mcp) and the unreachable
global 85% API coverage gate — assert the **new** lines are covered instead.

Key assertions (see `contracts/domain-matching.md`):
- Company created with a non-public founder email ⇒ exactly one
  `DomainJoinPolicy{policy: request_approval, verified: true}` + audit record.
- Company created with a public founder email ⇒ no domain policy.
- Second user on the same non-public domain: `/suggestions` lists the company;
  `POST …/join {domain_match}` ⇒ `pending`; admin `…/approve` ⇒ membership.
- Cross-domain isolation: `@foo` user joining a `@bar` company ⇒ 404.

## Manual validation (the reported bug)

1. Register **user A** with `founder@acme.example` and create company "Acme".
   → Confirm a domain policy for `acme.example` now exists
   (`request_approval`, `verified`).
2. Register **user B** with `teammate@acme.example`. Proceed through onboarding
   to the company step.
   → **Expected:** the step shows "Acme" as a match with **Request Access**, and
   "Create a new company" is the secondary option (not the default). This is the
   corrected behavior; previously user B saw only the create-company form.
3. As user B, click **Request Access**.
   → Redirected to `/onboarding/pending` showing "waiting for approval"; **no new
   company was created**.
4. As **user A** (admin), open the company's join-requests view and **Approve**
   user B.
   → User B's pending page polls, detects approval, and advances to
   `/onboarding/complete` as a **member** of Acme.
5. Negative check: register **user C** with `someone@gmail.com` and create a
   company; register **user D** with `other@gmail.com`.
   → **Expected:** user D sees **no** domain match for user C's company (public
   domains never match).

## Backfill check (existing data / the reporter's company)

After running the backfill migration, the reporter's pre-existing "Gusba dev"
company (admin email `@gusba.dev`) should have a `domain_join_policies` row for
`gusba.dev`. The next `@gusba.dev` registrant is then matched to it — closing the
original report. (Any accidental duplicate "Gusba dev" company created before the
fix is not auto-merged; clean it up manually if desired.)
