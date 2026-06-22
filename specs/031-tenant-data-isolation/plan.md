# Implementation Plan: Tenant Data Isolation

**Branch**: `031-tenant-data-isolation` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/031-tenant-data-isolation/spec.md`

## Summary

Companies are currently accessing each other's Spaces because the `spaces` table has no `company_id` column and all list/fetch endpoints call unscoped repository methods (`list_all()`, bare `get_by_id()`). This plan adds `company_id` to the Space schema, introduces a company-context activation endpoint that embeds `company_id` into the JWT/session, and scopes every data-access path (Spaces, Documents, Search, Assistant) to the authenticated tenant.

## Technical Context

**Language/Version**: Python 3.12 (API venv), Python 3.11 (core package)

**Primary Dependencies**: FastAPI, SQLAlchemy async, joserfc (JWT), PostgreSQL 15

**Storage**: PostgreSQL — one new column on `spaces`, one new index

**Testing**: pytest + anyio (API package), pytest-asyncio (core package)

**Target Platform**: Linux container (Docker / Kubernetes)

**Project Type**: Web service — multi-package monorepo (`packages/core`, `apps/api`)

**Performance Goals**: No p95 regression; added JOIN on document lookup is a single-table join

**Constraints**: Zero cross-tenant data disclosure; backward-compatible migration with nullable-first backfill

**Scale/Scope**: All tenant-owned tables: `spaces`, `documents`, `chunks` (via space), `role_permissions`, `space_memberships`, `connectors`

## Constitution Check

### I. Domain-Driven Architecture ✅
`company_id` is added to the `Space` domain entity first; the SQLAlchemy model and repository follow. No framework imports in domain layer.

### II. Separation of Concerns ✅
Company context propagation lives in the auth layer (`require_company_context` dependency). Repository methods enforce tenant scoping. Neither layer leaks into the other.

### III. Data Locality & Consent ✅
No new local persistence. Session cookie is server-signed.

### IV. Test-Driven Development ✅ (REQUIRED)
Every new method must have a failing test written before implementation. Cross-tenant isolation tests in `test_tenant_isolation.py` must be written test-first.

### V. Quality Gates ✅
Ruff + Black must pass before commit.

### VI. Tenant Data Isolation — CURRENT STATE: VIOLATED; TARGET: COMPLIANT

**Tables accessed and their current/target state:**

| Table | Has `company_id` | Current State | Target State |
|-------|-----------------|---------------|--------------|
| `spaces` | ❌ | Unscoped | Add `company_id` FK; scope all queries |
| `documents` | ❌ (indirect via space) | Unscoped bare `get_by_id` | Scope via space join |
| `chunks` | Via `space_id` | Search accepts caller-supplied space_ids | Caller restricted to company spaces |
| `company_memberships` | ✅ | Already scoped | No change |
| `invitations` | ✅ | Already scoped | No change |
| `join_requests` | ✅ | Already scoped | No change |
| `domain_join_policies` | ✅ | Already scoped | No change |

**Cross-tenant isolation tests to be written:**
- `test_company_a_cannot_list_company_b_spaces`
- `test_company_a_cannot_get_company_b_space_by_id` *(when GET /spaces/{id} exists)*
- `test_company_a_cannot_get_company_b_document_by_id`
- `test_company_a_cannot_create_document_in_company_b_space`
- `test_company_a_search_returns_only_company_a_results`
- `test_company_a_assistant_returns_only_company_a_citations`
- `test_activate_company_forbidden_for_non_member`
- `test_context_switch_scopes_correctly`

### Security Requirements ✅
JWT remains HS256 signed. New `company_id` claim is server-issued and cannot be forged. Session cookie is HttpOnly and signed by `settings.secret_key`. Cross-tenant access returns uniform 403 to prevent entity enumeration.

### UI Design System ✅
No frontend changes in this feature (company switching UI was built in 030).

## Project Structure

### Documentation (this feature)

```text
specs/031-tenant-data-isolation/
├── plan.md              ← this file
├── research.md          ← audit findings + architectural decisions
├── data-model.md        ← schema changes, entity changes, new dependency
├── contracts/
│   └── api-isolation.md ← endpoint-by-endpoint contract changes
├── quickstart.md        ← validation scenarios
└── tasks.md             ← /speckit-tasks output (not yet created)
```

### Source Code (affected paths)

```text
packages/core/tessera_core/
├── domain/entities.py           # Space: add company_id field
└── ports/repositories.py        # SpaceRepository, DocumentRepository: new scoped methods

