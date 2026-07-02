# Implementation Plan: Reindex Document on Finishing an Edit

**Branch**: `047-fix-edit-reindex` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/047-fix-edit-reindex/spec.md`

## Summary

`POST /documents/{document_id}/draft/finish` (added in feature 046) creates a
new `DocumentVersion` when a user finishes an editing session, but — unlike
`POST /documents/{document_id}/publish` and `POST
/documents/{document_id}/reindex` — it never dispatches the
`tessera.index_document_version` Celery task. Search therefore keeps serving
stale content for any document that is edited after being published. The fix
adds the same dispatch already used by `publish_document` and
`reindex_document` to `finish_document_draft`, gated so it only fires when
(a) a new version was actually created and (b) the document is currently in
the `PUBLISHED` state — mirroring the existing rule that only published
documents are searchable/reindexable.

## Technical Context

**Language/Version**: Python 3.11 (FastAPI backend) — no new language, matches existing `apps/api` stack.

**Primary Dependencies**: FastAPI (existing router), Celery via the existing `get_celery_app()` adapter and the existing `tessera.index_document_version` task — both reused as-is, no new dependency.

**Storage**: PostgreSQL — reads/writes only the existing `documents`, `document_versions`, and `document_drafts` tables already touched by `finish_document_draft`; no schema change.

**Testing**: pytest (`apps/api/tests/unit/test_documents_draft_router.py`), following the existing `unittest.mock.patch("tessera_api.routers.documents.get_celery_app", ...)` pattern already used in `test_documents_router.py` and `test_reindex_router.py`.

**Target Platform**: Linux server (existing FastAPI + Celery worker containers, unchanged).

**Project Type**: Web service — backend-only change. No frontend change: the edit UI (feature 046) already calls `POST /draft/finish`; this fix only changes a server-side side effect of that existing call, and the endpoint's request/response shape is unchanged.

**Performance Goals**: Reindex dispatch must add no perceptible latency to finishing an edit — `send_task` is fire-and-forget, exactly as it already is for `publish_document` and `reindex_document`.

**Constraints**: Dispatch MUST NOT block or fail the finish-edit request (FR-005, FR-006) — the new version is committed to the database regardless of whether the Celery dispatch call succeeds.

**Scale/Scope**: One router function changed (`finish_document_draft` in `apps/api/tessera_api/routers/documents.py`) plus companion unit tests. No new endpoint, no new table, no migration.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Domain-Driven Architecture**: PASS. No domain logic is added — the
  "is this document published" check is a read of the existing
  `Document.state` field, the same one-line condition already used inline in
  `reindex_document` (`doc.state != DocumentLifecycleState.PUBLISHED`). No
  framework or persistence types leak into `tessera_core`.
- **II. Separation of Concerns**: PASS. No product/domain definition changes;
  purely an orchestration change in the API router.
- **III. Data Locality & Consent**: PASS. No client-side persistence involved.
- **IV. Test-Driven Development**: PASS (enforced in Phase 2/implementation).
  New failing tests will be added to `test_documents_draft_router.py` for:
  dispatch-on-published-with-change, no-dispatch-on-no-change,
  no-dispatch-on-unpublished — written before the router change, following
  this repo's existing red-green pattern for this file.
- **V. Quality Gates**: PASS (enforced in Phase 2/implementation) — Ruff and
  Black run before commit, as for every change in this repo.
- **VI. Tenant Data Isolation**: PASS — see Tenant Isolation section below.

### Tenant Isolation

- **Tables accessed**: `documents`, `document_versions`, `document_drafts` —
  all already accessed, unchanged, by the existing
  `finish_document_draft` / `_resolve_document_for_draft_write` code path.
- **`company_id` scoping**: Unchanged. The document is resolved via
  `SqlDocumentRepository.get_by_id_for_company(document_id, company_id)`
  inside `_resolve_document_for_draft_write` *before* any draft/version logic
  runs (existing behavior, covered by
  `test_finish_cross_tenant_returns_404_and_audits`). This fix adds no new
  data-access call — the added Celery dispatch (`send_task("tessera.
  index_document_version", args=[version_id, document_id, space_id])`) uses
  only IDs already available from that tenant-scoped lookup, identical to the
  existing dispatch in `publish_document`/`reindex_document`.
- **Cross-tenant operations introduced**: None.
- **Isolation tests**: No *new* isolation test is required because no new
  data-access path is introduced — the existing
  `test_finish_cross_tenant_returns_404_and_audits` test already proves the
  404 + `cross_tenant_denied` audit fires before this logic (and therefore
  before any reindex dispatch) would run. This is called out explicitly here
  so it isn't mistaken for an oversight.

## Project Structure

### Documentation (this feature)

```text
specs/047-fix-edit-reindex/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── draft-finish-side-effect.md   # Phase 1 output — side-effect delta only
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/api/
├── tessera_api/
│   └── routers/
│       └── documents.py                       # finish_document_draft: + conditional
│                                                #   get_celery_app().send_task(...) dispatch
└── tests/unit/
    └── test_documents_draft_router.py          # + 3 new tests under TestFinishDraft;
                                                  #   _build_doc gains an optional `state=`
                                                  #   param; _patched_router gains an
                                                  #   optional `celery=` patch
```

**Structure Decision**: No new projects, directories, or files beyond test
additions — this is a localized change inside the existing `apps/api`
documents router, following the exact structure already established by
features 016/017 (search indexing) and 046 (document edit flow). No changes
to `apps/web`, `packages/core`, or `db/migrations`.

## Complexity Tracking

*No violations — table omitted.*
