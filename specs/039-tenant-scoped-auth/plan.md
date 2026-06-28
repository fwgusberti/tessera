# Implementation Plan: Tenant-Scoped Authentication

**Branch**: `039-tenant-scoped-auth` | **Date**: 2026-06-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/039-tenant-scoped-auth/spec.md`

## Summary

Add explicit tenant-scoping to every credential issued by the authentication system. A JWT access token will carry a `token_kind` claim (`full` | `select` | `onboarding`) and, when fully scoped, a `company_id` claim. Login resolves scope automatically for single-membership users, issues a temporary `select` token for multi-membership users who must call the new `POST /auth/select-tenant` endpoint, and issues an `onboarding` token for zero-membership users. Refresh tokens will persist scope server-side so the refresh flow preserves the original tenant context. All data-access guards already reject unscoped tokens via `_resolve_company_membership`; this feature adds the missing classification layer and the tenant-selection endpoint.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, SQLAlchemy (async), joserfc (JWT), bcrypt, PostgreSQL via asyncpg

**Storage**: PostgreSQL — `refresh_tokens` table gains `company_id` and `token_kind` columns; `companies` table gains `is_active` boolean

**Testing**: pytest-anyio (API package), pytest-asyncio (core package); FastAPI TestClient (sync) for integration tests

**Target Platform**: Linux server (Docker / Kubernetes)

**Project Type**: REST API (web-service)

**Performance Goals**: Credential issuance within current login/refresh latency budget (no measurable regression from membership check, which already runs at login)

**Constraints**: JWT must remain the credential format; no session-state for the tenant scope (scope encoded in the token itself); `company_id` must be derived server-side at issuance — never accepted as client input on data endpoints

**Scale/Scope**: Existing user/company scale; no new tables, only column additions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Domain-Driven Architecture ✅
- `TokenKind` is a domain concept defined in `tessera_core`
- `RefreshToken` domain entity extended with scope fields
- Auth logic stays in domain services / helper modules, not leaked into routers

### II. Separation of Concerns ✅
- JWT encoding/decoding isolated in `jwt_auth.py`
- OIDC guards (`oidc.py`) remain transport-layer; domain entities are technology-agnostic

### III. Data Locality & Consent ✅
- Token scope is stored server-side in `refresh_tokens`; no new client-side persistence

### IV. Test-Driven Development (NON-NEGOTIABLE) ✅
- Tests written before implementation for every FR and acceptance scenario
- Coverage must be maintained at or above the current baseline

### V. Quality Gates ✅
- All code passes Ruff and Black before commit

### VI. Tenant Data Isolation (NON-NEGOTIABLE) ✅

**Tables accessed by this feature:**
| Table | `company_id` scoping | Notes |
|---|---|---|
| `refresh_tokens` | new `company_id` column | nullable; set at issuance, read at refresh |
| `companies` | n/a (lookup by PK) | new `is_active` column checked in membership guard |
| `company_memberships` | `user_id` + `company_id` filter | already present; re-validated on every request |

**company_id scoping present on every query?** Yes — `_resolve_company_membership` validates membership on every guarded request.

**Cross-tenant isolation tests required:**
- `test_select_token_blocked_from_data_endpoints` — `select` token → 403 on all data-access routes
- `test_full_token_cannot_access_other_tenant_data` — `full` token for Company A → 403/empty on Company B resources
- `test_revoked_membership_rejects_existing_token` — revoke membership → next request with that token → 403
- `test_select_tenant_refuses_non_member_company` — `select` token + Company X (no membership) → 403
- `test_admin_scope_confined_to_active_tenant` — admin of Company A cannot perform admin ops on Company B

**Security requirement — Audit logging:**
- `auth.credential.issued` event added to `POST /auth/select-tenant` (actor, company_id, timestamp)
- Login already emits `auth.login.success`; extended to record `token_kind` in metadata

**Cross-tenant access exemptions:** None. No super-admin bypass in this feature.

## Project Structure

### Documentation (this feature)

```text
specs/039-tenant-scoped-auth/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   └── auth.yaml        ← Phase 1 output (OpenAPI fragment)
└── tasks.md             ← Phase 2 output (/speckit-tasks)
```

### Source Code

```text
db/migrations/versions/
└── 0011_tenant_scoped_auth.py      ← new migration

packages/core/tessera_core/
├── domain/
│   ├── token_kind.py               ← new: TokenKind literal
│   └── refresh_token.py            ← add company_id, token_kind fields

apps/api/tessera_api/
├── auth/
│   ├── jwt_auth.py                 ← add token_kind param to create_access_token
│   └── oidc.py                     ← expose token_kind/company_id; add require_select_token;
│                                      update _resolve_company_membership to gate on token_kind
├── adapters/
│   ├── models/
│   │   └── refresh_token.py        ← add company_id, token_kind columns
│   └── repositories/
│       └── refresh_token.py        ← update create/get_by_hash for new fields
└── routers/
    └── auth.py                     ← update login+refresh; add POST /auth/select-tenant

apps/api/tests/
├── auth/
│   ├── test_auth_login.py          ← extend: token_kind, zero/multi/single membership
│   ├── test_auth_refresh.py        ← extend: scope preservation across refresh
│   └── test_select_tenant.py       ← new: all FR-007 acceptance scenarios
└── test_tenant_auth_isolation.py   ← new: cross-tenant token enforcement tests
```

**Structure Decision**: Single web-service project (apps/api). Core domain types in packages/core. No new packages introduced.

## Complexity Tracking

No constitution violations.
