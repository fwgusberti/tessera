# Quickstart / Validation: User Badge

Validates the feature end-to-end against the spec's user stories and success
criteria. See [contracts/](./contracts/) and [data-model.md](./data-model.md) for
details; this guide is a run/validation checklist, not implementation.

## Prerequisites

- API and web dev servers runnable per the repo's standard dev workflow.
- At least two known accounts: one **with** a display name, one **without**
  (email only). Accounts in two different companies are useful for the isolation
  check.

## Automated tests

**API** (`apps/api`, pytest + anyio):
```bash
cd apps/api && pytest tests/integration/test_auth_me.py -q
```
Expect: 200 with caller identity; `display_name: null` when unset; 401 without a
token; cross-account isolation cases pass (each caller sees only their own
identity).

**Web** (`apps/web`, Vitest):
```bash
cd apps/web && npx vitest run tests/identity.test.ts tests/UserBadge.test.tsx
```
Expect: initials derivation cases pass; badge hidden when unauthenticated; email
shown immediately; name/initials enrich after `/auth/me`; long values truncate
with full value in `title`.

## Manual validation

### Story 1 — See who I am signed in as (P1)
1. Sign in as the named account. → Badge appears in the top navigation showing
   the email, and the display name (SC-002, FR-001/FR-002/FR-003).
2. Navigate Chat → Documents → Spaces. → Badge stays visible and unchanged on
   every page (FR-003, SC-002).
3. Sign out. → Badge disappears (FR-004).
4. While signed out, load any page. → No badge shown (FR-004).

### Story 2 — Distinguish accounts at a glance (P2)
5. Sign in as account A; note the initials + label. Sign out; sign in as account
   B. → Badge label and initials change to reflect B, never A (FR-005, SC-003).

### Edge cases
6. **Missing name**: sign in as the email-only account. → Badge shows the email;
   initials derived from the email (spec "Missing name").
7. **Long identifier**: use an account with a long email. → Badge truncates
   within the bar without breaking layout; hovering reveals the full value
   (FR-008).
8. **Small screens**: narrow the viewport / open the mobile menu. → Badge remains
   present and legible in the mobile menu (FR-009, SC-005).
9. **Session expiry**: let the session end (or clear the token). → Badge is
   removed in step with being treated as signed out (spec "Session expiry").

### Isolation (SC-004)
10. Sign in as user A (company 1); confirm the badge shows A's identity. Sign in
    as user B (company 2); confirm B's identity. At no point does the badge (or
    `/auth/me`) surface the other account's identity — 0% cross-account leakage.

## Success-criteria mapping

| Criterion | Validated by            |
|-----------|-------------------------|
| SC-001    | Steps 1–2 (identity visible < 3s, email renders synchronously) |
| SC-002    | Steps 1–2 (badge on 100% of authenticated pages)              |
| SC-003    | Step 5 (reflects new account after switch)                    |
| SC-004    | Step 10 + API isolation tests                                 |
| SC-005    | Step 8 (desktop + mobile legibility)                          |
