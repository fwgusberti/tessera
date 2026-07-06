# Phase 0 Research: Domain-Based Company Matching on Sign-Up

All open questions from the spec's one clarification were resolved before
planning (**auto-infer, approval-gated, no verification**). The remaining
research below records the *how* decisions and the code investigation that
shaped them.

## Decision 1: Where does the "make a company matchable" gap actually live?

**Finding**: The end-to-end flow already exists and is wired:

- `GET /companies/suggestions` returns `invitations` + `domain_matches`
  (`apps/api/.../routers/companies.py:420`).
- `POST /companies/{id}/join` with `method=domain_match` already branches on
  `policy.policy`: `auto_join` → immediate membership; `request_approval` →
  creates a `JoinRequest` and returns `pending` (`companies.py:562`).
- `GET /companies/{id}/join-status`, `DELETE …/join-request`, `GET
  …/join-requests`, `POST …/approve`, `POST …/deny` all exist and audit.
- Frontend: `app/onboarding/company/page.tsx` fetches suggestions and shows them
  **first** (view `suggestions`), demoting "Create a new company" to secondary;
  `onJoinViaDomain` routes to `app/onboarding/pending/page.tsx`, which polls
  `join-status` and advances on approval.

**Root cause**: two lines of gating, plus a missing write:
1. `create_company` (`companies.py:355`) creates the company + admin membership
   but **never creates a `DomainJoinPolicy`**.
2. `get_suggestions` only appends a match when `policy and policy.verified`
   (`companies.py:462`); the `domain_match` join branch rejects
   `not policy.verified` with 403 (`companies.py:581`).

**Decision**: Fix by *writing the missing policy* at creation and making it
`verified=True`, rather than relaxing the verified gate globally.

**Rationale**: Relaxing `verified` in suggestions/join would also surface
*manually-created, not-yet-email-verified* policies (the admin flow at
`companies.py:875` intentionally emails `verify@<domain>` and only matches after
confirmation). That would regress an existing, deliberate security behavior.
Writing an auto-created policy as `verified=True` is surgical: the existing
verified code paths light up for exactly the auto-inferred case and nothing else
changes.

**Alternatives considered**:
- *Add an `auto_created`/`source` column and match on `verified OR auto_created`*
  — cleaner semantics but requires a schema migration and edits to two match
  conditions. Rejected as over-engineering for the confirmed decision; the
  approval gate already carries the trust burden. (Revisit only if we later need
  to visually distinguish "email-verified" from "auto-trusted" in admin UI.)
- *Relax the global verified check* — rejected; regresses the manual flow.

## Decision 2: Trust semantics of `verified=True` on an auto-created policy

**Decision**: Auto-created policies are stored with `verified=True` and
`policy=REQUEST_APPROVAL`.

**Rationale**: The founder authenticated with an email on that domain, which we
treat as sufficient *association* (not full DNS/mailbox ownership proof). The
real protection is the **admin-approval gate**: no same-domain user is added
without an existing admin approving. `verified` here means "trusted enough to
surface as a match," which the approval gate backstops. This matches the
user-confirmed "auto-infer, approval-gated, no domain-ownership verification"
decision.

**Note**: `AUTO_JOIN` is never chosen automatically — auto-association always
uses `REQUEST_APPROVAL`, honoring the reporter's "waiting for approval"
expectation (spec FR-009). Auto-join remains an explicit, manual admin choice
and is out of scope here.

## Decision 3: Public / free email-provider exclusion

**Decision**: Add `is_public_email_domain(domain: str) -> bool` (and a small
`extract_domain(email)` helper) to a new pure-domain module
`packages/core/tessera_core/domain/email_domain.py`, backed by a curated
frozenset. `create_company` skips auto-association for public domains;
`create_domain_policy` rejects public domains with 422 (defense in depth).

**Rationale**: Constitution Principle I/II require business rules in the
framework-agnostic domain layer, where they are unit-testable in isolation.
Without this, the first person to found a company with `@gmail.com` would make
every future Gmail user a match — a privacy/security defect (spec FR-010,
SC-004).

