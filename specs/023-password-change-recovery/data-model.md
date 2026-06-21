# Data Model: Password Change and Recovery Flow

## New Domain Entity

### PasswordResetToken

Defined in `packages/core/tessera_core/domain/entities.py`.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | `UUID` | PK, default `uuid4()` | Surrogate key |
| `user_id` | `UUID` | FK → `users.id` CASCADE DELETE | Owning user |
| `token_hash` | `str` | `sha256(raw_token)`, 64 hex chars, unique | Hashed raw token (never store plain) |
| `created_at` | `datetime \| None` | UTC, server default `now()` | Issuance timestamp |
| `expires_at` | `datetime` | UTC, `created_at + 1h` | Hard expiry |
| `consumed_at` | `datetime \| None` | UTC, nullable | Set on first use or when superseded |

**State transitions**:
- `consumed_at is None AND expires_at > now()` → **valid**: may be used once
- `consumed_at is not None` → **consumed**: single-use exhausted or superseded by a newer token
- `expires_at ≤ now()` → **expired**: link lifetime exceeded

**Invariants**:
- At most one unconsumed, unexpired token exists per user at any given time (enforced by bulk-consuming prior tokens before INSERT)
- `token_hash` is globally unique (UNIQUE constraint on column)

---

## Existing Entity Extensions

### User (no schema change)

The `password_hash` column already exists (added in migration 0003). No new columns needed on `users`.

---

## Database Migration: 0005

File: `db/migrations/versions/0005_password_reset_tokens.py`

```sql
CREATE TABLE password_reset_tokens (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash   VARCHAR(64) NOT NULL UNIQUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at   TIMESTAMPTZ NOT NULL,
    consumed_at  TIMESTAMPTZ
);

CREATE INDEX ix_prt_user_active ON password_reset_tokens (user_id)
    WHERE consumed_at IS NULL;
```

**Index rationale**: `ix_prt_user_active` is a partial index covering only non-consumed tokens, which is the set queried when validating a reset link and when bulk-consuming prior tokens on re-issue.

---

## Redis Rate-Limit Keys (ephemeral, not system of record)

```
tessera:rate:reset:{sha256(client_ip)}
  Type: string (INCR counter)
  TTL:  900 seconds (15 minutes), set on first INCR
  Value: integer request count
```

These keys are **not** replicated to PostgreSQL and may be lost on Redis restart without security impact — the window simply resets.

---

## Audit Log Events

All events are appended to the existing `audit_records` table via `write_audit()`.

| Action | Actor type | Entity type | Metadata |
|--------|-----------|-------------|----------|
| `auth.password.change` | `user` | `user` | `{}` |
| `auth.password.reset_requested` | `anonymous` | `user` | `{"email": "<email>"}` |
| `auth.password.reset_completed` | `anonymous` | `user` | `{}` |

For `reset_requested` when the email is not found: the audit record uses the nil UUID (`00000000-...`) as `entity_id` (same pattern as failed login) and includes `{"email": "<email>", "found": false}` in metadata.

---

## Entity Relationship (affected tables)

```
users (existing)
  │
  ├─< refresh_tokens (existing)   — revoked in bulk on change/reset
  │
  └─< password_reset_tokens (NEW) — one active per user at most
```