apps/api/tessera_api/
├── auth/
│   ├── jwt_auth.py              # create_access_token: add company_id param
│   └── oidc.py                  # require_company_context dependency
├── adapters/
│   ├── models.py                # SpaceModel: add company_id mapped column
│   └── repo.py                  # SqlSpaceRepository, SqlDocumentRepository: scoped impls
└── routers/
    ├── companies.py             # POST /companies/{id}/activate
    ├── spaces.py                # scope to company_id from session
    ├── documents.py             # scope all endpoints to company_id
    ├── search.py                # restrict space_ids to company's spaces
    └── assistant.py             # restrict space_ids to company's spaces

db/migrations/versions/
└── 0007_space_company_id.py    # ALTER TABLE spaces ADD COLUMN company_id

apps/api/tests/
└── test_tenant_isolation.py     # new cross-tenant isolation test suite
```

## Complexity Tracking

No constitution violations requiring justification. The nullable-first migration pattern (add column nullable → backfill → add NOT NULL constraint) is standard practice for zero-downtime migrations and is not a deviation.

## Implementation Phases

### Phase A: Schema + Domain Entity

1. Write failing tests for `Space(company_id=...)` construction
2. Add `company_id: UUID` to `Space` entity
3. Write migration `0007_space_company_id.py`:
   - Add column as nullable
   - Update backfill if any rows exist
   - Add NOT NULL constraint + index
4. Add `company_id` mapped column to `SpaceModel`
5. Update `_space_from_model` mapper
6. Update `SqlSpaceRepository.create()` to persist `company_id`

### Phase B: Repository Scoped Methods

1. Write failing tests for new repository methods
2. Add `list_by_company(company_id)` to `SqlSpaceRepository`
3. Add `get_by_id_for_company(space_id, company_id)` to `SqlSpaceRepository`
4. Add `get_by_id_for_company(doc_id, company_id)` to `SqlDocumentRepository`
5. Add `list_by_space_ids_for_company(space_ids, company_id)` to `SqlDocumentRepository`
6. Update `SpaceRepository` and `DocumentRepository` port protocols

### Phase C: JWT + Company Context Auth

1. Write failing tests for `create_access_token` with `company_id`
2. Update `create_access_token` to accept optional `company_id` parameter
3. Write `require_company_context` dependency
4. Add `POST /companies/{company_id}/activate` endpoint:
   - Validates user membership
   - Issues new JWT with `company_id` claim
   - Updates session `active_company_id`
5. Update login/register flow to set `active_company_id` in session when user has exactly one company

### Phase D: Route Handler Updates

For each router, swap `require_user` for `require_company_context` and use scoped repository methods:

1. `spaces.py` — `list_spaces`, `create_space`
2. `documents.py` — `list_documents`, `get_document`, `create_document`, `publish_document`, `reindex_document`
3. `search.py` — restrict `allowed_space_ids` to company's spaces
4. `assistant.py` — same restriction as search

### Phase E: Cross-Tenant Isolation Tests

Write all tests listed in Constitution Check §VI before implementing (TDD). Each test:
- Creates two companies with separate users
- Creates resources under Company A
- Asserts Company B user receives 403 or empty result

All tests must pass green before the PR is opened.

## Follow-up: MCP Server Tenant Isolation

`apps/mcp-server` is in scope for tenant isolation but is **not addressed in this PR**. It will be handled in a dedicated follow-up sub-task. The MCP server's tool handlers that access spaces, documents, and search must be updated to pass `company_id` from the request context, mirroring the changes made to the FastAPI routers in this feature.
