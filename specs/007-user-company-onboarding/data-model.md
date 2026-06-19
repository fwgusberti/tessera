# Data Model: User & Company Onboarding

**Feature**: 007-user-company-onboarding | **Date**: 2026-06-15

---

## Overview

This feature adds five new domain entities and extends one existing entity. All persistent state lives in PostgreSQL. Domain entities (pure Pydantic) reside in `packages/core/tessera_core/domain/entities.py`; ORM models (SQLAlchemy) reside in `apps/api/tessera_api/adapters/models.py`.

---

## Existing Entity — Extension

### `User` (extended)

File: `packages/core/tessera_core/domain/entities.py`

New field added:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `title` | `str \| None` | No | Professional role/title (e.g., "Head of Engineering") |
| `onboarding_completed` | `bool` | Yes | Default `False`. Denormalised shortcut used by the JWT to avoid a join on every request. |

ORM change: `UserModel` gains `title: Mapped[str \| None]` and `onboarding_completed: Mapped[bool]` columns. New Alembic migration `0004_onboarding.py`.

---

## New Domain Entities

### `Company`

Represents an organisation created on Tessera.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | `UUID` | Yes | PK, default `uuid4` |
| `name` | `str` | Yes | Max 255 chars |
| `industry` | `str \| None` | No | Free-text or controlled vocab |
| `team_size` | `str \| None` | No | Range label e.g. "1-10", "11-50" |
| `admin_user_id` | `UUID` | Yes | FK → `users.id` (first creator) |
| `created_at` | `datetime` | Yes | Server default |
| `updated_at` | `datetime` | Yes | Server default, updated on write |

**Constraints**: No global uniqueness on `name` (companies can share names; domain policy is the differentiator). `admin_user_id` is NOT NULL.

**ORM table**: `companies`

---

### `CompanyMembership`

Join table between users and companies.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | `UUID` | Yes | PK |
| `user_id` | `UUID` | Yes | FK → `users.id CASCADE DELETE` |
| `company_id` | `UUID` | Yes | FK → `companies.id CASCADE DELETE` |
| `role` | `CompanyRole` enum | Yes | `admin` \| `member` |
| `joined_at` | `datetime` | Yes | Server default |

**Constraints**: `UNIQUE(user_id, company_id)` — a user belongs to a company exactly once.

**State transitions**:
- Created when: user creates a company (role=`admin`), accepts invitation (role=`member`), or approved join request (role=`member`).

**ORM table**: `company_memberships`

---

### `DomainJoinPolicy`

Domain ownership claim + join policy attached to a company.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | `UUID` | Yes | PK |
| `company_id` | `UUID` | Yes | FK → `companies.id CASCADE DELETE` |
| `domain` | `str` | Yes | e.g. `acme.com` (lowercase, no leading `@`). UNIQUE globally. |
| `policy` | `DomainPolicy` enum | Yes | `auto_join` \| `request_approval` |
| `verified` | `bool` | Yes | Default `False`; set `True` when admin clicks verification link |
| `created_at` | `datetime` | Yes | Server default |
| `verified_at` | `datetime \| None` | No | Set when verification completes |

**Constraints**: `UNIQUE(domain)` — one verified owner per domain globally.

**State transitions**:
- `verified=False` → `verified=True`: admin clicks email link (token signed by `itsdangerous`, 24h expiry).
- While `verified=False`, domain is never used for user matching.

**ORM table**: `domain_join_policies`

---

### `Invitation`

A pending invitation sent to a colleague email during onboarding or post-onboarding.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | `UUID` | Yes | PK |
| `company_id` | `UUID` | Yes | FK → `companies.id CASCADE DELETE` |
| `invited_by_user_id` | `UUID` | Yes | FK → `users.id SET NULL on delete` |
| `email` | `str` | Yes | Lowercase, normalised |
| `token_hash` | `str` | Yes | SHA-256 of the raw token sent in the email link. Unique. |
| `status` | `InvitationStatus` enum | Yes | `pending` \| `accepted` \| `expired` \| `cancelled` |
| `expires_at` | `datetime` | Yes | `created_at + 7 days` |
| `created_at` | `datetime` | Yes | Server default |
| `accepted_at` | `datetime \| None` | No | Set when recipient registers and accepts |

**Constraints**: `UNIQUE(token_hash)`. Soft-unique on `(company_id, email, status=pending)` enforced at application layer — prevents duplicate pending invitations to the same address.

**State transitions**:
- `pending` → `accepted`: recipient registers and uses the invitation link.
- `pending` → `expired`: checked at query time when `expires_at < now()`.
- `pending` → `cancelled`: inviting user or admin explicitly cancels.

**ORM table**: `invitations`

---

### `OnboardingProgress`

Tracks which onboarding steps a user has completed.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | `UUID` | Yes | PK |
| `user_id` | `UUID` | Yes | FK → `users.id CASCADE DELETE`. UNIQUE. |
| `completed_steps` | `list[str]` | Yes | Ordered list of step keys completed so far. Values: `profile`, `company`, `invite`, `complete`. |
| `current_step` | `str` | Yes | The step the user should be on next. |
| `company_join_method` | `str \| None` | No | Set when company step completes: `"created"` or `"joined"`. Drives completion screen variant. |
| `completed_at` | `datetime \| None` | No | Set when `complete` step is reached. |
| `created_at` | `datetime` | Yes | Server default |
| `updated_at` | `datetime` | Yes | Server default, updated on each step advance |

**Constraints**: `UNIQUE(user_id)` — exactly one progress record per user. Created automatically when a user first logs in (via `POST /v1/auth/login` response or a lazy-create on first `/v1/onboarding/status` call).

**ORM table**: `onboarding_progress`

---

## Entity Relationships Diagram (textual)

```
users (1) ──── (1) onboarding_progress
users (1) ──── (N) company_memberships
users (1) ──── (N) invitations [invited_by_user_id]

companies (1) ──── (N) company_memberships
companies (1) ──── (1..N) domain_join_policies
companies (1) ──── (N) invitations
```

---

## Enumerations

```python
class CompanyRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"

class DomainPolicy(str, Enum):
    AUTO_JOIN = "auto_join"
    REQUEST_APPROVAL = "request_approval"

class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class JoinRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
```

---

## Migration

**File**: `db/migrations/versions/0004_onboarding.py`

Operations (in order):

1. `ALTER TABLE users ADD COLUMN title VARCHAR(255)` (nullable)
2. `ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE`
3. `CREATE TABLE companies (…)`
4. `CREATE TABLE company_memberships (…)` with `UNIQUE(user_id, company_id)`
5. `CREATE TABLE domain_join_policies (…)` with `UNIQUE(domain)`
6. `CREATE TABLE invitations (…)` with `UNIQUE(token_hash)`
7. `CREATE TABLE onboarding_progress (…)` with `UNIQUE(user_id)`
8. Indexes:
   - `ix_company_memberships_user` on `company_memberships(user_id)`
   - `ix_invitations_company_status` on `invitations(company_id, status)`
   - `ix_invitations_email_status` on `invitations(email, status)`
