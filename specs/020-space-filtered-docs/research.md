# Research: Space-Filtered Document Listing

## 1. Current Behaviour of the Two Stubs

### Decision
`SqlSpaceRepository.list_for_user()` currently delegates to `list_all()`, ignoring the user argument. `GET /v1/documents` with no `space_id` returns `docs = []`. Both must be fixed for this feature.

### Rationale
Identified by reading `apps/api/tessera_api/adapters/repo.py:236-237` and `apps/api/tessera_api/routers/documents.py:47-49`.

### Alternatives considered
None — these are plainly incomplete stubs.

---

## 2. User Group Resolution Strategy

### Decision
Resolve accessible spaces via a single SQL JOIN:

```sql
SELECT DISTINCT s.*
FROM spaces s
JOIN role_permissions rp ON rp.space_id = s.id
WHERE rp.idp_group = ANY(:user_groups)
```

For `is_admin = True`: call `list_all()` (all spaces).

### Rationale
A single round-trip query is more efficient than loading all spaces and all permissions into Python for filtering. The rule (`idp_group ∈ user.groups`) is exactly what `resolve_user_role()` in `permissions/access.py` models — the SQL JOIN is the DB-efficient expression of the same invariant.

### Alternatives considered
- **Load all RolePermissions and filter in Python**: Correct, but O(spaces × permissions) with multiple DB calls. Worse at scale.
- **Add a domain service for space resolution**: Possible, but the access logic is already defined in `access.py`; a second encoding would duplicate it. The SQL JOIN lives in the adapter (infrastructure) layer — domain stays clean.

---

## 3. Cross-Space Document Fetch Strategy

### Decision
Add `list_by_space_ids(space_ids: list[UUID], state: … | None) -> list[Document]` to `DocumentRepository` (port) and implement it with:

```sql
SELECT * FROM documents WHERE space_id = ANY(:space_ids) [AND state = :state]
```

### Rationale
Single query is preferable to N×`list_by_space()` calls. Adding a new port method keeps the domain contract explicit. `ANY(:space_ids)` maps cleanly to SQLAlchemy's `DocumentModel.space_id.in_(space_ids)`.

### Alternatives considered
- **Call `list_by_space()` in a loop**: Works for small N, but produces N DB round-trips.
- **Inline raw SQL directly in the router**: Violates DDD separation (infrastructure in presentation layer).

---

## 4. How to Obtain the User's Groups Inside the Router

### Decision
`require_user(request)` returns a minimal dict (`sub`, `id`, `email`, `is_admin`). Groups are stored in the `users` table (`ARRAY(String)`). To get groups, call `SqlUserRepository.get_by_subject(user_info["sub"])` inside the same DB session.

### Rationale
JWT tokens in Tessera do not embed groups (confirmed from `auth/jwt_auth.py` claims structure). The `users.groups` column is already kept up to date by `SqlUserRepository.upsert()` on every login. No new infrastructure needed.

### Alternatives considered
- **Embed groups in JWT**: Requires token size increase + token rotation on group changes. Out of scope for this feature.
- **Separate `/me/groups` call from the router**: Extra round-trip and complexity with no benefit.

---

## 5. Frontend: State Machine for the Documents Page

### Decision
Three cases in `DocumentsPage`:
1. **Mount (no space selected)**: fetch `GET /v1/documents` → auto-populates the list.
2. **Space selected**: fetch `GET /v1/documents?space_id={id}` → filters list.
3. **Space cleared**: fetch `GET /v1/documents` again → restores cross-space list.

A single `fetchDocuments(spaceId: string | null)` helper is called by `useEffect` on mount and whenever `selectedSpaceId` changes (including being reset to `null`).

### Rationale
The existing two-`useEffect` pattern (one for spaces load, one for docs gated on `selectedSpaceId`) only needs the second effect changed: remove the `if (!selectedSpaceId) return` guard and adjust the URL conditionally. The "no space selected" empty-state message becomes an "all accessible spaces" auto-loaded view.

### Alternatives considered
- **New `/v1/documents/accessible` endpoint**: Unnecessary since `GET /v1/documents` with no `space_id` is the natural semantic for "all visible documents."
- **Server-side render (RSC)**: Would require exposing auth token to server component — more complexity than the existing client-side pattern warrants for this change.

---

## 6. Empty-State Handling

### Decision
- No space selected, no documents: "No documents found across your accessible spaces."
- Space selected, no documents: "No documents in this space."
- User has access to no spaces: same first message (the query returns an empty list, not an error).

### Rationale
FR-007 requires a clear empty-state message. Distinguishing the two contexts helps users understand whether the issue is their access level or the content of a specific space.

### Alternatives considered
- Single generic message: Less informative; ruled out by FR-007 wording.
