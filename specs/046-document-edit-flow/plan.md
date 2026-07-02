# Implementation Plan: Document Edit Flow

**Branch**: `046-document-edit-flow` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/046-document-edit-flow/spec.md`

## Summary

Add a dedicated document editing view (`/documents/{id}/edit`) with a
split-pane layout — the raw editable Markdown source on the left, a live
rendered preview on the right (reusing feature 045's `DocumentContent`
component and its `react-markdown`/`remark-gfm` rendering pipeline
unchanged). Any space member with an effective EDITOR or ADMIN role can open
it. While editing, content is periodically autosaved to a new
ephemeral-per-document `document_drafts` table (not the version history);
when the session ends — the user explicitly leaves, the tab closes, or a
client-side inactivity timer elapses — the draft is finalized into exactly
one new `DocumentVersion`, `Document.current_version_id` is repointed to it,
and the draft row is cleared. A future rich-text (WYSIWYG) editing mode is
explicitly out of scope and not designed here.

## Technical Context

**Language/Version**: TypeScript 5, React 19, Next.js 15.5 (App Router) for
the new edit view; Python 3.12 / FastAPI ≥0.115 for the three new endpoints
— both existing stacks, no new language/runtime.

**Primary Dependencies**: No new runtime dependencies. Frontend reuses
`react-markdown`/`remark-gfm` (already added in feature 045) and a plain
HTML `<textarea>` for the editable pane (see research.md §4). Backend reuses
SQLAlchemy ≥2.0 (async) and Alembic ≥1.13, already in `apps/api/pyproject.toml`.

**Storage**: PostgreSQL — one new table, `document_drafts` (see
data-model.md), added via Alembic migration `0014_document_drafts.py`. No
change to `documents` or `document_versions` schemas.

**Testing**: Backend — pytest + pytest-anyio, `TestClient` from
`fastapi.testclient`, mirroring `apps/api/tests/unit/test_documents_router.py`'s
dependency-override/mocking pattern; new file
`apps/api/tests/unit/test_documents_draft_router.py`. Frontend — Vitest +
`@testing-library/react`, mirroring `apps/web/tests/documents-reindex-admin.test.tsx`;
new file `apps/web/tests/documents-edit.test.tsx`.

**Target Platform**: Web browser (existing Next.js app, `apps/web`) + existing
FastAPI service (`apps/api`).

**Project Type**: Web application — both frontend and backend touched (new
route + 3 new endpoints + 1 new table), unlike feature 045 which was
frontend-only.

**Performance Goals**: Preview re-render is synchronous client-side React
state (no network round-trip), targeting the <1s feel required by SC-001
with no debounce needed on rendering itself. Autosave network calls are
debounced (~4s after last keystroke, hard-capped flush at ~15s of continuous
typing) to avoid hammering the API — see research.md §3.

**Constraints**: MUST NOT let in-progress/autosaved content become visible
to other viewers before the session finalizes (`current_version_id` is only
repointed at finalization — data-model.md "Lifecycle"). MUST NOT render
raw HTML from user Markdown in the preview (no `rehype-raw`, matching
feature 045's constraint — FR-006). MUST create at most one new
`DocumentVersion` per completed edit session, never one per autosave tick
(FR-012).

**Scale/Scope**: One new frontend route
(`apps/web/app/documents/[id]/edit/page.tsx`), reuse of the existing
`DocumentContent` component unmodified, one new frontend API-client
addition for the draft endpoints, three new backend endpoints in the
existing `documents.py` router, one new repository
(`SqlDocumentDraftRepository`) + domain entity (`DocumentDraft`) +
port, one new Alembic migration, zero new runtime dependencies.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Domain-Driven Architecture**: New `DocumentDraft` concept gets its
  own domain entity (`packages/core/tessera_core/domain/`) and repository
  port (`tessera_core/ports/repositories/document_draft.py`), implemented
  by a SQL adapter (`SqlDocumentDraftRepository`) — mirroring the existing
  `Document`/`DocumentVersion` port+adapter split exactly. No domain logic
  depends on FastAPI, SQLAlchemy, or Next.js types. ✅ PASS
- **II. Separation of Concerns**: `spec.md` describes the edit flow with no
  framework/library references; this plan carries every technical decision
  (draft table shape, endpoint contracts, debounce timings, textarea vs.
  rich editor). ✅ PASS
- **III. Data Locality & Consent**: No new client-side persistence —
  in-progress content lives server-side in `document_drafts` (autosaved via
  API calls), not in browser storage. ✅ PASS (N/A)
- **IV. Test-Driven Development**: New pytest tests for the three draft
  endpoints (happy path, cross-tenant 404, non-write-access 403, no-op
  finalize with no draft, no-op finalize with unchanged content) MUST be
  written before the endpoint implementations, mirroring
  `test_documents_router.py`. New Vitest tests for the edit view (split
  view renders, preview updates on keystroke, autosave call fires debounced,
  finalize call fires on explicit exit/unmount, Edit entry point hidden for
  non-write-access users) MUST be written before the component, mirroring
  `documents-reindex-admin.test.tsx`. Both MUST be written and failing
  before implementation, per Tasks. ✅ PASS (enforced in Tasks)
- **V. Quality Gates**: New Python files pass Ruff/Black; new TypeScript
  files follow existing `apps/web` ESLint conventions. ✅ PASS (enforced in
  Tasks, standard pre-commit gate)
- **VI. Tenant Data Isolation (NON-NEGOTIABLE)** — **Tenant Isolation section**:
  - Tables accessed: `documents` (existing, read via
    `get_by_id_for_company`), `document_versions` (existing, written at
    finalization), `document_drafts` (**new**), `space_memberships`
    (existing, read for the `can_write_document` check).
  - `company_id` scoping: `document_drafts` has no `company_id` column by
    design (see data-model.md) — every `SqlDocumentDraftRepository` method
    MUST accept `company_id` and resolve/validate the row only via a join
    through `documents.space_id → spaces.company_id`, exactly like
    `SqlDocumentRepository.get_by_id_for_company`. No method may accept a
    bare `document_id` without `company_id`, per the constitution's
    explicit rule — this MUST be enforced in code review for the new
    repository.
  - All three new endpoints call `get_by_id_for_company(document_id,
    company_id)` first and return the same generic 404 +
    `cross_tenant_denied` audit record as existing document endpoints on a
    miss, before any draft logic runs.
  - Cross-tenant access: none introduced; no new cross-tenant operation is
    added.
  - Isolation tests to add: `test_documents_draft_router.py` MUST include a
    test authenticated as Company A's user attempting `GET`/`PUT
    /documents/{company_b_document_id}/draft` and `POST
    .../draft/finish`, asserting a 404 (indistinguishable from
    not-found) and a `cross_tenant_denied` audit record, matching the
    existing pattern for `GET /documents/{id}` and
    `GET /documents/{id}/versions`.

No violations requiring justification — Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/046-document-edit-flow/
├── plan.md                        # This file (/speckit-plan command output)
├── research.md                    # Phase 0 output
├── data-model.md                  # Phase 1 output
├── quickstart.md                  # Phase 1 output
├── contracts/
│   └── draft-endpoints.md         # Phase 1 output — the 3 new endpoints
└── tasks.md                       # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/api/
├── tessera_api/
│   ├── routers/
│   │   └── documents.py                       # + 3 new endpoints (GET/PUT draft, POST draft/finish)
│   └── adapters/
│       ├── models/
│       │   └── document_draft.py              # NEW — SQLAlchemy model for document_drafts
│       └── repositories/
│           └── document_draft.py              # NEW — SqlDocumentDraftRepository
└── tests/unit/
    └── test_documents_draft_router.py         # NEW

packages/core/
└── tessera_core/
    ├── domain/
    │   └── document_draft.py                  # NEW — DocumentDraft domain entity
    └── ports/repositories/
        └── document_draft.py                  # NEW — DocumentDraftRepository port

db/migrations/versions/
└── 0014_document_drafts.py                    # NEW — creates document_drafts table

apps/web/
├── app/documents/[id]/
│   └── edit/
│       └── page.tsx                           # NEW — split-pane edit view
├── components/documents/
│   └── DocumentContent.tsx                    # REUSED unmodified (feature 045) — right-pane preview
├── lib/
│   └── api.ts                                 # + draft endpoint helpers (getDraft/saveDraft/finishDraft)
└── tests/
    └── documents-edit.test.tsx                # NEW
```

**Structure Decision**: Standard extension of the existing `apps/api` +
`apps/web` + `packages/core` + `db/migrations` layout already used by every
prior documents-related feature (024, 037, 044, 045) — no new top-level
directories or projects.

## Complexity Tracking

*No violations — table omitted.*
