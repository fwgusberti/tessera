# Data Model: User Roles (024)

## New Domain Entities

### SpaceRole (Enum)

Location: `packages/core/tessera_core/domain/entities.py`

| Value    | Description                                    |
|----------|------------------------------------------------|
| `VIEWER` | Read-only access to published documents        |
| `EDITOR` | Create, edit, and delete documents             |
| `ADMIN`  | All Editor capabilities + member management    |

Precedence order for privilege checks: `VIEWER < EDITOR < ADMIN`

---

### SpaceMembership (Entity)

Location: `packages/core/tessera_core/domain/entities.py`

| Field                | Type          | Constraints                           |
|----------------------|---------------|---------------------------------------|
| `id`                 | UUID          | PK, auto-generated                    |
| `space_id`           | UUID          | FK → spaces.id, NOT NULL              |
| `user_id`            | UUID          | FK → users.id, NOT NULL               |
| `role`               | SpaceRole     | NOT NULL                              |
| `invited_by_user_id` | UUID \| None  | FK → users.id, nullable               |
| `created_at`         | datetime \| None | server default now()               |
| `updated_at`         | datetime \| None | server default now(), onupdate     |

**Uniqueness**: `(space_id, user_id)` — a user holds exactly one role per space.

**Validation rules**:
- `role` must be a valid `SpaceRole` value.
- `user_id` must reference an active (non-deactivated) user.
- Removing or demoting the last ADMIN in a space is rejected by the service layer.

**State transitions** (role changes):
```
VIEWER → EDITOR  (requires actor ADMIN or global admin)
VIEWER → ADMIN   (requires actor ADMIN or global admin)
EDITOR → VIEWER  (requires actor ADMIN or global admin)
EDITOR → ADMIN   (requires actor ADMIN or global admin)
ADMIN  → EDITOR  (allowed only if at least 2 ADMINs remain)
ADMIN  → VIEWER  (allowed only if at least 2 ADMINs remain)
```

---

## Modified Domain Entities

### User (existing — no schema change)

`User.is_admin: bool` continues to represent Global Admin status. No new column needed. The spec's `PlatformRole.ADMIN` maps to `is_admin=True`; `PlatformRole.USER` maps to `is_admin=False`.

---

## Database Tables

### `space_memberships` (new table)

```sql
CREATE TABLE space_memberships (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    space_id     UUID         NOT NULL REFERENCES spaces(id) ON DELETE CASCADE,
    user_id      UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role         VARCHAR(20)  NOT NULL,
    invited_by_user_id UUID   REFERENCES users(id) ON DELETE SET NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_space_membership UNIQUE (space_id, user_id)
);

CREATE INDEX ix_space_memberships_space ON space_memberships (space_id);
CREATE INDEX ix_space_memberships_user  ON space_memberships (user_id);
```

Migration: `db/migrations/versions/0006_space_memberships.py`

---

## Audit Log Events

Reuses existing `audit_records` table via `AuditRecord` entity.

| Action                   | entity_type        | metadata keys                                  |
|--------------------------|--------------------|------------------------------------------------|
| `member_invited`         | `space_membership` | `space_id`, `user_id`, `role`                  |
| `role_changed`           | `space_membership` | `space_id`, `user_id`, `previous_role`, `new_role` |
| `member_removed`         | `space_membership` | `space_id`, `user_id`, `previous_role`         |
| `platform_role_changed`  | `user`             | `user_id`, `previous_is_admin`, `new_is_admin` |

---

## Permission Logic (domain layer)

Location: `packages/core/tessera_core/permissions/access.py`

New functions added alongside existing ones:

### `get_space_membership_role(user, space_id, memberships) → SpaceRole | None`
Returns the user's direct membership role in the space, or None if not a member.

### `effective_space_role(user, space_id, memberships) → SpaceRole | None`
If `user.is_admin`, returns `SpaceRole.ADMIN` (global admin is implicit space admin everywhere).
Otherwise delegates to `get_space_membership_role`.

### `can_write_document(user, space_id, memberships) → bool`
True if `effective_space_role ∈ {EDITOR, ADMIN}`.

### `can_manage_members(user, space_id, memberships) → bool`
True if `effective_space_role == ADMIN`.

### `can_read_space_document(user, space_id, memberships) → bool`
True if user is a member of the space (any role) or a global admin.

---

## Relationship Diagram

```
users ──────────────────┐
  │                     │
  │ (invited_by)        │
  ▼                     ▼
space_memberships ◄──── users
  │
  ▼
spaces
```

`space_memberships.user_id` → `users.id`  
`space_memberships.invited_by_user_id` → `users.id`  
`space_memberships.space_id` → `spaces.id`
