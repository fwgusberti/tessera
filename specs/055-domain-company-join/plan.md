# Implementation Plan: Domain-Based Company Matching on Sign-Up

**Branch**: `055-domain-company-join` | **Date**: 2026-07-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/055-domain-company-join/spec.md`

## Summary

A new user who registers with a work email whose domain already belongs to an
existing company is currently funneled into *creating a new company*, producing
duplicate organizations. Investigation shows the entire join-by-domain flow —
suggestions endpoint, `request to join` → pending → admin approve/reject,
notifications, and the full frontend (suggestions-first onboarding view + a
polling "pending approval" page) — **already exists and works**. The flow never
triggers for organically-created companies because of two narrow gaps:

1. **`create_company` never associates the founder's email domain with the
   company.** A domain becomes matchable only if an admin *manually* adds and
   *email-verifies* a domain policy — which almost never happens before the
   second teammate signs up.
2. **`get_suggestions` and the `domain_match` join branch only honor
   `verified=True` domain policies.** Any auto-inferred domain would be filtered
   out.

Per the confirmed product decision (**auto-infer, approval-gated, no
domain-ownership verification required**), the fix is deliberately surgical:

- Add a framework-agnostic **public-email-domain classifier** to the core domain
  (so gmail/outlook/etc. never make a company matchable).
- On company creation, if the founder's email domain is **non-public** and **not
  already claimed**, auto-create a `DomainJoinPolicy(policy=request_approval,
  verified=True)`. Marking it `verified` makes it immediately matchable through
  the *existing, unchanged* suggestions and join code paths — the founder
  authenticated with that email domain, and the admin-approval gate is the real
  safety net.
- Guard the manual domain-policy endpoint against public domains (defense in
  depth for FR-010).
- One-time **data backfill** associating existing companies with their admin's
  non-public email domain (fixes the reporter's already-existing "Gusba dev"
  company going forward).

No frontend changes are required. No schema change is required (the
`domain_join_policies` table and `verified` column already exist).

## Technical Context

**Language/Version**: Python 3.11 (backend, `apps/api` + `packages/core`);
TypeScript / Next.js (frontend, `apps/web`) — **no frontend changes in scope**.

**Primary Dependencies**: FastAPI, SQLAlchemy (async), Alembic, Pydantic v2
(backend). Domain layer (`tessera_core`) is pure Python, no framework imports.

**Storage**: PostgreSQL. Reuses existing tables `companies`,
`domain_join_policies` (unique `domain`), `join_requests`,
`company_memberships`. No new tables or columns.

**Testing**: pytest. Core package uses `pytest-asyncio`
(`@pytest.mark.asyncio`); API package uses `anyio` (`@pytest.mark.anyio`) with
`fastapi.testclient.TestClient` for integration — do not mix the two markers.

**Target Platform**: Linux server (containerized).

**Project Type**: Multi-tenant web service (monorepo: `packages/core` domain,
`apps/api` FastAPI, `apps/web` Next.js).

**Performance Goals**: Onboarding-time, per-request; no throughput concern. The
added work is one indexed `get_by_domain` lookup + at most one insert per company
creation.

**Constraints**: Must not weaken the existing manual, email-verified domain
policy flow (unverified *manual* policies must still NOT match). Must preserve
tenant isolation and audit logging on every state change.

**Scale/Scope**: Small, well-bounded change — ~1 new core module + helper, ~1
modified endpoint (`create_company`), ~1 guarded endpoint (`create_domain_policy`),
1 data-migration, and companion tests. Existing suggestions/join/approve
endpoints and all frontend are unchanged.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

- **I. Domain-Driven Architecture** — PASS. The new business rule ("is this a
  public email provider domain?") lives in `tessera_core.domain`
  (`email_domain.py`), free of framework/persistence imports. The API layer
  consumes it.
- **II. Separation of Concerns** — PASS. Public-domain classification and the
  auto-association policy decision are domain concerns; persistence stays behind
  the existing repositories.
- **III. Data Locality & Consent** — N/A. No client-side persistence.
- **IV. Test-Driven Development (NON-NEGOTIABLE)** — PASS (planned). The core
  classifier and each `create_company` branch are written test-first. New code
  ships with companion coverage. Note (per `project_test_env_baseline` memory):
  the repo-wide 85% API coverage gate is unreachable at the current baseline
  (~73%); we validate by covering the new/changed lines specifically, not by the
  global gate.
- **V. Quality Gates** — PASS (planned). Ruff + Black clean before commit.
- **VI. Tenant Data Isolation (NON-NEGOTIABLE)** — PASS. See dedicated section
  below.

### Tenant Isolation (mandatory)

**Tables accessed**: `companies`, `domain_join_policies`, `join_requests`,
`company_memberships`, `users` (for notification identity), `onboarding_*`.

**Intentional pre-membership, self-referential global lookup (documented
exception)**: Domain matching at sign-up is by design *not* company-scoped —
the whole point is to match a user who has **no company context yet** to an
existing company. This is safe and narrowly bounded because:

- The lookup key is always the **caller's own authenticated email domain**
  (`_email_domain(user_info["email"])`), never a client-supplied domain or
  company id used to fish for other tenants.
- Only a company that owns *the caller's own domain* is exposed, and only its
  `id`, `name`, and `domain` — no tenant-owned content.
- `join_company(method=domain_match)` re-validates that the resolved policy's
  `company_id` matches the target and that the policy domain equals the caller's
  domain; a mismatch returns 404 `no_domain_policy`.

**Company-scoped, admin-gated mutations (unchanged)**: listing, approving, and
denying join requests all go through `_require_company_admin(user_id,
company_id, …)`; membership creation on approval is scoped to that
`company_id`. Auto-association writes only the founder's own new company id.

**Isolation tests to add/confirm**:
- A user with email `@foo.example` calling `POST
  /companies/{bar_company_id}/join` (a company that owns `@bar.example`) receives
  404 `no_domain_policy` — never joins or reveals the other tenant.
- `GET /companies/suggestions` for a `@foo.example` user never returns a company
  associated only with `@bar.example`.
- A non-admin calling list/approve/deny join-requests receives 403 (existing
  guard; confirm still covered).

**Audit logging**: Auto-association emits a new
`company.domain_auto_associated` audit record; all existing join/approve/deny
paths already audit.

**Verdict**: No unjustified cross-tenant access. The one global lookup is an
explicitly-modeled, minimal-exposure, self-referential onboarding operation.
Constitution Check passes; no entries in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/055-domain-company-join/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (behavioral contracts)
│   └── domain-matching.md
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # /speckit-tasks (NOT created here)
```

### Source Code (repository root)

```text
packages/core/tessera_core/domain/
├── email_domain.py          # NEW: is_public_email_domain(), extract_domain()
└── entities.py              # (re-exports; add email_domain helpers if pattern used)

packages/core/tests/                     # NEW unit tests for email_domain

apps/api/tessera_api/routers/
└── companies.py             # MODIFY: create_company (auto-associate);
                             #         create_domain_policy (public-domain guard)

apps/api/alembic/versions/
└── XXXX_backfill_company_domains.py   # NEW: data-only backfill migration

apps/api/tests/
├── unit/                    # create_company auto-association branches
└── integration/
    └── test_companies.py    # extend: full match→join→pending→approve loop,
                             #         public-domain exclusion, isolation

apps/web/                    # NO CHANGES (flow already implemented)
```

**Structure Decision**: Existing monorepo layout. Business rule
(`is_public_email_domain`) added to the pure-Python domain package
(`packages/core/tessera_core/domain`) per Principle I; wiring lives in the
existing FastAPI router (`apps/api/tessera_api/routers/companies.py`). Frontend
(`apps/web`) is untouched.

## Complexity Tracking

No constitution violations. Section intentionally empty.
