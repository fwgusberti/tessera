# Contract: Per-Endpoint Authorization Matrix

This feature changes **authorization sources and denial shapes**, not request or
response schemas. Each row records what authorizes the action *before* (global
`is_admin` override available) and *after* (per-company admin only), and the
denial status for a cross-company by-ID attempt.

Legend:
- **CA** = caller is `CompanyRole.ADMIN` in the active company.
- **Cross-company by-ID denial** = caller targets a resource owned by another
  company by its identifier → response. "404 + audit" = HTTP 404, generic
  not-found body, exactly one `cross_tenant_denied` audit record (FR-004, FR-008,
  SC-003, SC-004).
- In-company non-admin attempting an admin action → **403** (unchanged; not a
  cross-tenant case).

## Admin-gated write/manage endpoints

| Endpoint | Authorizes (before) | Authorizes (after) | Cross-company by-ID denial |
|----------|--------------------|--------------------|----------------------------|
| `POST /v1/spaces/{id}/members` (invite) | space ADMIN **or** global `is_admin` | space ADMIN **or** CA (in own company) | 404 + audit |
| `PATCH /v1/spaces/{id}/members/{uid}` (change role) | space ADMIN **or** global `is_admin` | space ADMIN **or** CA | 404 + audit |
| `DELETE /v1/spaces/{id}/members/{uid}` (remove) | space ADMIN **or** global `is_admin` | space ADMIN **or** CA | 404 + audit |
| `POST /v1/spaces/{id}/permissions` (create permission) | global `is_admin` / CA (035) | CA only | 404 + audit |
| `POST /v1/connectors` / `POST /v1/connectors/{id}/sync` | CA (035) — confirm no `is_admin` path | CA only | 404 + audit |
| `POST /v1/agent-credentials` (issue) | CA (035) | CA only | 404 + audit |
| `DELETE /v1/agent-credentials/{id}` (revoke) | CA (035) | CA only | 404 + audit |
| `POST /v1/proposals/{id}/approve` / `/reject` | `can_approve_proposal` w/ global `is_admin` override | `can_approve_proposal` w/ `is_company_admin` | 404 + audit |
| `POST /v1/documents/{id}/reindex` | owner **or** global `is_admin` | owner **or** CA (in own company) | 404 + audit |
| `POST /v1/documents` (create in space) | `can_write_document` w/ global `is_admin` | `can_write_document` w/ `is_company_admin` | 404 + audit (space) |

## Read endpoints (no existence disclosure)

| Endpoint | Authorizes (before) | Authorizes (after) | Cross-company behavior |
|----------|--------------------|--------------------|------------------------|
| `GET /v1/spaces/{id}/members` (list) | member **or** global `is_admin` | member **or** CA (own company) | 404 on by-ID space not in company; list never includes other tenants |
| `GET /v1/documents/{id}` (read) | `can_read_document` w/ global `is_admin` | `can_read_document` w/ `is_company_admin` | 404 + audit |
| `GET /v1/documents` (list) | scoped (031) | scoped (031), no global override | only own company's rows; **no** denial audit |
| `GET /v1/metrics` | CA (035), aggregated per company | CA only, per company | own company's aggregates only; **no** denial audit |

## Platform-operator endpoints — UNCHANGED (documented exception, FR-010)

| Endpoint | Authorizes | Note |
|----------|-----------|------|
| `PUT /v1/users/{id}/platform-role` | global `is_admin` | bootstraps the global flag; audited |
| `GET /v1/admin/spaces` | global `is_admin` | cross-company by design; unreachable by company admins |
| `PUT /v1/admin/spaces/{id}/retention` | global `is_admin` | cross-company by design |
| `POST /v1/admin/reindex` | global `is_admin` | cross-company by design |

These are the single documented cross-tenant exception. After this feature, a
company admin does not hold the global flag, so none of these is reachable via
ordinary company admin status.

## Invariants the contract guarantees

- **SC-001/SC-002**: every admin-gated action targeting another company's data is
  denied; a single-company admin can read/modify zero resources of another company.
- **SC-003**: cross-company by-ID denial == genuine not-found (identical 404 +
  body).
- **SC-004**: exactly one `cross_tenant_denied` record per cross-company by-ID
  attempt; zero for filtered listings.
- **SC-005**: in-company admin happy paths unchanged (no regression).
- **SC-006**: per-company authority applied correctly on every company switch.
- **SC-007**: every company owner holds an explicit company-admin membership; no
  member is elevated.
