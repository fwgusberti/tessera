# Quickstart & Validation: Add User on the Company User Management Page

Runnable validation of feature 054. Contract details live in
[contracts/add-users-endpoints.md](./contracts/add-users-endpoints.md) and
[contracts/invitation-acceptance-change.md](./contracts/invitation-acceptance-change.md);
schema details in [data-model.md](./data-model.md). This guide only shows how to
prove the feature works end-to-end.

## Prerequisites

- Local dev stack running (PostgreSQL + API + web), per the repo README.
- Migrations applied: `make migrate` (must include `0015_invitation_role`).
- A test company with a signed-in **admin** and at least one non-admin member.
- A second, already-registered user who is **not** a member of that company
  (for the direct-add path), and a fresh email address with no account
  (for the invite path).

## Setup

```bash
make migrate            # apply through 0015
make dev                # or the project's usual API + web run targets
```

## Backend validation (contract tests)

```bash
# API endpoint contracts + outcome matrix (admin/member/unauth, already-member,
# already-invited, no-such-user, malformed-email, send-failed)
uv run pytest apps/api/tests/unit/test_company_add_user_router.py -v

# Cross-tenant isolation: adds land only in the active company; directory search
# excludes current members and never leaks another company's roster
uv run pytest apps/api/tests/test_tenant_isolation.py -k "add_user or addable" -v

# Invitation role round-trips through the DB and is granted on acceptance
uv run pytest packages/core/tests -k "invitation_role" -v
uv run pytest apps/api/tests -k "accept and role" -v
```

Expected: all pass. New code fully covered (see plan's TDD note re: the API
package coverage baseline).

## Frontend validation

```bash
cd apps/web && npm test -- user-management-add
```

## Manual end-to-end scenarios

Sign in as the **company admin** and open **Users** (`/users`).

1. **Invite by email (US1)** — Click **Add user**, choose *Invite by email*, enter
   the fresh email, leave role = *Member*, submit. Expect an "invitation sent"
   confirmation. Then accept the invite as that person (`/onboarding/company?invite=…`)
   and confirm they now appear in the roster as a **member**.
2. **Direct-add existing user (US2)** — **Add user** → *Add existing user*, type a
   couple letters of the other registered user's name/email, pick them from the
   results, submit. Expect them to appear in the roster **immediately** as a
   member, with no acceptance step.
3. **Role choice (US3)** — Repeat either path with role = *Administrator*; confirm
   the new person shows as an **administrator** in the roster. Confirm the role
   selector defaults to *Member*.
4. **Duplicate guard (FR-007)** — Try to add someone already in the roster (both
   paths); expect a clear "already a member" message and no duplicate row.
5. **Already invited (FR-008)** — Invite the same fresh email twice; the second
   attempt reports "already invited", not a second pending invitation.
6. **Invalid email (FR-006)** — Enter `not-an-email`; expect a validation message
   and nothing sent.
7. **Admin-only, tenant-scoped (US4)** — Sign in as a **non-admin member**: the
   Add-user affordance is absent, and calling the endpoints directly returns 403.
   As a multi-company admin, confirm the add lands only in the **active** company.

## Success criteria mapping

| Criterion | Validated by |
|-----------|--------------|
| SC-001 invite by email, clear confirmation | Manual #1, invite contract test |
| SC-002 direct add appears immediately | Manual #2, `POST /companies/members` test |
| SC-003 only active company affected | tenant-isolation tests, Manual #7 |
| SC-004 non-admin/unauth denied, no writes | endpoint 403/401 tests, Manual #7 |
| SC-005 no duplicate membership | `uq_company_membership` test, Manual #4 |
| SC-006 added user holds chosen role | role tests, Manual #3 |
| SC-007 unambiguous outcome message | outcome-matrix test, Manual #1–#6 |
