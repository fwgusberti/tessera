# Research: User & Company Onboarding

**Feature**: 007-user-company-onboarding | **Date**: 2026-06-15

---

## 1. Email Token Strategy

**Decision**: Use `itsdangerous.URLSafeTimedSerializer` (already in `apps/api/pyproject.toml`) for domain-verification email tokens. For team invitation tokens, generate `secrets.token_urlsafe(32)`, store its SHA-256 hash in the database (same pattern as `RefreshToken`).

**Rationale**:
- `itsdangerous` is already a declared dependency; adding no new dep for domain verification.
- Signed, timestamped tokens mean the verification token doesn't need a DB row — the link's signature + expiry are self-contained. Reduces state to manage.
- Invitation tokens need DB tracking (to query by company, revoke, track status) so the `secrets` + hash pattern matches the existing `RefreshToken` implementation exactly.

**Alternatives considered**:
- `PyJWT` for all tokens — rejected; `joserfc` already used for auth, mixing is confusing and `itsdangerous` handles link tokens more idiomatically.
- Storing domain verification token in DB — rejected; stateless signed tokens are simpler and already in the toolbox.

---

## 2. Transactional Email Service

**Decision**: Add `fastapi-mail>=1.4` as a new dependency to `apps/api/pyproject.toml`. Implement an `EmailPort` abstract class in `packages/core/tessera_core/ports/` and a concrete `FastMailEmailAdapter` in `apps/api/tessera_api/adapters/`. SMTP connection settings go in environment variables (never committed).

**Rationale**:
- `fastapi-mail` is async-native, wraps `aiosmtplib`, and integrates cleanly with FastAPI's DI. No new transport libraries needed.
- An `EmailPort` in the core ports layer keeps the domain decoupled from the concrete mailer — matches Tessera's DDD constitution requirement (Principle II: Separation of Concerns).
- Using the ports-and-adapters pattern means tests can inject a `FakeEmailAdapter` without mocking the SMTP layer.

**Alternatives considered**:
- `sendgrid-python` / `resend` SDKs — vendor SDKs add coupling to a specific provider. Rejected in favour of provider-agnostic SMTP + `fastapi-mail`.
- Python stdlib `smtplib` — synchronous; blocks the event loop. Rejected.

---

## 3. Onboarding Route Guard (Backend)

**Decision**: Implement a FastAPI dependency `require_onboarding_complete` that checks `onboarding_progress.completed_at IS NOT NULL` for the current user. Inject it into every non-onboarding, non-auth router. Return `HTTP 403` with `{"error": {"code": "onboarding_required", "message": "..."}}` if not complete.

**Rationale**:
- Dependency injection is the idiomatic FastAPI pattern (see existing `HTTPBearer` bearer check in `auth/bearer.py`).
- Returning a distinct error code (`onboarding_required`) lets the frontend redirect cleanly without parsing human-readable messages.
- 403 (not 302) keeps the API REST-pure; redirect logic belongs in the frontend.

**Alternatives considered**:
- Middleware-level check — harder to exclude specific routes cleanly (auth, onboarding itself). Rejected.
- Storing onboarding state in the JWT — complicates token refresh and adds stale-state risk. Rejected.

---

## 4. Onboarding Route Guard (Frontend)

**Decision**: Extend the existing `lib/auth-guard.tsx` to add an `OnboardingGuard` component. After authentication succeeds, it calls `GET /v1/onboarding/status`. If `completed: false`, it redirects to `/onboarding`. Applied in `app/layout.tsx` wrapping all non-auth, non-onboarding routes.

**Rationale**:
- Mirrors the existing auth guard pattern — consistent, minimal surface area.
- Single API call on initial load; result can be cached in React context for the session duration.

---

## 5. Domain Uniqueness Enforcement

**Decision**: Add a `UNIQUE` constraint on `domain_join_policies.domain` at the database level (via Alembic migration). Application layer also validates before insert and returns a user-friendly error if already claimed.

**Rationale**:
- Database-level constraint is the authoritative guard against race conditions (two admins claiming the same domain simultaneously).
- Application-layer pre-validation gives a better UX error message than a raw constraint violation.

---

## 6. Multi-Email Input (Frontend)

**Decision**: Implement a controlled textarea that accepts comma- or newline-separated email addresses. Parse, deduplicate, and validate client-side before the `POST /v1/invitations` call. No external tag-input library needed — plain Tailwind CSS + React state.

**Rationale**:
- Avoids adding a new npm dependency for a simple UX pattern.
- Comma/newline is a familiar convention (users copy-paste from spreadsheets, email clients).

---

## 7. Pending Join Request — Admin Notification

**Decision**: On join request submission, emit an `AuditRecord` (per constitution Section Security Requirements) and dispatch an email to all company administrators via the `EmailPort`. No push/websocket needed for MVP.

**Rationale**:
- Email notification matches the spec (FR-029) without requiring real-time infrastructure.
- AuditRecord covers the constitution's "every state-changing action MUST emit a structured audit log" requirement.

---

## 8. New Python Dependency

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi-mail` | `>=1.4` | Async transactional email (SMTP) |

No other new Python dependencies required.

No new npm dependencies required.
