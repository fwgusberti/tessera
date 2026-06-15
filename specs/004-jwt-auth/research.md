# Research: JWT Authentication

**Feature**: 004-jwt-auth  
**Date**: 2026-06-15

## Decision 1: JWT Library

**Decision**: Use `authlib.jose` (already a project dependency via `authlib>=1.3`)

**Rationale**: `authlib` is already in `apps/api/pyproject.toml` and actively used for the OIDC OAuth2 client flow. Its `jose` module provides full JWT encoding/decoding with RS256 and HS256. Adding another library (`python-jose`, `PyJWT`) would be redundant.

**Alternatives considered**:
- `PyJWT` — minimal and battle-tested, but redundant given authlib is present
- `python-jose` — also redundant; has known CVEs in older versions
- Custom signing — not acceptable; wheel reinvention

## Decision 2: Password Hashing

**Decision**: Add `passlib[bcrypt]>=1.7` to `apps/api` dependencies.

**Rationale**: `passlib` with bcrypt is the industry standard for password hashing in Python. No equivalent is already present in the project.

**Alternatives considered**:
- `argon2-cffi` — more modern, but bcrypt has broader ecosystem support and works equally well
- `hashlib` (SHA-256) — cryptographically insufficient for password storage; rejected

## Decision 3: Signing Algorithm

**Decision**: HS256 (HMAC-SHA256) using the existing `settings.secret_key`.

**Rationale**: The project already manages a `secret_key` for session middleware. HS256 is appropriate for a single-service deployment where the signer and verifier are the same service. RS256 would be needed for multi-service token sharing, which is not a current requirement.

**Alternatives considered**:
- RS256 — appropriate for federation/multi-service, over-engineered for this scope
- ES256 — same as RS256 rationale

## Decision 4: Refresh Token Storage

**Decision**: Store refresh tokens in a new `refresh_tokens` PostgreSQL table (per constitution).

**Rationale**: Constitution mandates PostgreSQL as the single system of record. Redis would violate the rule that "durable, authoritative state MUST live in PostgreSQL." Refresh token revocation requires authoritative storage.

**Alternatives considered**:
- Redis — fast but violates constitution; state would be lost on flush
- In-memory — not viable; tokens must survive service restarts

## Decision 5: User Credential Strategy

**Decision**: Add `password_hash: Mapped[str | None]` to `UserModel`. Populate it on first login via a new `POST /v1/auth/register` endpoint (or seed script). The existing `external_subject` field remains for OIDC users; local-credential users will have `external_subject = email`.

**Rationale**: The `User` entity already exists with all required fields except password. Extending it is simpler than a separate credential entity. OIDC users and local users can coexist: OIDC users have no `password_hash`, local users have one.

**Alternatives considered**:
- Separate `UserCredential` entity — adds a table join on every auth check; unnecessary at this scale
- Keep OIDC-only and issue JWT after OIDC callback — possible but diverges from spec which requires email/password

## Decision 6: Token Expiry Defaults

**Decision**: Access tokens: 15 minutes. Refresh tokens: 7 days. Both configurable via `Settings`.

**Rationale**: 15-minute access tokens limit the exposure window of a stolen token. 7-day refresh tokens balance security (can be revoked server-side) with usability (users stay logged in for a week without re-entering credentials).

## Decision 7: Refresh Token Rotation

**Decision**: Single-use refresh tokens (token rotation). Each refresh issues a new refresh token and invalidates the old one.

**Rationale**: Matches FR-007 from spec. Prevents replay of stolen refresh tokens.

## Decision 8: Token Invalidation on Logout

**Decision**: Delete the `refresh_tokens` row on logout. Access tokens cannot be server-side invalidated (they expire in 15 min); logout clears the client-side token.

**Rationale**: Stateless access token revocation would require a block-list (additional complexity). A 15-minute window is acceptable for access tokens. Refresh token deletion immediately prevents new access token issuance.

## Decision 9: Endpoint Placement

**Decision**: New `auth` router at `apps/api/tessera_api/routers/auth.py`, mounted at `/v1/auth`.

**Rationale**: Follows existing router pattern. Auth is a first-class domain, not an adapter concern.

## Decision 10: Password Registration

**Decision**: Add `POST /v1/auth/register` endpoint for creating local users (email + password + display_name).

**Rationale**: The spec states users are "already registered" but the system needs a way to create local-credential users. A minimal register endpoint is required for the feature to be end-to-end testable. Registration is not the focus of the feature and can be locked down (admin-only or invite-only) later.
