# Research: Tenant-Scoped Authentication

## 1. Token-kind classification approach

**Decision**: Add a `token_kind` string claim to JWT access tokens with values `"full"`, `"select"`, `"onboarding"`.

**Rationale**: Encoding intent in the token itself avoids an extra DB call on every request. The three states map directly to the three login outcomes (single membership → `full`, multi → `select`, zero → `onboarding`). This is the same pattern used by OAuth 2.0 step-up flows and SAML partial-auth tokens.

**Alternatives considered**:
- *DB lookup on each request*: verify membership count at request time to infer token type. Rejected — adds latency on every call and creates TOCTOU risk if memberships change between issuance and lookup.
- *Separate endpoint for each token type*: issue tokens from different paths. Rejected — unnecessary proliferation of endpoints; the single `/auth/login` already resolves the right kind.
- *Implicit inference from presence/absence of `company_id`*: use `company_id == null` as the "unscoped" signal. Rejected — can't distinguish `select` (multi-membership) from `onboarding` (zero-membership) without a DB call, which is needed to enforce different allowed-endpoint sets.

---

## 2. Refresh token scope preservation

**Decision**: Add `company_id UUID nullable` and `token_kind VARCHAR(20) NOT NULL DEFAULT 'full'` columns to the `refresh_tokens` table. Set these at token issuance; read them at refresh time to re-issue an access token with identical scope.

**Rationale**: The refresh token is server-side and opaque — storing scope there is the only tamper-proof way to persist it without requiring the client to re-submit the old access token on every refresh. A new DB column is a one-migration cost with zero ongoing request-path overhead.

**Alternatives considered**:
- *Require old access token when refreshing*: common in some OAuth flows. Rejected — breaks all existing refresh clients and contradicts the spec assumption that refresh policies are unchanged.
- *Re-evaluate memberships on refresh*: query memberships at refresh time; auto-scope if now single-member. Rejected — a user who logged in as multi-member, selected a tenant, and now refreshes would lose that selection if a second membership was added in the interim.
- *Store scope in opaque refresh token payload (HMAC-signed)*: encode scope in the refresh token string itself. Rejected — adds decoding complexity; the hashed token string is already the lookup key; attaching a signed payload makes it a JWT and loses the simplicity of the current design.

---

## 3. Tenant-selection endpoint design

**Decision**: `POST /v1/auth/select-tenant` accepts a `select`-kind access token (Bearer) and a `{ "company_id": "..." }` request body. Validates active membership, issues a `full`-kind access token and a new scoped refresh token. Returns the same response shape as `/auth/login`.

**Rationale**:
- FR-007 requires rejecting unauthenticated calls AND rejecting already-`full`-scoped tokens — a dedicated endpoint with its own guard is the cleanest enforcement point.
- Same response shape as login means clients can handle both flows with one code path.
- Issuing a new refresh token (scoped to the selected company) at this step prevents the user from carrying forward an unscoped refresh token that could be replayed.

**Alternatives considered**:
- *PATCH on the existing access token*: no standard mechanism; tokens are immutable once issued.
- *Accept company_id as a query parameter*: query params are logged by many proxies — leaks tenant ID in access logs. Rejected.
- *Combine with refresh endpoint (`POST /auth/refresh` + optional `company_id`)*: ambiguous semantics; mixes two distinct operations. Rejected.

---

## 4. Company deactivation check (FR-006)

**Decision**: Add `is_active BOOLEAN NOT NULL DEFAULT TRUE` to `companies` table. Extend `_resolve_company_membership` to reject requests when `company.is_active IS FALSE` with 403 `company_suspended`.

**Rationale**: FR-006 explicitly requires rejecting credentials for deactivated tenants. Adding a boolean flag is the minimal viable mechanism; it does not require a soft-delete or status-enum at this stage.

**Alternatives considered**:
- *Status enum (active/suspended/deleted)*: more expressive but not required by this spec. Deferred to a future feature.
- *Check at token issuance only*: an inactive company could be reactivated; checking only at issuance would accept stale credentials. Rejected — FR-006 requires per-request validation.

---

## 5. Guard enforcement for `select` tokens

**Decision**: Update `_resolve_company_membership` to check `token_kind`. If `token_kind == "select"` or `token_kind == "onboarding"`, raise 403 with code `credential_not_scoped` before the company-context check. The tenant-selection endpoint uses a dedicated `require_select_token` dependency that inverts this logic — it accepts only `select` tokens.

**Rationale**: The existing guard already returns 403 when `company_id` is absent from the JWT. Adding an explicit `token_kind` check makes the error code more descriptive and prevents any accidental future path where a `select` token might carry a `company_id` (e.g., a bug in the issuance path).

**Alternatives considered**:
- *Global middleware*: intercept all requests, check `token_kind`, route accordingly. Rejected — FastAPI dependencies already provide per-route enforcement; middleware would need to exempt public routes manually.
- *No extra check, rely on `company_id` absence*: already enforced by `_resolve_company_membership`. Rejected — loses distinguishability of error codes and makes future endpoint allowlisting harder.

---

## 6. Audit logging for credential issuance

**Decision**: Emit `auth.credential.issued` via `write_audit` in `POST /auth/select-tenant`. Update `/auth/login` to include `token_kind` in the existing `auth.login.success` metadata. No new audit table needed.

**Rationale**: Existing `audit_records` table already serves all audit logging. FR-009 requires actor, tenant, and timestamp — all captured by `write_audit(actor_type="user", actor_id=..., action="auth.credential.issued", entity_type="company", entity_id=company_id)`.

---

## 7. `require_onboarding_complete` guard interaction

**Decision**: Keep `require_onboarding_complete` as-is (DB-based check on `onboarding_progress`). Do not replace with a `token_kind` check.

**Rationale**: The onboarding guard covers the case where a user has a company but has not completed the multi-step onboarding wizard. This is orthogonal to zero-membership (`onboarding` token kind). Removing the DB check would require migrating the concept of "onboarding complete" into the JWT, which is a separate refactor. The current DB check is one extra query on onboarding-exempt paths only.

**Alternatives considered**:
- *Replace DB check with `token_kind == "onboarding"` check*: cleaner and faster. Rejected for this feature — would remove the onboarding-wizard gate concept, which is a deliberate product constraint tracked separately.
