# Contract: Onboarding Gate & Status — Membership Satisfies Onboarding

Behavioral contract for the two gates changed by this feature. No new endpoints;
these describe the amended behavior of existing surfaces. `has_membership` means
the authenticated caller has ≥ 1 `company_memberships` row (keyed on their own
`user_id`).

## C1. Domain predicate (pure)

`has_completed_onboarding(progress, has_company_membership) -> bool`

| progress.completed_at | has_company_membership | result |
|-----------------------|------------------------|--------|
| set                   | any                    | `True` |
| `None` (or progress `None`) | `True`           | `True` |
| `None` (or progress `None`) | `False`          | `False` |

- Pure function, no I/O. Unit-tested in `packages/core`.

## C2. Server onboarding gate — `auth/bearer.py` (full tokens)

Applies to every non-exempt `full`-token request.

- **Given** the caller has ≥ 1 company membership,
  **When** the request reaches the onboarding gate,
  **Then** the gate does **not** raise, regardless of `completed_at`
  (data endpoints proceed to the normal company-scoped guard).
- **Given** the caller has **no** membership and no `completed_at`,
  **Then** the gate still raises `403 { "code": "onboarding_required" }`
  (unchanged behavior — FR-007).
- Non-`full` tokens (`select`, `onboarding`) are unaffected (still short-circuit
  at line ~98 and are handled by route-level `_resolve_company_membership`).
- The membership check keys strictly on `UUID(user_info["sub"])` — never client
  input (tenant isolation).

## C3. Onboarding status — `GET /v1/onboarding/status`

Response shape unchanged: `{ completed, current_step, completed_steps,
company_join_method }`.

- **Given** the caller has ≥ 1 membership,
  **Then** `completed == true` even if `completed_at` is null.
- **Given** no membership and null `completed_at`,
  **Then** `completed == false` (normal onboarding — FR-007).
- `current_step` / `completed_steps` / `company_join_method` continue to reflect
  the stored `OnboardingProgress`.

## C4. Admin direct-add — `POST /v1/companies/members` (augmented)

Existing behavior (create membership, `201`, `409 already_member`,
`company.member_added` audit, admin-gated via `CompanyAdminContext`) is
preserved. Added:

- **Given** an admin successfully adds user `U` to company `C`,
  **Then** `U`'s `OnboardingProgress` is marked complete (`completed_at` set,
  `company_join_method = "added"`, `company_id = C`; row created if absent),
  **And** an `onboarding.completed` audit record is written for `U`,
  **And** `U`'s next login is admitted straight into the app (C2 + C3 also hold
  independently via the membership branch).
- Persisting completion here is idempotent-safe: if `U` already has
  `completed_at`, the value is left/refreshed without error.

## C5. Documents visibility (unchanged, confirm no regression)

- **Given** `U` is a member of `C` and authenticated to `C` (full token),
  **Then** `U` can read `C`'s documents (C2 no longer blocks them).
- **Given** `U` requests resources scoped to company `B` where `U` is not a
  member,
  **Then** the unchanged `_resolve_company_membership` guard returns
  `403 { "code": "not_a_member" }` (FR-008 — the onboarding change grants no
  cross-tenant access).

## Test matrix (contract-level)

| # | Setup | Action | Expected |
|---|-------|--------|----------|
| 1 | `U` added to `C` by admin; `U` had null `completed_at` | `U` logs in, `GET /onboarding/status` | `completed=true`; no redirect |
| 2 | same `U` | `U` calls a documents endpoint (full token, scoped to `C`) | `200`, sees `C`'s docs (no `onboarding_required`) |
| 3 | `U'` registered, **no** company | `GET /onboarding/status` / any data call | `completed=false` / `403 onboarding_required` |
| 4 | admin adds `U` to `C` | inspect audit + `U` progress | `onboarding.completed` audit; `completed_at` set; `company_join_method="added"` |
| 5 | `U` member of `C` only | request scoped to `B` | `403 not_a_member` |
| 6 | predicate | truth table C1 | matches table |
