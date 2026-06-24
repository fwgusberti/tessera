# API Contract: Close Company & User Scope Gaps

These endpoints already exist. This feature **changes their access behavior**,
not their request/response shapes (except where noted). The invariant for every
row below: a request acting on behalf of a company that does not own the target
returns **403** with the generic body and is indistinguishable from "not found"
(FR-010), and the denial is audited as `cross_tenant_denied` (FR-013).

Generic denial body (reused from 031):

```json
{ "error": { "code": "forbidden", "message": "Access denied" } }
```

No-company-context body (FR-011):

```json
{ "error": { "code": "no_company_context", "message": "No active company context" } }
```

## US1 — Proposals (`proposals.py`)

| Endpoint | Auth before | Auth after | Cross-company result |
|----------|-------------|-----------|----------------------|
| `GET /v1/proposals` | `require_user` | `require_company_context` + `list_for_company` | Company A proposals absent from Company B's list |
| `GET /v1/proposals/{id}` | `require_user`, unscoped `get_by_id` | `require_company_context` + `get_by_id_for_company` | 403, no document content returned |
| `POST /v1/proposals/{id}/approve` | `require_user` only | `require_company_context` + scoped load + `can_approve_proposal` | 403; target doc + version history unchanged |
| `POST /v1/proposals/{id}/reject` | `require_user` only | `require_company_context` + scoped load + `can_approve_proposal` | 403; proposal state unchanged |

Additional in-company rule: approve/reject return **403** when the caller lacks
publish rights in the document's space, even within their own company (FR-004).

## US2 — Connectors (`connectors.py`)

| Endpoint | Auth before | Auth after | Cross-company result |
|----------|-------------|-----------|----------------------|
| `POST /v1/spaces/{space_id}/connectors` | `require_user` + global `is_admin` | `require_company_admin` + `validate_space_for_company` | 403; no connector created |
| `POST /v1/connectors/{id}/sync` | `require_user` + global `is_admin` | `require_company_admin` + `get_by_id_for_company` | 403; **no Celery sync job enqueued** |

## US3 — Agent credentials (`agent_credentials.py`)

| Endpoint | Auth before | Auth after | Cross-company result |
|----------|-------------|-----------|----------------------|
| `POST /v1/agent-credentials` | `require_user` + global `is_admin` | `require_company_admin` + validate every `scoped_space_id` ∈ company; bind `company_id` | 403 if any scoped space is another company's; no token issued |
| `POST /v1/agent-credentials/{id}/revoke` | `require_user` + global `is_admin` | `require_company_admin` + `get_by_id_for_company` | 403; token remains active |

Response of issuance unchanged (`{ "credential": {…}, "token": "<once>" }`); the
stored credential now carries `company_id`.

## US4 — Members & permissions (`members.py`, `spaces.py`)

| Endpoint | Auth before | Auth after | Cross-company result |
|----------|-------------|-----------|----------------------|
| `POST /v1/spaces/{space_id}/members` | `require_user` | `require_company_context` + `validate_space_for_company` | 403 |
| `PUT /v1/spaces/{space_id}/members/{user_id}` | `require_user` | `require_company_context` + `validate_space_for_company` | 403 |
| `DELETE /v1/spaces/{space_id}/members/{user_id}` | `require_user` | `require_company_context` + `validate_space_for_company` | 403 |
| `GET /v1/spaces/{space_id}/members/me` | `require_user` | `require_company_context` + `validate_space_for_company` | 403/404, reveals no Company A data |
| `POST /v1/spaces/{space_id}/permissions` | `require_user` + global `is_admin` | `require_company_admin` + `validate_space_for_company` | 403 |

In-company role rule (unchanged): `MembershipService` still returns 403 when the
caller's space role does not permit the action (FR-007 acceptance #3).

## US5 — Metrics (`metrics.py`)

| Endpoint | Auth before | Auth after | Behavior change |
|----------|-------------|-----------|-----------------|
| `GET /v1/metrics` | `require_user` + global `is_admin`; counts across all companies | `require_company_admin`; counts scoped to active company | `total_queries` and `documents_with_drift` reflect the active company only |

Response shape unchanged; values now exclude other companies (FR-008). Requires
the assistant "query" audit to carry `metadata.company_id` (see data-model).

## US6 — Per-company admin (cross-cutting)

New dependency `require_company_admin` authorizes by `CompanyRole.ADMIN` in the
active company. A user who is ADMIN of Company A but only MEMBER (or non-member)
of Company B receives **403** on every admin-gated Company B endpoint above
(SC-004). The global `is_admin` flag authorizes **only**
`PUT /v1/users/{id}/platform-role` after this feature (FR-014).

## Audit contract (all denials)

Every 403 from the rows above writes:

```text
action     = "cross_tenant_denied"
actor_id   = <caller user id>
entity_type= "proposal" | "connector" | "agent_credential" | "space" | "role_permission"
entity_id  = <targeted resource id>
metadata   = { "company_id": "<active company id>" }
```
