# Research: Fix Create Company "Failed to fetch"

## Root-Cause Analysis

### Finding 1 — CORS wildcard + credentials is browser-rejected

**Decision**: Fix the CORS `allow_origins` setting to use an explicit origin instead of `*`.

**Rationale**:

Per the CORS specification (Fetch Living Standard §3.2.3) and all major browser
implementations, when a request is sent with `credentials: "include"` (or
`XMLHttpRequest.withCredentials = true`), the server's `Access-Control-Allow-Origin`
response header MUST be the exact request origin — the wildcard `*` is forbidden.

Current `apps/api/tessera_api/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else [],
    allow_credentials=True,   # ← credentials enabled
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Current `apps/web/lib/api.ts`:
```typescript
const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: "include",   // ← forces strict CORS credential mode
    headers,
});
```

When the browser sends `POST /v1/companies` (a cross-origin request from
`http://localhost:3000` to `http://localhost:8000`) it first sends an OPTIONS
preflight. If the server responds with `Access-Control-Allow-Origin: *` together
with `Access-Control-Allow-Credentials: true`, the browser immediately aborts the
preflight and throws `TypeError: Failed to fetch` before the actual POST is sent.

`getSuggestions()` suffers the same failure, but its error is silently caught
(`catch(() => setView("create"))`), so only the company-creation error is visible.

**Why `credentials: "include"` is necessary**: `require_user()` in `oidc.py` supports
a session-cookie path (OIDC/Google Workspace) via `request.session.get("user")`.
The `SessionMiddleware` sets a cookie, so `credentials: "include"` is needed for
that auth path to work. Removing it would break OIDC login.

**Fix**: Replace the wildcard with `[settings.frontend_url]`. The `frontend_url`
setting already defaults to `"http://localhost:3000"` (see `config.py`), matching
the Next.js dev server origin. In production it can be overridden via `FRONTEND_URL`
env var (already documented in deploy/docker-compose.yml).

**Alternatives considered**:
- `allow_origins=["*"]` and remove `allow_credentials=True`: would break the
  session-cookie auth path (OIDC login) — rejected.
- Remove `credentials: "include"` from the frontend: breaks session-cookie auth
  path — rejected.
- Add `CORS_ALLOWED_ORIGINS` as a separate setting: unnecessary indirection since
  `frontend_url` already captures this value — rejected.

---

### Finding 2 — Raw `TypeError: Failed to fetch` shown to users

**Decision**: Wrap the `fetch()` call in `api.ts` to translate `TypeError` network
errors to a human-readable message before they propagate to components.

**Rationale**:

`TypeError: Failed to fetch` is a browser-level error string that exposes internal
implementation details and gives users no actionable guidance. The spec requires:
- **FR-002**: Raw browser error strings MUST NOT be shown.
- **FR-004**: A human-readable, actionable message MUST be shown on failure.

The translation belongs in `api.ts` (the single API client used by all callers) so
that every callers benefits automatically — not in individual components.

The message `"Could not reach the server. Please check your connection and try again."`
is accurate (the request never reached the server) and actionable (user can retry or
check connectivity). It uses the same `error` pattern already in the client.

**Alternatives considered**:
- Translate per-component (CompanyForm, etc.): duplicated logic across every caller —
  rejected.
- Show a generic "Something went wrong" instead: loses the connection-problem signal,
  which is useful for diagnosing setup issues during development — rejected.

---

### Finding 3 — No other endpoint or schema changes required

The backend endpoint `POST /v1/companies` already exists and is correctly exempt from
the `require_onboarding_complete` guard (exempt pattern `r"^/v1/companies$"` with
`{"POST"}` in `bearer.py`). The route handler, repository, and domain entities are
correct. No database migration or schema change is needed.
