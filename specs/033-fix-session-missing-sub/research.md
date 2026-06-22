# Research: Fix Missing User Identity in Session After Company Activation

No external research was required. All questions were resolved by direct inspection of the codebase.

## Findings

### Finding 1 — Exact crash site

**Decision**: The crash is in `auth/bearer.py:81` (`user_id = UUID(user_info["sub"])`), triggered because `require_user` returns an incomplete session dict.

**Rationale**: `require_user` in `auth/oidc.py:53-55` returns the session's `"user"` dict immediately if it is truthy — no field validation. After `activate_company`, a JWT-only user's session dict is `{"active_company_id": "..."}`, which is truthy but lacks `sub`.

**Alternatives considered**: Validate `sub` presence inside `require_user` itself. Rejected: `require_user` is a general auth helper used by many endpoints; adding session field validation there would change its contract for OIDC users and is outside the scope of this fix.

---

### Finding 2 — Correct fix location for FR-001

**Decision**: Fix `activate_company` in `routers/companies.py` to populate the full identity dict when creating a new session user record.

**Rationale**: `user_info` (the resolved identity) is already available at that call site via `require_user(request)`. The fix is a 4-line addition with no side effects.

**Alternatives considered**: Fix `require_user` to fall through to JWT path if session dict lacks `sub`. Rejected: would change priority ordering (session wins) in an undocumented way, and would cause OIDC sessions without a `sub`-equivalent field to silently fall through to JWT, which is a security concern.

---

### Finding 3 — Defensive fix in the guard (FR-003)

**Decision**: Add an explicit `if "sub" not in user_info` check in `require_onboarding_complete`, raising HTTP 401.

**Rationale**: Defense-in-depth. Even after FR-001 prevents new malformed sessions, existing stale cookies from before the fix (or any other unexpected session state) should yield a structured 401 rather than a 500.

**Alternatives considered**: Wrap `UUID(user_info["sub"])` in a try/except `KeyError`. Rejected: `try/except` hides the type of error; an explicit `if` check is more readable and communicates intent.

---

### Finding 4 — No migration needed

**Decision**: No database schema changes.

**Rationale**: The session user record lives in the encrypted cookie (itsdangerous), not in PostgreSQL. Updating the session is automatic on the next write. Existing OIDC user sessions already contain `sub` (written at OIDC login time); they are unaffected.

---

### Finding 5 — Test infrastructure

**Decision**: Use `fastapi.testclient.TestClient` (sync), patch session via `client.cookies` or set session state directly using the TestClient's `session` parameter.

**Rationale**: Consistent with existing test patterns in `test_onboarding_gate.py` and `test_companies.py`. The session cookie for the activate-company test can be injected by calling `request.session` directly inside a mock, or by inspecting `request.session` state after the handler runs through a mock that captures it.
