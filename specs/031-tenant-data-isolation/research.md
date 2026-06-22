# Research: Tenant Data Isolation (031)

## Current State Audit

### Critical Isolation Gaps Found

| Area | Gap | Severity |
|------|-----|----------|
| `spaces` table | No `company_id` column — spaces have no DB-level tenant owner | CRITICAL |
| `GET /spaces` | Calls `list_all()` — returns every company's spaces to any user | CRITICAL |
| `GET /search` | Calls `list_all()` then filters by user-supplied `space_ids` — no tenant gate | CRITICAL |
| `POST /assistant/answer` | Same as search — AI searches across all tenants' data | CRITICAL |
| `GET /documents/{id}` | Fetches document by ID with no company ownership check | HIGH |
| `POST /documents` | Accepts any `space_id` — no check it belongs to user's company | HIGH |
| `POST /documents/{id}/publish` | No company ownership verification | HIGH |
| `GET /spaces/{id}/members` | No check that space belongs to user's company | HIGH |
| JWT token | `company_id` not included in claims; session has no active company | HIGH |
| `Space` domain entity | No `company_id` field — cannot enforce isolation at domain layer | CRITICAL |

### What Already Exists

- `companies` table, `CompanyMembership`, `SqlCompanyRepository` — tenant model is built
- `SpaceMembership` table (from 006 migration) — user-space roles exist
- JWT auth + session cookie auth both implemented
- `require_user` dependency already returns authenticated user dict
- `SqlCompanyRepository.list_memberships_for_user()` — can look up user's companies

---

## Decision: Company Context in Session

**Problem**: FR-001 requires company context to come from the authenticated session, not from client-supplied parameters. The current session (`request.session["user"]` or JWT claims) contains no `company_id`.

**Decision: Dual-channel company context**

1. **JWT path**: `company_id` is added as a claim to the JWT. When a user activates a company, a fresh JWT is issued with that company's ID embedded. The claim is server-signed and cannot be forged by the client.

2. **Session-cookie path**: `active_company_id` is stored in the signed session cookie after company activation. The cookie is HttpOnly and signed by the server secret, so it cannot be altered client-side.

3. **Activation endpoint**: `POST /companies/{company_id}/activate` validates that the authenticated user is a member of `company_id`, then issues a new JWT and updates the session. The path parameter is used only to *select* which company to activate — all subsequent data-access reads exclusively from the server-side session/JWT, never from request bodies or query parameters.

**Rationale**: This satisfies FR-001 (session is the authority) while supporting both JWT-based API clients and cookie-based browser sessions. The `{company_id}` in the activation URL is an authentication action (like entering an OTP), not a data-access filter.

---

## Decision: Space-Company Ownership

**Problem**: The `spaces` table has no `company_id` column. There is no database-level link between a Space and its owning Company.

**Decision: Add `company_id` column to `spaces` table**

- Add `company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE`
- Migration 0007 adds the column as NULLABLE first, backfills existing rows if any, then adds NOT NULL constraint
- The `Space` domain entity gains a `company_id: UUID` field
- `SpaceRepository` gains `list_by_company(company_id)` and `get_by_id_for_company(space_id, company_id)` — bare `list_all()` is retained only for internal/super-admin use and must not be called from user-facing routes

**Rationale**: Direct FK on the table satisfies "explicit `company_id` filter" per Constitution §VI with a single predicate; no joins required for the most common query (list spaces by company). Documents and chunks derive their tenant scope via `space_id` → `spaces.company_id` join, avoiding denormalization.

---

## Decision: Document and Chunk Tenant Scoping

**Problem**: `documents` and `chunks` tables have no `company_id` column. Every document is accessed by bare ID with no company validation.

**Decision: Scope via space join; do not denormalize company_id onto documents/chunks**

- `SqlDocumentRepository.get_by_id_for_company(doc_id, company_id)` — JOINs to `spaces` to validate
- `SqlDocumentRepository.list_by_space_for_company(space_id, company_id)` — validates the space belongs to the company before listing
- `SqlChunkRepository.search()` already receives `space_ids`; callers must only pass company-owned space IDs

**Rationale**: Denormalizing `company_id` onto every document and chunk row creates update anomalies (what happens when a space moves?). The join is a single hop and adds minimal overhead. Chunk search already uses `space_id` filtering at the SQL level.

---

## Decision: What Changes in JWT Claims

Current `create_access_token` signature:
```python
def create_access_token(user_id: UUID, email: str, is_admin: bool) -> str
```

New signature:
```python
def create_access_token(user_id: UUID, email: str, is_admin: bool, company_id: UUID | None = None) -> str
```

- `company_id` is optional so that the initial login token (before company activation) remains valid for calling `/companies/me` and `/companies/{id}/activate`
- Once a company is activated, the client must use the new token with `company_id` claim for all tenant-scoped endpoints
- Tenant-scoped endpoints enforce `company_id` presence via a `require_company_context` dependency

---

## Decision: New `require_company_context` FastAPI Dependency

```python
async def require_company_context(request: Request) -> tuple[dict, UUID]:
    """Returns (user_info, company_id). Raises 401 if no company context."""
```

- Reads `company_id` from JWT claim OR from `request.session["user"]["active_company_id"]`
- Validates the user is still an active member of that company (DB check)
- Returns `(user_info, company_id)` for use in route handlers

All tenant-scoped endpoints use this dependency instead of bare `require_user`.

---

## Alternatives Considered

### URL-prefix scoping (`/companies/{company_id}/spaces`)
- **Rejected**: Company ID in URL is client-supplied. FR-001 explicitly prohibits this as the authority source. Could be used as a secondary validation but not as the primary isolation mechanism.

### Row-Level Security (PostgreSQL RLS)
- **Considered**: Constitution §VI mentions evaluating RLS as defense-in-depth
- **Not primary**: RLS requires setting `app.current_company_id` as a Postgres session variable before each query, which adds complexity to the SQLAlchemy async session setup. Recommended as a future hardening layer (see quickstart.md), not the primary enforcement mechanism for this feature.

### Denormalizing `company_id` onto documents and chunks
- **Considered**: Would make isolation filters on those tables trivial and enable RLS
- **Deferred**: Adds migration complexity and update anomaly risk. Can be added as a hardening step after primary isolation is proven correct by tests.
