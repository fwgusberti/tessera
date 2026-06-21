# Implementation Plan: Password Change and Recovery Flow

**Branch**: `023-password-change-recovery` | **Date**: 2026-06-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/023-password-change-recovery/spec.md`

## Summary

Adds self-service credential management across three flows: (1) authenticated password change with current-session preservation, (2) email-based password reset request with rate limiting and non-enumeration response, and (3) reset-link consumption. Implemented using the existing DDD layering — new `PasswordResetToken` domain entity in `packages/core`, a new port method `EmailPort.send_password_reset`, a DB migration, three new API endpoints, and three new Next.js pages.

## Technical Context

**Language/Version**: Python 3.12 (API), TypeScript / Next.js 15 (frontend)

**Primary Dependencies**:
- API: FastAPI, SQLAlchemy (async), bcrypt, joserfc, fastapi-mail, redis (all existing)
- Frontend: Next.js 15, React, Tailwind CSS (all existing)
- No new dependencies required

**Storage**: PostgreSQL (password_reset_tokens table via migration 0005)

**Testing**: pytest (API unit + integration + contract), Vitest (frontend)

**Target Platform**: Linux server (API) + browser (frontend)

**Project Type**: Web application (backend API + Next.js frontend)

**Performance Goals**:
- Reset email delivered within 60 s under normal conditions (SC-002)
- Password change round-trip < 500 ms p95 (no external calls)

**Constraints**:
- No new production dependencies (all required libraries already declared)
- Rate limit window: 5 reset requests per 15 minutes per IP address, tracked in Redis (ephemeral — not system of record)
- Reset token TTL: 60 minutes from issuance
- 85% statement coverage (existing threshold)

**Scale/Scope**: Same user base as existing auth system; no multi-region concerns

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. DDD — domain logic in `packages/core` | PASS | `PasswordResetToken` entity goes in `tessera_core/domain/entities.py`; service logic in `tessera_core/services/`; port interface in `tessera_core/ports/repositories.py` and `providers.py` |
| II. Separation of concerns | PASS | Domain entity has no framework imports; ORM model in `apps/api/tessera_api/adapters/models.py` |
| III. Data Locality & Consent | PASS | No client-side persistence; reset tokens stored server-side only |
| IV. TDD (NON-NEGOTIABLE) | PASS | Unit tests written before implementation for all service logic |
| V. Quality Gates | PASS | All code passes Ruff + Black before commit |
| PostgreSQL as system of record | PASS | `password_reset_tokens` in PostgreSQL; Redis used only as ephemeral rate-limit counter |
| Caching / Redis ephemeral only | PASS | Rate-limit counters in Redis are not system of record |
| Infrastructure as code | PASS | No new infra; existing Docker + K8s manifests cover Redis and PostgreSQL |
| JWT auth on protected endpoint | PASS | `POST /v1/auth/change-password` requires Bearer token |
| Audit logging | PASS | All three flows emit structured audit records (FR-011) |
| UI: slate/indigo palette | PASS | All new frontend pages use `slate-*` neutral + `indigo-600` primary |
| Secret management | PASS | Mail credentials via env injection (existing pattern) |

## Project Structure

### Documentation (this feature)

```text
specs/023-password-change-recovery/
├── plan.md              ← This file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/           ← Phase 1 output
│   ├── api.md
│   └── frontend.md
└── tasks.md             ← Phase 2 output (/speckit-tasks)
```

### Source Code

```text
packages/core/
├── tessera_core/
│   ├── domain/
│   │   └── entities.py          ← Add PasswordResetToken entity
│   ├── ports/
│   │   ├── repositories.py      ← Add PasswordResetTokenRepository ABC
│   │   └── providers.py         ← Add send_password_reset() to EmailPort
│   └── services/
│       └── password_reset.py    ← NEW: PasswordResetService (token lifecycle)
└── tests/
    └── test_password_reset.py   ← NEW: unit tests for PasswordResetService

apps/api/
└── tessera_api/
    ├── adapters/
    │   ├── models.py            ← Add PasswordResetTokenModel ORM class
    │   ├── repo.py              ← Add SqlPasswordResetTokenRepository
    │   └── email.py             ← Add send_password_reset() to FastMailEmailAdapter
    ├── auth/
    │   ├── password_strength.py ← NEW: validate_password_strength()
    │   └── rate_limit.py        ← NEW: Redis-based rate limiter
    └── routers/
        └── auth.py              ← Add 3 new endpoints

