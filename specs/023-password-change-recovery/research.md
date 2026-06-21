# Research: Password Change and Recovery Flow

## R-001 — Password Strength Validation Approach

**Decision**: Custom inline validator (no new library)

**Rationale**: The spec requires "at minimum 8 characters; no trivially weak patterns such as 'password' or sequences." A library like `zxcvbn` provides entropy scoring but adds ~100 KB of data files and introduces a new dependency. The stated requirement is a simple floor check, not a full entropy model. A small custom validator in `auth/password_strength.py` covering length, a static blocklist of ~20 common passwords, and an all-same-characters check satisfies FR-004 without widening the attack surface.

**Alternatives considered**:
- `zxcvbn-python`: Feature-rich, but overkill for the stated requirement and adds an unneeded dependency
- `password-strength` (PyPI): Simpler, but still an external dependency when a ~20-line function suffices

---

## R-002 — Rate Limiting Strategy

**Decision**: Manual Redis INCR + EXPIRE (no `slowapi` or similar)

**Rationale**: The project already declares `redis>=5.0` as a dependency and exposes `redis_url` in `Settings`. A single helper function using `redis.asyncio.from_url` with `INCR` + `EXPIRE` commands covers the requirement (5 requests / 15 min / IP) in ~15 lines. Adding `slowapi` would couple rate limiting to FastAPI middleware, making it harder to test in isolation and to silently accept over-limit requests (spec requires silent acceptance, not 429).

**Alternatives considered**:
- `slowapi` (FastAPI rate limiting middleware): Returns 429 by default; overriding to return 200 silently requires middleware hackery. Rejected.
- Database counter: Slower than Redis; violates the "Redis for ephemeral, PostgreSQL for durable" boundary. Rejected.

**Implementation key**: `tessera:rate:reset:{sha256(client_ip)}` — IP is hashed before use as a Redis key to avoid storing raw IPs in Redis (privacy + Data Locality principle).

---

## R-003 — Reset Token Format and Security

**Decision**: `secrets.token_urlsafe(48)` → SHA-256 stored in DB

**Rationale**: Follows the existing refresh-token pattern in the codebase (`hash_refresh_token` uses `hashlib.sha256`). 48 bytes = 288 bits of entropy, far exceeding OWASP recommendations (≥128 bits). URL-safe base64 encoding makes the raw token safe to embed in query parameters without further encoding.

**Alternatives considered**:
- UUID v4 as token: Only 122 bits and not URL-safe without encoding. Rejected.
- HMAC-signed token (like Django's password reset): Self-contained but more complex to implement and no advantage here since we store tokens in DB anyway. Rejected.

---

## R-004 — Session Invalidation Mechanism

**Decision**: Accept `refresh_token` in change-password request body; revoke all others; rotate current token

**Rationale**: The access token is short-lived (15 min) and stateless — it cannot be revoked. The only server-side session handle is the refresh token. Accepting the current refresh token mirrors the existing logout endpoint pattern and gives us a stable reference to the "current session." Rotating (revoke + reissue) the current token maintains session continuity while following the single-use rotation already enforced in `POST /v1/auth/refresh`.

For password reset, no `refresh_token` is available (the user is not logged in), so all tokens for the user are revoked and the user must re-authenticate.

**Alternatives considered**:
- Revoke all + return new token without requiring current refresh_token: Simpler API surface but requires the client to trust that the new token belongs to the same session. Rejected for clarity.
- Revoke all + log the user out: Breaks SC-006's requirement that "the current session remains valid" after a self-service password change. Rejected.

---

## R-005 — Email Non-enumeration Timing Defense

**Decision**: Dummy bcrypt call when email not found

**Rationale**: bcrypt is the dominant CPU cost in the login flow. If the reset handler returns immediately when the email is unknown, timing differences could reveal account existence. Performing `bcrypt.checkpw(b"dummy", stored_dummy_hash)` with a pre-computed hash equalises response time. This follows the identical pattern already used in `POST /v1/auth/login`.

**Alternatives considered**:
- Fixed `asyncio.sleep`: Fragile — actual bcrypt time varies with system load. Rejected.
- No timing equalisation: Violates SC-005. Rejected.

---

## R-006 — Frontend Routes and Account Settings Location

**Decision**: `/forgot-password` + `/reset-password` (new public pages); `/account` (new authenticated page)

**Rationale**: Existing public auth pages are at `/login` and `/register`. Adding `/forgot-password` and `/reset-password` at the same level is consistent. Account settings at `/account` is a standard convention; the existing nav bar can link to it once it exists. No `/account/security` sub-route needed for v1 (single-page account settings).

**Alternatives considered**:
- `/auth/forgot-password` nested route: Would require creating a shared auth layout. Unnecessary complexity. Rejected.
- Modal in nav bar for password change: Harder to deep-link; inconsistent with existing page-per-flow pattern. Rejected.
