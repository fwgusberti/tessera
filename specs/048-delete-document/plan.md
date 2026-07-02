# Implementation Plan: Delete Document

**Branch**: `048-delete-document` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/048-delete-document/spec.md`

## Summary

Add a way to permanently delete a document: a `DELETE /v1/documents/{document_id}` endpoint,
gated to the document's owner, a space admin of its space, or a platform admin, plus a **Delete**
button on the document detail page that confirms before calling it. The database already
declares `ON DELETE CASCADE` from `document_versions`, `document_drafts`, `update_proposals`, and
`chunks` (the search index table) to `documents`, so deleting the `documents` row transactionally
removes all dependent data — including making the document unsearchable — with no new Celery
dispatch required. A new `can_delete_document` domain permission function encodes the
owner-or-space-admin rule, mirroring the existing `can_write_document`/`can_manage_members`
pattern from feature 024.

## Technical Context

**Language/Version**: Python 3.11 (FastAPI backend, `apps/api`) + TypeScript/React 19 (Next.js
frontend, `apps/web`) — no new language, matches existing stack.

**Primary Dependencies**: FastAPI (new router handler), SQLAlchemy async (new repository
method + raw `DELETE`), existing `tessera_core.permissions.access` module (new function) — all
reused, no new dependency. Frontend: existing `api` fetch wrapper (`apps/web/lib/api.ts`,
`api.delete` already implemented), `next/navigation` `useRouter` (already used on the edit page).

**Storage**: PostgreSQL. No schema change — the `ON DELETE CASCADE` foreign keys this feature
relies on already exist (see [research.md §2](./research.md#2-cascade-deletion-mechanics)).

**Testing**: pytest (`apps/api/tests/unit/test_documents_router.py`, following the existing
module-level-import + `unittest.mock.patch` pattern) and
`packages/core/tests/test_membership.py` (new `TestCanDeleteDocument` class, pytest, following
the existing `TestCanWriteDocument`/`TestCanManageMembers` style). Frontend: Vitest +
Testing Library, new `apps/web/tests/document-delete.test.tsx`, following the existing
`documents-reindex-admin.test.tsx` structure.

**Target Platform**: Linux server (existing FastAPI container) + browser (existing Next.js app).
No new infrastructure.

**Project Type**: Web application (existing `apps/api` + `apps/web` split). Backend adds one
endpoint; frontend adds one button + handler to an existing page.

**Performance Goals**: Deletion (including cascade) must complete within a single request/
transaction with no perceptible added latency versus the existing `publish`/`reindex` endpoints
— it's a single `DELETE` statement plus one audit insert, no chunking/embedding work (unlike
indexing).

**Constraints**: The delete transaction must remove document + versions + drafts + proposals +
search chunks atomically (FR-004, FR-005, SC-003) — satisfied by relying on existing DB-level
cascades rather than sequencing multiple application-level deletes, which would risk partial
failure.

**Scale/Scope**: One new endpoint, one new repository method + port method, one new domain
permission function, one new frontend button + handler. No new tables, no new Celery task, no
new page.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Domain-Driven Architecture**: PASS. The new `can_delete_document` permission rule lives in
  `tessera_core.permissions.access` (pure domain logic, no framework/persistence imports), same
  module as its siblings. The router only orchestrates: resolve → authorize → delete → audit.
- **II. Separation of Concerns**: PASS. No product/domain definition depends on FastAPI or
  SQLAlchemy; the repository port (`DocumentRepository.delete`) is the only place persistence
  leaks in, matching the existing pattern for every other repository method.
- **III. Data Locality & Consent**: PASS. No client-side persistence introduced.
- **IV. Test-Driven Development**: PASS (enforced in Phase 2/implementation). New failing tests
  will be written first for: `can_delete_document` (owner/space-admin/company-admin/editor/
  viewer cases) in `packages/core`, and the router (200/403/404/double-delete/audit-record cases)
  in `apps/api`, before the implementation, following this repo's existing red-green pattern.
- **V. Quality Gates**: PASS (enforced in Phase 2/implementation) — Ruff and Black run before
  commit, as for every change in this repo.
- **VI. Tenant Data Isolation**: PASS — see Tenant Isolation section below.

### Tenant Isolation

- **Tables accessed**: `documents` (read then delete), `space_memberships` (read, for the
  permission check), `users` (read, to resolve the caller), `audit_records` (insert). No new
  tables.
- **`company_id` scoping**: The document is resolved via the existing
  `SqlDocumentRepository.get_by_id_for_company(document_id, company_id)` — identical to
  `get_document`, `list_versions`, and `_resolve_document_for_draft_write` — *before* the delete
  or the permission check runs. A cross-company `document_id` therefore 404s with a
  `cross_tenant_denied` audit record, exactly like every other document endpoint, and the
  `DELETE FROM documents WHERE id = :document_id` only ever executes after that scoped lookup
  has confirmed the document belongs to the caller's company.
- **Cross-tenant operations introduced**: None.
- **Isolation tests**: A new test (mirroring
  `test_finish_cross_tenant_returns_404_and_audits` in `test_documents_draft_router.py`) will
  assert that a `DELETE` for a document belonging to a different company returns 404 with a
  `cross_tenant_denied` audit record, and — critically — that no row is actually deleted (the
  mocked `doc_repo.delete` must NOT be called in that case).

## Project Structure

### Documentation (this feature)

```text
specs/048-delete-document/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── delete-document-endpoint.md   # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
packages/core/
├── tessera_core/
│   ├── ports/repositories/document.py           # + abstract delete(document_id) method
│   └── permissions/access.py                    # + can_delete_document()
└── tests/
    └── test_membership.py                        # + TestCanDeleteDocument class

apps/api/
├── tessera_api/
│   ├── adapters/repositories/document.py         # SqlDocumentRepository: + delete()
│   └── routers/documents.py                      # + DELETE /documents/{document_id} handler
└── tests/unit/
    └── test_documents_router.py                  # + delete-endpoint test cases

apps/web/
├── app/documents/[id]/page.tsx                    # + Delete button, confirm, handler, redirect
└── tests/
    └── document-delete.test.tsx                   # new file
```

**Structure Decision**: No new projects, directories, or top-level files — this is a localized
addition across the three layers already established by prior document features (024
permissions, 046 edit flow, 047 reindex fix): a domain permission function, a repository method
+ router endpoint, and a frontend button on the existing document detail page. No changes to
`db/migrations` (the cascades this relies on already exist) or `apps/workers`.

## Complexity Tracking

*No violations — table omitted.*
