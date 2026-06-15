# Implementation Plan: JWT Authentication

**Branch**: `004-jwt-auth` | **Date**: 2026-06-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-jwt-auth/spec.md`

## Summary

Add JWT-based authentication (access + refresh tokens) to the Tessera API. Users register with email/password, log in via `POST /v1/auth/login`, and receive a signed JWT access token (15 min TTL) and a rotating single-use refresh token (7 days). All existing protected endpoints accept the JWT bearer alongside the current session cookie. Refresh tokens are stored in PostgreSQL; logout invalidates them immediately. Every auth event is written to the existing audit log.

## Technical Context

**Language/Version**: Python 3.12, FastAPI 0.115

**Primary Dependencies**:
- `authlib>=1.3` (existing) — JWT signing/verification via `authlib.jose`
- `passlib[bcrypt]>=1.7` (new) — password hashing
- `SQLAlchemy>=2.0`, `alembic>=1.13` (existing) — ORM and migrations
- `pydantic>=2.0` (existing) — request/response schemas

**Storage**: PostgreSQL — new `refresh_tokens` table; `password_hash` column added to `users`

**Testing**: pytest + pytest-asyncio (existing); new unit tests for JWT helpers and integration tests for auth endpoints

**Target Platform**: Linux server (existing stack)

**Project Type**: Web service (FastAPI)

**Performance Goals**: Login endpoint responds in < 500ms p95; token validation overhead < 5ms per request

**Constraints**:
- Backward compatibility: existing session-cookie auth must keep working during transition (additive change to `require_user`)
- No new external services; signing key is the existing `secret_key`
- Constitution mandates PostgreSQL for refresh token storage (no Redis)
- Coverage ≥ 85% on all new modules

**Scale/Scope**: 1 new router (4 endpoints), 2 domain entity changes, 1 Alembic migration, 2 new auth helpers, ~5 new test files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| **I. Domain-Driven Architecture** | ✅ Pass | JWT helpers and auth service live in `tessera_api` (infrastructure). `RefreshToken` and `User` domain entities stay in `tessera_core.domain`. No framework imports in core. |
| **II. Separation of Concerns** | ✅ Pass | Auth logic is in `tessera_api.auth.jwt_auth`; domain entities carry no FastAPI/SQLAlchemy dependencies. Swapping the JWT library only touches the infrastructure layer. |
| **III. Data Locality & Consent** | ✅ Pass | Passwords are never stored in plaintext; tokens are never persisted on the client beyond what the client explicitly sends back. No localStorage or client-side persistence introduced. |
| **IV. TDD (NON-NEGOTIABLE)** | ✅ Pass | JWT helper tests and auth endpoint tests are written test-first. Coverage ≥ 85% enforced by pytest-cov on all new modules. |
| **V. Quality Gates** | ✅ Pass | Ruff and Black checks run in CI; no exceptions introduced. |
| **Stack: PostgreSQL** | ✅ Pass | Refresh tokens stored in PostgreSQL (new table). Redis is not used for auth state. |
| **Stack: Infrastructure as Code** | ✅ Pass | No new containers. Migration is Alembic-managed. |
| **Security: Auth (OAuth2/JWT)** | ✅ Pass | This feature *implements* the mandate. Access tokens are HS256-signed JWTs; existing OIDC flow is preserved as an alternative path. |
| **Security: Secret Management** | ✅ Pass | Signing key is `settings.secret_key` (env-injected). No secrets committed. |
| **Security: Audit Logging** | ✅ Pass | All auth events (login, failure, logout, refresh, register) emit structured audit records via existing `write_audit()`. |
| **Documentation Separation** | ✅ Pass | `spec.md` is product-only; this `plan.md` carries all technical decisions. |

**Post-Phase 1 re-check**: All principles remain satisfied. Additive changes only; no existing boundaries violated.

## Project Structure

### Documentation (this feature)

```text
specs/004-jwt-auth/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── auth-api.md      # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code Changes

```text
packages/core/tessera_core/
└── domain/
    └── entities.py           # Add RefreshToken entity; add password_hash to User

apps/api/tessera_api/
├── auth/
│   ├── __init__.py
│   ├── bearer.py             # Existing (unchanged)
│   ├── oidc.py               # Existing; require_user updated to also accept JWT
│   └── jwt_auth.py           # NEW: create_access_token, verify_access_token,
│                             #      create_refresh_token, hash_token helpers
├── routers/
│   ├── auth.py               # NEW: /register, /login, /refresh, /logout
│   └── [existing routers]    # Unchanged
├── adapters/
│   ├── models.py             # Add RefreshTokenModel, password_hash col to UserModel
│   └── repo.py               # Add SqlRefreshTokenRepository
├── config.py                 # Add jwt_* settings fields
└── main.py                   # Include auth router

apps/api/alembic/versions/
└── xxxx_add_jwt_auth.py      # NEW migration

apps/api/tests/
├── auth/
│   ├── test_jwt_helpers.py   # Unit tests for jwt_auth.py helpers
│   ├── test_auth_register.py # Integration test for /register
│   ├── test_auth_login.py    # Integration test for /login
│   ├── test_auth_refresh.py  # Integration test for /refresh + rotation
│   └── test_auth_logout.py   # Integration test for /logout
└── [existing tests]          # Unchanged
```

## Complexity Tracking

> No constitution violations. Section left blank intentionally.