**Initial denylist** (extensible): `gmail.com`, `googlemail.com`, `outlook.com`,
`hotmail.com`, `hotmail.co.uk`, `live.com`, `msn.com`, `yahoo.com`,
`yahoo.co.uk`, `ymail.com`, `icloud.com`, `me.com`, `mac.com`, `aol.com`,
`proton.me`, `protonmail.com`, `pm.me`, `gmx.com`, `gmx.net`, `mail.com`,
`zoho.com`, `yandex.com`, `yandex.ru`, `tutanota.com`, `fastmail.com`,
`hey.com`.

**Alternatives considered**: A third-party "disposable/free email" package or
remote list — rejected to avoid a runtime dependency and network calls in a
hot onboarding path; a curated in-repo list is deterministic, testable, and
trivially extended.

## Decision 4: Domain uniqueness & collisions

**Finding**: `domain_join_policies.domain` is `UNIQUE`. A domain maps to **at
most one** company.

**Decisions**:
- The spec's "multiple matching companies" edge case cannot occur under the
  current schema; a domain yields exactly zero or one match. The plan does not
  add multi-company-per-domain support.
- In `create_company`, guard with a `get_by_domain` pre-check **and** wrap the
  insert to tolerate a race: on `IntegrityError`/already-claimed, **skip
  silently** (the new company simply isn't matchable by that domain; the
  existing claimant keeps it) and continue. Company creation must never fail
  because of the optional auto-association.
- US3 scenario 3 ("second company on an already-claimed domain is steered to
  join") is satisfied by the existing suggestions-first frontend view; the
  backend's job is only to not duplicate-claim and not error.

## Decision 5: Backfill for existing companies

**Decision**: Ship a **data-only Alembic migration** that, for each existing
company without a domain policy, associates it with its `admin_user`'s email
domain when that domain is non-public and not already claimed
(`policy=request_approval`, `verified=True`). On a domain shared by multiple
existing companies, the earliest-created company wins; the rest are left
unassociated.

**Rationale**: Directly benefits the reporter — their existing "Gusba dev"
company becomes matchable immediately, so the *next* `@gusba.dev` registrant is
routed to it. Idempotent (skips companies that already have a policy) and
reversible (downgrade removes only rows it created, identifiable by absence of
`verified_at` + creation provenance; simplest: the downgrade is a no-op /
documented non-reversible data seed).

**Alternatives considered**: No backfill (only fix forward) — rejected because
it leaves every pre-existing organization exposed to the exact duplicate-company
problem that was reported.

## Decision 6: Frontend changes

**Decision**: None. `onboarding/company/page.tsx`, `CompanySuggestions.tsx`, and
`onboarding/pending/page.tsx` already implement suggestions-first display,
domain-join, and the pending/approval polling loop (spec FR-013, US1). Once the
backend surfaces matches, the existing UI handles the rest.

## Test strategy (per Principle IV)

- **Core unit** (`pytest-asyncio` not needed — pure functions):
  `is_public_email_domain` true/false cases (case-insensitivity, leading `@`,
  subdomain handling), `extract_domain`.
- **API unit/integration** (`anyio`, `TestClient`): create_company creates a
  `request_approval` + `verified` policy for a non-public domain; creates none
  for a public domain; skips when domain already claimed (no error); emits the
  audit record. `create_domain_policy` rejects a public domain (422).
- **Integration loop**: user A founds company (domain associated) → user B on
  same domain sees the match in `/suggestions` → `join` returns `pending` →
  admin approves → user B is a member; a second `pending` request is not
  duplicated.
- **Isolation**: `@foo` user cannot join a `@bar` company (404); `/suggestions`
  never leaks another domain's company; non-admin cannot list/approve/deny.
- Update the existing `test_create_company_returns_201` expectations to allow the
  new domain-policy side effect for non-public founder emails (or use a public
  test email where no side effect is expected).
