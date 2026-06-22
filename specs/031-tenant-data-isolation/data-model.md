# Data Model: Tenant Data Isolation (031)

## Schema Changes

### 1. `spaces` table — add `company_id`

```sql
-- Migration 0007
ALTER TABLE spaces ADD COLUMN company_id UUID REFERENCES companies(id) ON DELETE CASCADE;
-- Backfill: for any existing spaces, assign to the first company (or delete orphans)
-- Then enforce NOT NULL:
ALTER TABLE spaces ALTER COLUMN company_id SET NOT NULL;

CREATE INDEX ix_spaces_company ON spaces(company_id);
```

**Before:**
```
spaces(id, slug, name, sector, taxonomy, retention_policy, confidence_threshold, default_language, created_at, updated_at)
```

**After:**
```
spaces(id, company_id [FK→companies], slug, name, sector, taxonomy, retention_policy, confidence_threshold, default_language, created_at, updated_at)
```

No other tables require schema changes. `documents` and `chunks` are scoped by their `space_id` → `spaces.company_id` relationship.

---

## Domain Entity Changes

### `Space` entity (`packages/core/tessera_core/domain/entities.py`)

```python
# Before
class Space(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    slug: str
    name: str
    sector: str
    ...

# After
class Space(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    company_id: UUID          # NEW — owning tenant
    slug: str
    name: str
    sector: str
    ...
```

---

## Repository Interface Changes

### `SpaceRepository` (`packages/core/tessera_core/ports/repositories.py`)

New methods to add:

```python
class SpaceRepository(Protocol):
    async def list_by_company(self, company_id: UUID) -> list[Space]: ...
    async def get_by_id_for_company(self, space_id: UUID, company_id: UUID) -> Space | None: ...
    # list_all() retained but ONLY for internal/super-admin use — must not be called from user routes
```

### `DocumentRepository`

New methods to add:

```python
class DocumentRepository(Protocol):
    async def get_by_id_for_company(self, document_id: UUID, company_id: UUID) -> Document | None: ...
    async def list_by_space_ids_for_company(
        self, space_ids: list[UUID], company_id: UUID, state: DocumentLifecycleState | None = None
    ) -> list[Document]: ...
```

---

## JWT / Session Changes

### JWT claims — `create_access_token` signature change

```python
# apps/api/tessera_api/auth/jwt_auth.py
def create_access_token(
    user_id: UUID,
    email: str,
    is_admin: bool,
    company_id: UUID | None = None,   # NEW optional claim
) -> str: ...
```

JWT payload gains an optional `"company_id"` string claim. Absence means "no active company context" (valid for browsing `/companies/me` but blocked from tenant-scoped endpoints).

### Session cookie

The session user dict (`request.session["user"]`) gains:

```python
{
    "sub": "...",
    "email": "...",
    "is_admin": False,
    "active_company_id": "uuid-string | None"   # NEW
}
```

---

## New Auth Dependency

### `require_company_context` (`apps/api/tessera_api/auth/oidc.py`)

```python
async def require_company_context(request: Request) -> tuple[dict[str, Any], UUID]:
    """
    Extracts authenticated user + active company_id from JWT claim or session.
    Raises 401 if not authenticated.
    Raises 403 if no active company context is set.
    Returns (user_info, company_id).
    """
```

Used by all tenant-scoped route handlers as a replacement for `require_user`.

---

## New API Endpoint

### `POST /companies/{company_id}/activate`

**Purpose**: Validate user membership and set the active company context in the session and a fresh JWT.

**Request**: No body. `company_id` in path.

**Response** (200 OK):
```json
{
    "token": "<new-jwt-with-company_id-claim>",
    "company_id": "uuid",
    "company_name": "Acme Corp"
}
```

**Errors**:
- 401 if not authenticated
- 403 if user is not a member of `company_id`

**Side effects**:
- `request.session["user"]["active_company_id"] = str(company_id)` is set
- A new JWT with `"company_id"` claim is returned for stateless API clients

---

## State Transitions

### Company Context Activation Flow

```
User authenticates (login) 
    → JWT issued with NO company_id
    → User calls GET /companies/me to list their companies
    → User calls POST /companies/{id}/activate
    → Server validates membership
    → New JWT issued with company_id claim
    → Session cookie updated with active_company_id
    → All subsequent data requests use company_id from JWT/session
```

### Context Switch (multi-company user)

```
User calls POST /companies/{other_id}/activate
    → Server validates membership in other_id
    → New JWT with updated company_id
    → Session updated — previous company_id is replaced
    → FR-008: any cached state is invalidated (handled by client discarding old JWT)
```

---

## Entity Ownership Summary

| Table | Owned By | How Scoped |
|-------|----------|-----------|
| `companies` | — (top-level tenant) | `id = session.company_id` |
| `spaces` | Company | `company_id = session.company_id` (direct FK) |
| `documents` | Space → Company | JOIN `spaces` on `company_id` |
| `chunks` | Space → Company | `space_id IN (company's space IDs)` |
| `company_memberships` | Company | `company_id = session.company_id` |
| `role_permissions` | Space → Company | via space ownership |
| `space_memberships` | Space → Company | via space ownership |
| `connectors` | Space → Company | via space ownership |
| `invitations` | Company | `company_id = session.company_id` (already present) |
| `join_requests` | Company | `company_id = session.company_id` (already present) |
| `domain_join_policies` | Company | `company_id = session.company_id` (already present) |