apps/web/
└── app/
    ├── forgot-password/
    │   └── page.tsx             ← NEW: request reset form
    ├── reset-password/
    │   └── page.tsx             ← NEW: set-new-password form (reads ?token=)
    └── account/
        └── page.tsx             ← NEW: account settings with change-password form

db/migrations/versions/
└── 0005_password_reset_tokens.py ← NEW: password_reset_tokens table
```

**Structure Decision**: Follows existing web-application layout (Option 2 from template). New pages placed alongside existing `/login` and `/register` for consistency. Domain logic separated into `packages/core/tessera_core/services/password_reset.py` to enforce the DDD boundary — the service holds token-generation and validation logic; the FastAPI router is only a thin transport adapter.

## Complexity Tracking

No constitution violations. No exceptions required.

## Design Decisions

### Password Strength Validation
Custom validator in `apps/api/tessera_api/auth/password_strength.py` — no new library. Rules:
1. Length ≥ 8 characters
2. Not in a blocklist of ~20 known-weak passwords ("password", "12345678", "qwerty", "letmein", etc.)
3. Not all identical characters (e.g., "aaaaaaaa")

Same rules applied client-side (inline JS) and server-side (authoritative). **Rationale**: keeps the dependency surface flat; the spec's "at minimum 8 characters; no trivially weak patterns" does not require a full entropy scorer.

### Token Generation & Storage
Reset tokens follow the same pattern as refresh tokens:
- Generate: `secrets.token_urlsafe(48)` → opaque, URL-safe, 288 bits entropy
- Store: SHA-256 hash (same as `hash_refresh_token`)
- URL: `{frontend_url}/reset-password?token={raw_token}`

### Session Invalidation — Password Change
`POST /v1/auth/change-password` accepts the current `refresh_token` in the request body (same pattern as `POST /v1/auth/logout`). The handler:
1. Revokes **all** refresh tokens for the user except the submitted one
2. Rotates the submitted token (revoke + issue new)
3. Returns `{access_token, refresh_token, ...}` — client updates stored tokens

**Rationale**: The current session stays alive without a forced re-login; all other sessions are invalidated. Requiring the refresh token in the request body gives us a stable handle on which session is "current" without adding session-identity infrastructure.

### Session Invalidation — Password Reset Confirmation
Revokes **all** refresh tokens for the user. No new token issued. User is redirected to `/login`. **Rationale**: reset is initiated from outside an existing session; issuing a new session after reset without MFA would be a privilege escalation.

### Rate Limiting (Password Reset Request)
Redis `INCR` + `EXPIRE` per IP address:
- Key: `tessera:rate:reset:{client_ip}` (hashed with SHA-256 before storing)
- Limit: 5 requests per 15-minute window
- Behaviour on limit exceeded: silently accept — return the same 200 response, do not send email (FR-012 + SC-005)
- Redis key expiry is ephemeral; a Redis flush does not constitute a security breach

### Non-enumeration (Reset Request)
`POST /v1/auth/forgot-password` always returns HTTP 200 with a fixed body regardless of whether the email is registered. When the email is not found, the handler performs a dummy bcrypt operation to consume similar CPU time, then returns early without sending email. **Rationale**: prevents account existence probing (FR-009, SC-005).

### Token Invalidation on Re-issue (FR-008)
When a new reset token is created for a user that already has a pending token, all prior non-consumed tokens for that user are marked `consumed_at = now()` before inserting the new one. Implemented as a single UPDATE before the INSERT in `SqlPasswordResetTokenRepository.create()`.

### Email Port Extension
Add `send_password_reset(*, to: str, reset_url: str, expires_in_minutes: int) -> None` to `EmailPort` ABC and implement in `FastMailEmailAdapter`. **Rationale**: follows existing port/adapter pattern; `EmailPort` already has 4 methods using the same signature style.

### Frontend: "Forgot password?" link
Added to `apps/web/app/login/page.tsx` below the sign-in button, linking to `/forgot-password`. Matches the "Create account" link style already present.
