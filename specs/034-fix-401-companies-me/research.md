# Research: Fix 401 on Companies/Me After Login

## Decision 1 — Session Validity Check Strategy

**Decision**: Check `user.get("sub")` presence before returning a session dict as the authenticated identity.

**Rationale**: The `sub` claim (user ID) is the minimum identity needed by every downstream handler. A session dict without it cannot be used for authentication. Checking its presence at the session-extraction step is the least invasive guard: it keeps `require_user` as the single authority on "is this request authenticated" and makes incomplete sessions fall through to the next credential source (JWT Bearer).

**Alternatives considered**:
- Check for a specific set of required fields (`sub`, `email`, `is_admin`): Over-specified; `sub` is sufficient for all current uses.
- Validate session on write (in `activate_company`): Fix 033 already does this — new sessions will be complete. The guard in `require_user` is defense-in-depth for pre-033 cookies that are still in browser storage.
- Discard incomplete sessions by clearing them: Mutating the request session mid-request is a side effect in a read-only function. Keep the function pure.

## Decision 2 — Onboarding Gate Exemption for GET /companies/me

**Decision**: Add `GET /v1/companies/me` to the exempt patterns in `require_onboarding_complete`.

**Rationale**: `GET /companies/me` is a read-only metadata query that the root layout calls on every page, including onboarding pages. It returns the user's company memberships, which is empty during onboarding — exactly the correct response. Blocking it with 403 forces the frontend into an error state mid-onboarding. The spec (FR-003) mandates this exemption explicitly.

**Alternatives considered**:
- Move `GET /companies/me` to a different router that doesn't have `_onboarding_guard`: Would require restructuring router includes and could affect other guards or middleware; surgical exemption is simpler and more explicit.
- Return empty list by catching the 403 on the frontend: Leaks server errors into UI logic; backend should return the correct status code.

## No New Research Items

All NEEDS CLARIFICATION items resolved from code inspection:
- Auth order in `require_user`: confirmed session-first, JWT-second (oidc.py:51–77)
- Onboarding gate application: confirmed via `main.py:77` — companies router wrapped with `_onboarding_guard`
- Exempt patterns location: `bearer.py:63–69`
- Test pattern for session cookies: confirmed via `TestOnboardingGateIncompleteSession` — encode with `itsdangerous.TimestampSigner`
