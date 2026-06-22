# API Contracts: Tenant Isolation (031)

All tenant-scoped endpoints require the `require_company_context` dependency.
Company context is read from the JWT `company_id` claim or the session `active_company_id` cookie —
never from request bodies, query parameters, or URL path parameters (except the activation endpoint).

---

## New: Company Context Activation

### `POST /companies/{company_id}/activate`

Validates membership and promotes the company to the active context for the session.

**Path params**: `company_id` (UUID)  
**Auth**: JWT or session (no company context required — this endpoint sets it)  
**Body**: none

**Response 200**:
```json
{
    "token": "<jwt-string>",
    "company_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "company_name": "Acme Corp"
}
```

**Response 403**:
```json
{
    "error": {"code": "forbidden", "message": "Not a member of this company"}
}
```

---

## Modified: Space Endpoints

### `GET /spaces`
- **Before**: returned all spaces across all tenants
- **After**: returns only spaces belonging to `session.company_id`
- No request change. Response schema unchanged.

### `POST /spaces`
- **Before**: accepted an admin-only request to create a space with no tenant binding
- **After**: binds the new space to `session.company_id` (taken from session, not body)
- Request body: remove any `company_id` field if previously present (it was not)
- Response: `space` object now includes `company_id` field

### `GET /spaces/{space_id}`  *(future endpoint — currently not present, but applies when added)*
- Must validate `space.company_id == session.company_id`; return 403 otherwise

---

## Modified: Document Endpoints

### `GET /documents`
- **Before**: returned documents from all spaces visible to the user (via IDP groups) with no company gate
- **After**: returns only documents in spaces owned by `session.company_id`
- Query param `space_id` still accepted but validated: must belong to `session.company_id` or 403 is returned

### `GET /documents/{document_id}`
- **Before**: returned document by ID with no company check (404 for missing, but no 403 for wrong tenant)
- **After**: validates document's space belongs to `session.company_id`; returns 403 if not (without leaking existence)

### `POST /documents`
- **Before**: accepted any `space_id` in body
- **After**: validates `body.space_id` belongs to `session.company_id` before creating; 403 if not

### `POST /documents/{document_id}/publish`
- **After**: validates document belongs to `session.company_id` before publishing

### `POST /documents/{document_id}/reindex`
- **After**: validates document belongs to `session.company_id` before queuing

---

## Modified: Search & Assistant Endpoints

### `POST /search`
- **Before**: `allowed_space_ids = list_all()` — all tenants
- **After**: `allowed_space_ids = list_by_company(session.company_id)` — only session tenant
- `space_ids` filter in request body still honored but capped to company-owned IDs

### `POST /assistant/answer`
- **Before**: same gap as `/search`
- **After**: same fix — spaces restricted to `session.company_id`

---

## Unchanged Endpoints (No Isolation Change Required)

| Endpoint | Reason |
|----------|--------|
| `GET /companies/me` | Returns only the user's own memberships — already safe |
| `POST /companies` | Creates a new company for the user — no cross-tenant risk |
| `POST /companies/{id}/join` | Joins a specific company — isolation enforced by membership check |
| `GET /spaces/{id}/members` | Members endpoint — validated through `require_company_context` that space belongs to company |
| Auth endpoints (`/auth/*`) | Pre-company-context — no tenant data involved |
| Onboarding endpoints | Pre-company-context — no tenant data involved |

---

## Error Response for Cross-Tenant Access Attempt

All cross-tenant access attempts return the same response to avoid leaking entity existence:

**Response 403**:
```json
{
    "error": {
        "code": "forbidden",
        "message": "Access denied"
    }
}
```

The response is identical whether the entity does not exist or belongs to another tenant.
This satisfies FR-006: "The response MUST NOT disclose whether the entity exists in another company."
