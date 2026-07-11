# Implementation Plan: Admin-Added Members Skip the "Create a Company" Onboarding Trap

**Branch**: `056-fix-added-user-onboarding` | **Date**: 2026-07-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/056-fix-added-user-onboarding/spec.md`

## Summary

A person who is added to a company by an admin (the feature-054 "add user" flow)
becomes a real member, yet every login bounces them back into onboarding, hides
the company's documents, and forces them to create a company. Investigation
pinned the cause to **two onboarding gates that both key off
`OnboardingProgress.completed_at` while ignoring company membership entirely**:

1. **Server gate** — `apps/api/tessera_api/auth/bearer.py` runs on every
   full-token request and raises `403 onboarding_required` when
   `progress is None or progress.completed_at is None`. This is why the added
   user "can't see the documents": their data-API calls are rejected server-side.
2. **Frontend gate** — `apps/web/lib/auth-guard.tsx` (`OnboardingGuard`) calls
   `GET /v1/onboarding/status` and, when `completed` is false, redirects to
   `/onboarding`, which walks the user to the "create a company" step.

The direct-add endpoint (`add_company_member` in `routers/companies.py`) creates
the membership but **never touches the target's onboarding progress**, so
`completed_at` stays null and both gates trip. (By contrast, the approve-join and
self-create paths get `completed_at` set indirectly when the user's own browser
passes through `/onboarding/complete`.) Notably, the **token layer already
behaves correctly**: at login `list_memberships_for_user` count `== 1` mints a
`full`, company-scoped token — so the added user *is* authenticated to the
company; only the redundant onboarding-completion gates are wrong.

**Fix (surgical, migration-free): make company membership the authoritative
signal for "onboarding satisfied."**

- Add a pure domain predicate in `tessera_core` that answers "is onboarding
  satisfied?" from `(progress, has_company_membership)`.
- Both gates consult it: the server gate skips the 403 when the caller has any
  membership; the status endpoint reports `completed=true` when the user has any
  membership.
- Because both gates now **derive** from live membership, every existing trapped
  account (FR-006) recovers automatically on its next request — **no data
  migration is required** — and every membership path (create / approve / admin-
  add) is covered uniformly (FR-005).
- Belt-and-suspenders: `add_company_member` also **persists** onboarding
  completion for the target (mirroring the approve-join path) and emits an
  `onboarding.completed` audit record, so stored state stays truthful (FR-003).

No schema change. No frontend change (the existing `OnboardingGuard` already
reacts correctly once `/v1/onboarding/status` reports `completed=true`).

## Technical Context

**Language/Version**: Python 3.11 (backend, `apps/api` + `packages/core`).
TypeScript / Next.js exists (`apps/web`) but **needs no changes**.

**Primary Dependencies**: FastAPI, SQLAlchemy (async), Pydantic v2. Domain layer
(`tessera_core`) is pure Python — no framework/persistence imports.

**Storage**: PostgreSQL. Reads existing tables `company_memberships`,
`onboarding_progress`. No new tables, columns, or migration.

**Testing**: pytest. Core package uses `pytest-asyncio` (`@pytest.mark.asyncio`);
API package uses `anyio` (`@pytest.mark.anyio`) with
`fastapi.testclient.TestClient` for integration — do not mix the two markers
(per `feedback_async_markers`, `feedback_integration_testclient`).

**Target Platform**: Linux server (containerized).

**Project Type**: Multi-tenant web service (monorepo: `packages/core` domain,
`apps/api` FastAPI, `apps/web` Next.js).

**Performance Goals**: Onboarding/auth-time, per-request. The server gate already
performs one `onboarding_progress` lookup per full-token request; this adds one
indexed `company_memberships` lookup by `user_id` (typically 1–2 rows). No
throughput concern.

**Constraints**: Must not weaken tenant isolation — the membership check keys
strictly on the authenticated caller's own `user_id`. Must not admit a user who
belongs to no company (FR-007). Every state change keeps its audit record.

**Scale/Scope**: Small, well-bounded — 1 new pure-domain predicate + tests, 2
gate call-sites updated (`bearer.py`, `onboarding.py` status), 1 endpoint
augmented (`add_company_member`), companion API tests. No migration, no frontend.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

- **I. Domain-Driven Architecture** — PASS. The business rule ("a member has
  satisfied company onboarding") is expressed as a pure function in
  `tessera_core.domain.onboarding_progress`, free of framework/persistence
  imports. The API layer supplies the `has_company_membership` fact and consumes
  the verdict.
- **II. Separation of Concerns** — PASS. The onboarding-satisfaction policy is a
  domain concern; membership lookup stays behind the existing repository.
- **III. Data Locality & Consent** — N/A. No client-side persistence.
- **IV. Test-Driven Development (NON-NEGOTIABLE)** — PASS (planned). The domain
  predicate is written test-first; each gate change and the `add_company_member`
  augmentation ship with companion coverage. Per `project_test_env_baseline`, the
  repo-wide 85% API coverage gate is unreachable at the current baseline (~73%);
  we validate by covering the new/changed lines specifically, not the global gate.
- **V. Quality Gates** — PASS (planned). Ruff + Black clean before commit.
- **VI. Tenant Data Isolation (NON-NEGOTIABLE)** — PASS. See dedicated section.

### Tenant Isolation (mandatory)

**Tables accessed**: `company_memberships` (read: existence-by-`user_id`),
`onboarding_progress` (read/write: the target user's own row), `companies` (read
in the admin-add path, already scoped), `audit` (write).

**Every access is self- or admin-scoped**:

- The new membership existence check in the **server gate** keys strictly on the
  **authenticated caller's own** `user_id` (`UUID(user_info["sub"])`) — never on
  client-supplied input. It only answers "does *this* caller belong to *any*
  company," exposing no other tenant's data.
- The **status endpoint** likewise keys on the caller's own `user_id`.
- `add_company_member` already derives `company_id` solely from
  `CompanyAdminContext` (JWT/active-company claim), never from client input
  (Principle VI, unchanged). The added onboarding write targets only
  `body.user_id`'s own `onboarding_progress` row — not tenant-owned content — and
  is reached only after the existing admin gate.
- No cross-tenant read is introduced. A `full` token is only ever minted for a
  user with a verified membership (login `count==1`, or `select-tenant` which
  re-validates `get_membership`), so "has membership" cannot be spoofed to view
  another company's data. Document/company visibility remains governed by the
  unchanged `_resolve_company_membership` company-scoped guard (FR-008).

**Isolation tests to add/confirm**:

- A user who is a member of company A, when authenticated to A, can read A's
  documents but a request scoped to company B (which they do not belong to) still
  receives 403 `not_a_member` (existing guard; confirm unaffected).
- The membership existence check does not let a user with zero memberships pass
  the onboarding gate (FR-007): a no-company user still receives
  `403 onboarding_required` / `completed=false`.

**Audit logging**: `add_company_member` emits a new `onboarding.completed` audit
record for the target (in addition to the existing `company.member_added`). The
derive-only gate changes are pure reads and change no state.

**Verdict**: No unjustified cross-tenant access. The one added lookup is a
self-referential, minimal-exposure existence check. Constitution Check passes; no
entries in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/056-fix-added-user-onboarding/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (behavioral contracts)
│   └── onboarding-gate.md
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # /speckit-tasks (NOT created here)
```

