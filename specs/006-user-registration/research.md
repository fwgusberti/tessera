# Research: New User Registration

**Feature**: 006-user-registration | **Date**: 2026-06-15

## Decision Log

### 1. Password Strength Meter Library

**Decision**: No external library — inline scoring function in `register/page.tsx`

**Rationale**: The strength meter is informational only (non-blocking). A simple heuristic (length + character class count) requires < 20 lines of TypeScript. Adding a library (e.g., `zxcvbn`, `check-password-strength`) for purely cosmetic feedback would increase bundle size with no functional benefit, since the backend only enforces an 8-character minimum.

**Alternatives considered**:
- `zxcvbn` (~800 KB unminified): overengineered for a non-blocking hint
- `check-password-strength` (lightweight): still an extra dep for < 20 lines of logic

**Scoring heuristic**:
```
weak   → length < 8 (will already be blocked by FR-003 validation)
medium → length ≥ 8, one character class only
strong → length ≥ 12  OR  (length ≥ 8 AND ≥ 2 character classes including uppercase, digit, or symbol)
```

---

### 2. Auto-login after registration

**Decision**: Call `login({ email, password })` from `useAuth()` immediately after the register API call succeeds.

**Rationale**: The `POST /v1/auth/register` endpoint returns a user object (confirmed from `apps/api/tessera_api/routers/auth.py`) but does not return JWT tokens. The simplest way to obtain a session is to immediately call the existing `authLogin` flow via the `login` method already exposed by `useAuth`. The email and password are already held in component state.

**Alternatives considered**:
- Modify the backend register endpoint to also return tokens: out of scope, requires backend change, and the spec assumption already confirms this pattern.
- Redirect to login page after registration: worse UX (extra page, user must re-enter password).

---

### 3. Display name max-length client-side enforcement

**Decision**: Validate `displayName.trim().length > 100` client-side and show an inline error.

**Rationale**: The backend's `RegisterRequest.display_name` field has `max_length=100` (pydantic `Field(max_length=100)`). Without client-side enforcement a user could type a very long name and receive a cryptic 422 from the server. The spec (FR-003, clarification Q3) explicitly confirmed this should be caught client-side.

---

### 4. Redirect parameter — reuse login page predicate

**Decision**: Use the identical safety predicate from `apps/web/app/login/page.tsx`: `redirect && redirect.startsWith("/") && !redirect.startsWith("//")`.

**Rationale**: Consistency and security. The login page already has a validated, tested implementation of this pattern. Diverging would create two different security postures for the same concern.

---

### 5. No new dependencies required

All implementation uses:
- Next.js App Router (already in project)
- React hooks (already in project)
- Tailwind CSS (already in project)
- Existing `lib/api.ts`, `lib/auth.tsx`, `lib/types.ts`
- Vitest + @testing-library/react (already in project)
