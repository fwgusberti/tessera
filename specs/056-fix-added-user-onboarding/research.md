# Phase 0 Research: Admin-Added Members Onboarding Trap

The spec had no open `[NEEDS CLARIFICATION]` markers. "Research" here is the
root-cause investigation of the reported bug and the two design decisions it
surfaced. All findings are from the current codebase.

## Root-cause investigation

**Symptom** (reporter): a user added to a company by an admin, on login, cannot
see documents and is repeatedly redirected to onboarding and forced to create a
company.

**Trace of the login → gate path**:

1. `POST /v1/auth/login` (`routers/auth.py:186`) counts memberships via
   `list_memberships_for_user`. For the added user, count `== 1` → mints a
   **`full`** token auto-scoped to that company (`token_kind="full"`,
   `company_id=<the company>`). So the token layer is already correct — the added
   user is authenticated to the company.
2. Every full-token request hits the middleware in `auth/bearer.py`. At line 107
   it loads the user's `OnboardingProgress` and raises
   **`403 onboarding_required`** when `progress is None or
   progress.completed_at is None`. The added user's progress has
   `completed_at = None`, so **all their data-API calls 403** → "can't see
   documents."
3. Independently, the frontend `OnboardingGuard` (`apps/web/lib/auth-guard.tsx`)
   calls `GET /v1/onboarding/status`; `_status_response` reports
   `completed = progress.completed_at is not None` → `false` → redirect to
   `/onboarding` → the "create a company" step.

**Why `completed_at` is null for admin-added users**:
`add_company_member` (`routers/companies.py:292`) creates the `CompanyMembership`
but never advances or completes the target's onboarding. Compare:

| Path into membership | Sets onboarding completion? |
|----------------------|-----------------------------|
| Self-create company (`create_company` → user finishes `/onboarding/complete`) | Yes — `complete()` sets `completed_at`. |
| Approved join request (`approve_join_request:818`) | Advances to `"complete"`; `completed_at` set when the requester's browser lands on `/onboarding/complete`. |
| **Admin direct-add (`add_company_member`)** | **No — nothing at all.** |

**Conclusion**: `completed_at` is the wrong signal. Company membership is the
real "the user has a company" fact, and it is ignored by both gates.

## Decision 1 — Derive "onboarding satisfied" from membership (not just `completed_at`)

- **Decision**: Introduce a pure domain predicate
  `has_completed_onboarding(progress, has_company_membership) -> bool` that
  returns `True` when the user has any company membership OR
  `progress.completed_at` is set. Both gates (server `bearer.py`, status
  endpoint) consult it, supplying a live membership-existence check.
- **Rationale**:
  - Fixes the server gate and the frontend gate from a single source of truth.
  - **Recovers every already-trapped account with no data migration** (FR-006):
    the verdict is computed from live membership on each request, so the
    reporter's existing added user works on its next call with zero backfill.
  - Covers **all** membership paths uniformly (FR-005), including any future one.
  - Keeps FR-007 intact: a user with **zero** memberships and no `completed_at`
    still fails the gate and goes through normal onboarding.
- **Alternatives considered**:
  - *Backfill migration that sets `completed_at` for all current members* —
    rejected as the primary fix: it is a one-shot that does not prevent the class
    of bug recurring, and the derive approach makes it unnecessary. (Left as an
    optional truthfulness cleanup, out of scope.)
  - *Only patch `add_company_member` to call `complete()`* — rejected as
    insufficient alone: it fixes new adds but not the reporter's already-existing
    trapped account, and leaves the two gates still keyed on a fragile flag.

## Decision 2 — Also persist completion in `add_company_member` (belt-and-suspenders)

- **Decision**: In `add_company_member`, after creating the membership, mark the
  target's onboarding complete (create the progress row if missing, set
  `completed_at`, record `company_join_method` and `company_id`) and emit an
  `onboarding.completed` audit record for the target.
- **Rationale**: Satisfies FR-003 literally ("onboarding state MUST be updated"),
  keeps stored `onboarding_progress` truthful for reporting/analytics, and gives
  an explicit audit trail of when the added user became onboarded — mirroring the
  existing `approve_join_request` behavior. The derive-based gates (Decision 1)
  remain the load-bearing fix; this keeps data honest.
- **Alternatives considered**: *Derive-only, write nothing* — acceptable and
  simpler, but leaves stored progress permanently stuck at the `company` step for
  added users, which is misleading and lacks an onboarding audit event. The small
  extra write is worth the truthfulness.

## Decision 3 — Membership existence lookup

- **Decision**: Reuse the existing `SqlCompanyRepository.list_memberships_for_user`
  and test the returned list for non-emptiness. No new repository method.
- **Rationale**: The per-user membership set is tiny (typically 1–2 rows), the
  method is already used on the login hot path, and reuse minimizes surface area.
  An `EXISTS`-style `has_any_membership` is a possible micro-optimization but is
  not warranted at current scale; noted for future if profiling ever shows it.
- **Alternatives considered**: Adding `has_any_membership(user_id) -> bool` for a
  cheaper `SELECT EXISTS` — deferred; premature at this scale.

## Cross-cutting notes

- **No frontend change**: `OnboardingGuard` already routes into the app when
  `/v1/onboarding/status` reports `completed=true`; fixing the endpoint is
  sufficient.
- **Test markers** (per memory): core predicate tests live in `packages/core`
  under `pytest-asyncio`; API tests use `anyio` + `TestClient`. Do not mix.
- **Tenant isolation**: the added membership lookup is keyed on the caller's own
  `user_id`; no cross-tenant surface is introduced (see plan's Tenant Isolation).