### Source Code (repository root)

```text
packages/core/tessera_core/domain/
└── onboarding_progress.py   # MODIFY: add pure predicate
                             #   has_completed_onboarding(progress, has_company_membership)

packages/core/tests/
└── test_onboarding_progress.py   # NEW/EXTEND: predicate unit tests (pytest-asyncio pkg)

apps/api/tessera_api/auth/
└── bearer.py                # MODIFY: onboarding gate consults membership before 403

apps/api/tessera_api/routers/
├── onboarding.py            # MODIFY: _status_response / get_status derive `completed`
│                            #         from membership too
└── companies.py             # MODIFY: add_company_member persists target onboarding
                             #         completion + onboarding.completed audit

apps/api/tests/
└── integration/
    ├── test_companies.py    # EXTEND: admin-add → added user reaches app & documents;
    │                        #         no-company user still gated (FR-007); isolation
    └── test_onboarding.py   # EXTEND (or test_auth): status reports completed for a
                             #         member with null completed_at; server gate passes

apps/web/                    # NO CHANGES (OnboardingGuard already reacts to `completed`)
```

**Structure Decision**: Existing monorepo layout. The business rule
(`has_completed_onboarding`) is added to the pure-Python domain package per
Principle I; the two gates and the admin-add endpoint (all in the existing
FastAPI app) consume it. Frontend (`apps/web`) is untouched.

## Complexity Tracking

No constitution violations. Section intentionally empty.
