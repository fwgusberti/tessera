# Data Model: Tenant-Scoped Authentication

## 1. New domain type: `TokenKind`

**File**: `packages/core/tessera_core/domain/token_kind.py`

```python
from typing import Literal

TokenKind = Literal["full", "select", "onboarding"]
```

| Value | Meaning |
|---|---|
| `"full"` | Fully scoped — carries `company_id`; all data-access endpoints accepted |
| `"select"` | Temporary — multi-membership user awaiting tenant selection; only `/auth/select-tenant` accepted |
| `"onboarding"` | Temporary — zero-membership user; only onboarding/join endpoints accepted |

---

## 2. Updated domain entity: `RefreshToken`

**File**: `packages/core/tessera_core/domain/refresh_token.py`

**New fields**:

| Field | Type | Default | Description |
|---|---|---|---|
| `company_id` | `UUID \| None` | `None` | Tenant scope of the credential; `None` for `select`/`onboarding` tokens |
| `token_kind` | `TokenKind` | `"full"` | Mirror of the access token kind; used at refresh time to re-issue same-scope access token |

---

## 3. Schema change: `refresh_tokens` table

**Migration**: `db/migrations/versions/0011_tenant_scoped_auth.py`

```sql
ALTER TABLE refresh_tokens
  ADD COLUMN company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
  ADD COLUMN token_kind VARCHAR(20) NOT NULL DEFAULT 'full';

CREATE INDEX ix_refresh_tokens_company ON refresh_tokens (company_id)
  WHERE company_id IS NOT NULL;
```

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `company_id` | UUID FK → companies | YES | `NULL` for `select` and `onboarding` tokens |
| `token_kind` | VARCHAR(20) | NO | Default `'full'` (safe upgrade for existing rows) |

---

## 4. Schema change: `companies` table

**Migration**: `db/migrations/versions/0011_tenant_scoped_auth.py` (same migration)

```sql
ALTER TABLE companies
  ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
```

| Column | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| `is_active` | BOOLEAN | NO | `TRUE` | `FALSE` → all credentials scoped to this company are rejected on next request |

---

## 5. JWT claim additions

No new DB table. JWT structure extended:

```json
{
  "sub": "<user_id>",
  "email": "user@example.com",
  "is_admin": false,
  "company_id": "<company_uuid>",
  "token_kind": "full",
  "iat": 1234567890,
  "exp": 1234567890,
  "jti": "<uuid>"
}
```

| Claim | Present when | Notes |
|---|---|---|
| `company_id` | `token_kind == "full"` only | Omitted for `select` and `onboarding` |
| `token_kind` | Always | One of `"full"`, `"select"`, `"onboarding"` |

---

## 6. Entity relationships (unchanged)

```
User (1) ──── (*) CompanyMembership (*) ──── (1) Company
                          │
                          └── role: CompanyRole (ADMIN | MEMBER)

User (1) ──── (*) RefreshToken
                          │
                          ├── company_id ──► Company (nullable)
                          └── token_kind: "full" | "select" | "onboarding"
```

---

## 7. Validation rules

- `company_id` in `RefreshToken` MUST be `None` when `token_kind != "full"`.
- A `full`-kind `RefreshToken` MUST carry a non-`None` `company_id`.
- When re-issuing an access token from a `select`-kind refresh token, the system MUST NOT infer a `company_id` from any other source.
- A membership check against `company_memberships` MUST succeed before any `full`-kind token is issued or refreshed.
- `companies.is_active` MUST be `TRUE` at the time of membership validation; an inactive company causes 403.

---

## 8. State transitions

```
                  Login
                    │
          ┌─────────┼──────────┐
   1 membership  0 memberships  >1 memberships
          │            │               │
       "full"     "onboarding"     "select"
      token           token          token
          │            │               │
          │       join company    POST /auth/select-tenant
          │            │               │
          │         "full"          "full"
          │          token           token
          └────────────┴───────────────┘
                    │
               Refresh (preserves kind + company_id)
```
