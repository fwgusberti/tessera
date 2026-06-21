# Implementation Plan: Space-Filtered Document Listing

**Branch**: `020-space-filtered-docs` | **Date**: 2026-06-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/020-space-filtered-docs/spec.md`

## Summary

When the Documents page opens, the API must automatically return all documents from spaces the authenticated user has access to — determined by matching the user's identity-provider group memberships against `role_permissions` records — without requiring a space to be explicitly selected. The space selector remains available for narrowing the view. The implementation fixes two stubs: `SqlSpaceRepository.list_for_user()` (currently returns all spaces) and the `GET /v1/documents` no-`space_id` branch (currently returns an empty list).

## Technical Context

**Language/Version**: Python 3.12 (API/core), TypeScript / React 19 / Next.js 15 (web)

**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy (async), PostgreSQL, `tessera_core` domain package, pytest + anyio
- Frontend: Next.js, React hooks, Tailwind CSS, existing `api` client (`@/lib/api`)

**Storage**: PostgreSQL — `users.groups` (ARRAY of group names), `role_permissions` (idp_group → role per space), `documents` (space_id FK)

**Testing**: pytest + anyio (API), Vitest / React Testing Library (web); TDD order enforced by constitution

**Target Platform**: Linux server (API), browser (web)

**Performance Goals**: SC-001 — documents visible within 3 s; the cross-space query uses a single SQL JOIN rather than N+1 calls

**Constraints**: Zero unauthorized document exposure (SC-002); no new DB migrations required (all needed data already exists)

**Scale/Scope**: Single PostgreSQL query per page load to fetch accessible spaces; single follow-up query to fetch their documents

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | ✅ PASS | New `list_by_space_ids()` is added to the `DocumentRepository` port (domain boundary). `list_for_user()` business rule belongs in the adapter's SQL — same rule already encoded in `resolve_user_role()`. No framework imports in `tessera_core`. |
| II. Separation of Concerns | ✅ PASS | Port contract change in `packages/core`; SQL implementation in `apps/api`. Frontend change is presentation only. |
| III. Data Locality & Consent | ✅ PASS | No new client-side persistence introduced. |
| IV. Test-Driven Development | ✅ REQUIRED | Tests must be written before implementation for: new port method, fixed `list_for_user`, updated endpoint, updated frontend behaviour. |
| V. Quality Gates | ✅ REQUIRED | All files must pass Ruff + Black before commit. |
| UI Design System | ✅ PASS | Existing slate/indigo palette already in use on the Documents page; no new colour families introduced. |
| Security | ✅ PASS | JWT/session auth enforced via `require_user`. Accessible-space query runs server-side; documents from inaccessible spaces never returned. |
| Audit Logging | ✅ N/A | Read-only list endpoint — no state change, no audit record required. |

**Post-Phase 1 re-check**: No violations found after design. The SQL JOIN approach does not bypass the domain's access model — it implements the same rule (`idp_group ∈ user.groups`) in an efficient single query, consistent with how `resolve_user_role` works.

## Project Structure

### Documentation (this feature)

```text
specs/020-space-filtered-docs/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── documents-api.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
packages/core/tessera_core/
├── domain/entities.py          # No change — entities already correct
├── permissions/access.py       # No change — resolve_user_role already correct
└── ports/repositories.py       # ADD list_by_space_ids() to DocumentRepository

packages/core/tests/
└── test_ports.py               # ADD test for list_by_space_ids() contract

apps/api/tessera_api/
├── adapters/repo.py            # FIX list_for_user(); ADD list_by_space_ids()
└── routers/documents.py        # FIX GET /v1/documents no-space_id branch

apps/api/tests/
├── contract/test_documents.py  # ADD contract test for no-space_id list endpoint
└── integration/                # ADD integration test for accessible-docs flow

apps/web/app/documents/
└── page.tsx                    # FIX: auto-load on mount; restore on clear
```

**Structure Decision**: Existing web-application layout (backend + frontend). No new files at the project root level; changes are confined to `packages/core` (port), `apps/api` (adapter + router), and `apps/web` (page component).

## Complexity Tracking

> No constitution violations requiring justification.
