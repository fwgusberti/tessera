# Contract: Space-Visibility Matrix (per surface, before → after)

This feature changes no request/response shapes. The contract it pins down is the
**visibility source** behind each space-resolving surface and the audit behavior. Tests
in `quickstart.md` assert this matrix.

## Surfaces that resolve a company's space set

| Surface | Auth dependency | Visibility source — before | Visibility source — after |
| ------- | --------------- | -------------------------- | ------------------------- |
| `GET /v1/spaces` | `require_company_context` | `list_by_company(company_id)` | unchanged (now the only shape) |
| `GET /v1/spaces/{id}` | `require_company_context` | `get_by_id_for_company` → 404 + `cross_tenant_denied` on miss | unchanged |
| `POST /v1/spaces` | `require_company_context` | create with `company_id = active` | unchanged |
| `POST /v1/spaces/{id}/permissions` | `require_company_admin` | `get_by_id_for_company` → 404 on miss | unchanged |
| search (`search.py`) | `require_company_context` | `list_by_company(company_id)` | unchanged |
| assistant (`assistant.py`) | `require_company_context` | `list_by_company(company_id)` | unchanged |
| documents (`documents.py`) | `require_company_context` | `list_by_company(company_id)` | unchanged |
| `SpaceRepository.list_for_user(user)` | (domain port) | `is_admin → list_all`; else unscoped group-join | **REMOVED** |

## Platform-operator surface (single documented cross-tenant exception — FR-008)

| Endpoint | Gate | Reads/Writes | Audit — before | Audit — after |
| -------- | ---- | ------------ | -------------- | ------------- |
| `GET /v1/admin/spaces` | global `is_admin` | `list_all()` (all companies) | none | **`cross_company_admin_access`** |
| `PUT /v1/admin/spaces/{id}/retention` | global `is_admin` | update any space | none | **`cross_company_admin_access`** |
| `POST /v1/admin/reindex` | global `is_admin` | dispatch across all companies | none | **`cross_company_admin_access`** |
| `PUT /v1/users/{id}/platform-role` | global `is_admin` | set platform flag | `platform_role_changed` | unchanged |

## Behavioral contract (assertions)

1. **C-001 (FR-001/SC-001)**: For every everyday surface above, a request active as
   Company A returns only Company A's spaces; Company B's spaces never appear.
2. **C-002 (FR-004/US3)**: Carrying the legacy global `is_admin` flag while active as
   Company A yields the **same** result as a non-admin member of A — A's spaces only.
   Active as a company that owns no spaces → empty set.
3. **C-003 (FR-002/SC-004)**: An ordinary member of Company B (no `is_admin`) sees B's
   spaces on every everyday surface.
4. **C-004 (FR-007/SC-005)**: `GET /v1/spaces/{id}` for a Company B space while active as
   A returns `404` with body `{"error":{"code":"not_found","message":"Not found"}}` —
   byte-identical to a non-existent id — and writes exactly one `cross_tenant_denied`
   record.
5. **C-005 (FR-008/FR-009)**: Each `/v1/admin/*` space endpoint, when invoked by a global
   admin, writes one `cross_company_admin_access` record (actor, endpoint, operation).
6. **C-006 (Principle VI)**: `SpaceRepository` exposes no `list_for_user`; the only
   multi-tenant space query without a `company_id` argument is `list_all()`, reachable
   solely from the audited operator surface.

## Error-shape reference (unchanged from 036)

```json
404 Not Found
{ "error": { "code": "not_found", "message": "Not found" } }
```

Used for both genuinely-absent spaces and cross-company by-ID access, so existence is
never disclosed (FR-007).
