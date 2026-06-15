# Data Model: JWT Authentication

**Feature**: 004-jwt-auth  
**Date**: 2026-06-15

## Modified Entities

### User (modified)

**Location**: `packages/core/tessera_core/domain/entities.py` + `apps/api/tessera_api/adapters/models.py`

**Change**: Add optional `password_hash` field for local-credential users.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | PK, existing |
| `external_subject` | str | OIDC subject or email for local users, existing |
| `email` | str | unique, existing |
| `display_name` | str | existing |
| `is_admin` | bool | existing |
| `groups` | list[str] | existing |
| `default_language` | str | existing |
| `password_hash` | str \| None | **new** — bcrypt hash; NULL for OIDC-only users |
| `created_at` | datetime \| None | existing |

**Migration**: `ALTER TABLE users ADD COLUMN password_hash TEXT;` (nullable, no default)

---

## New Entities

### RefreshToken

**Location (domain)**: `packages/core/tessera_core/domain/entities.py`

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK → users.id |
| `token_hash` | str | SHA-256 of the raw token; 64 hex chars |
| `issued_at` | datetime | server-set on creation |
| `expires_at` | datetime | `issued_at + 7 days` (configurable) |
| `is_revoked` | bool | set to True on logout or rotation |

**Constraints**:
- `token_hash` is unique
- Index on `(user_id, is_revoked)` for fast lookup of active tokens per user

**Migration**:
```sql
CREATE TABLE refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(64) NOT NULL UNIQUE,
    issued_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL,
    is_revoked  BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX ix_refresh_tokens_user_active ON refresh_tokens (user_id, is_revoked);
```

---

## New Settings Fields

**Location**: `apps/api/tessera_api/config.py`

| Field | Type | Default | Notes |
|---|---|---|---|
| `jwt_access_token_expire_minutes` | int | 15 | Access token TTL |
| `jwt_refresh_token_expire_days` | int | 7 | Refresh token TTL |
| `jwt_algorithm` | str | "HS256" | Signing algorithm |

Signing key reuses the existing `secret_key` setting.

---

## Audit Events (new action codes)

All written to the existing `audit_records` table via `write_audit()`.

| `action` | `entity_type` | `actor_type` | Trigger |
|---|---|---|---|
| `auth.login.success` | `user` | `user` | Successful login |
| `auth.login.failure` | `user` | `anonymous` | Failed login attempt |
| `auth.logout` | `user` | `user` | Explicit logout |
| `auth.token.refresh` | `refresh_token` | `user` | Token refresh |
| `auth.register` | `user` | `anonymous` | New local user created |
