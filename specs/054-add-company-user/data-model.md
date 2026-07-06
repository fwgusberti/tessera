# Phase 1 Data Model: Add User on the Company User Management Page

This feature reuses existing entities and adds exactly **one persisted field**
(`invitations.role`). No new tables.

## Changed entity: Invitation

The pending record tying an email to a company until accepted. Gains a role so the
admin's choice survives to acceptance (FR-004, FR-011).

| Field              | Type                 | Notes                                                          |
|--------------------|----------------------|----------------------------------------------------------------|
| id                 | UUID (PK)            | unchanged                                                      |
| company_id         | UUID (FK companies)  | unchanged; the tenant boundary                                |
| invited_by_user_id | UUID \| null         | unchanged                                                      |
| email              | str(255)             | unchanged; stored lower-cased                                 |
| token_hash         | str(64), unique      | unchanged                                                      |
| status             | str(20)              | unchanged; `pending` / `accepted` / `expired` / `cancelled`   |
| **role**           | **str(20)**          | **NEW.** `admin` \| `member`. `NOT NULL`, server default `member`. Role granted on acceptance. |
| expires_at         | datetime (tz)        | unchanged                                                     |
| created_at         | datetime (tz)        | unchanged                                                     |
| accepted_at        | datetime \| null     | unchanged                                                     |

**Domain model** (`packages/core/.../domain/invitation.py`): add
`role: CompanyRole = CompanyRole.MEMBER`.

**Validation**: `role` must be a valid `CompanyRole` (`admin` | `member`);
defaults to `member` when the admin does not choose (FR-004, US3 scenario 3).

### Indexes / constraints (migration `0015`)

- Existing: `ix_invitations_company_status (company_id, status)`,
  `ix_invitations_email_status (email, status)`, `token_hash` unique — unchanged.
- **NEW** partial unique index `uq_invitation_pending_email` on
  `(company_id, lower(email)) WHERE status = 'pending'` — enforces at most one
  outstanding invitation per email per company (FR-008; the "concurrent adds" edge
  case). A concurrent second invite raises `IntegrityError`, mapped to the
  "already invited" outcome.

### Migration `0015_invitation_role`

- `down_revision = "0014"` (current head).
- **Up**: `ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'member'` on `invitations`;
  create the partial unique index above. Existing rows backfill to `member` via
  the default (backward compatible with the legacy bulk `POST /invitations`).
- **Down**: drop the index; drop the column.

## Reused entities (unchanged schema)

### Company Membership / Role

`company_memberships (id, user_id, company_id, role, joined_at)` with
`uq_company_membership (user_id, company_id)`. This feature **creates** rows here:

- Direct add → one row with the admin-chosen role, `company_id` from context.
- Invitation acceptance → one row with `invitation.role` (acceptance path change).

The unique constraint guarantees a single membership under concurrent adds
(FR-007, SC-005); `add_membership` maps a duplicate `IntegrityError` to the
"already a member" outcome.

### User

`users (id, display_name, email, ...)` — global identity table, **not**
tenant-owned. Read-only here:

- `get_by_email(email)` — invite path, to detect an already-member target.
- `search_addable_users(company_id, query)` — NEW read used by direct-add search;
  returns identity fields only for users **not** already in `company_id`.

### Company

`companies (...)` — read-only; the active `company_id` is the tenant boundary for
every write. Never sourced from client input.

## New repository port method

`CompanyRepository.search_addable_users(company_id: UUID, query: str, limit: int = 20) -> list[CompanyMemberMatch]`

- Reuses the existing `CompanyMemberMatch` value object (`user_id`,
  `display_name`, `email`).
- SQL (adapter): `SELECT users … WHERE (email ILIKE :q OR display_name ILIKE :q)
  AND id NOT IN (SELECT user_id FROM company_memberships WHERE company_id =
  :company_id) ORDER BY display_name LIMIT :limit`.

## State transitions

```
Invite by email:
  (no record) --admin invites (role R)--> Invitation{status=pending, role=R}
  Invitation{pending} --invitee accepts--> CompanyMembership{role=R} + Invitation{accepted}
  Invitation{pending} --expires_at passed--> treated as expired (existing behavior)

Direct add:
  (no membership) --admin adds existing user (role R)--> CompanyMembership{role=R}  [immediate]
```

No other state machines are introduced.
