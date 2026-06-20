# Implementation Plan: Fix Document Content Display

**Branch**: `011-fix-doc-content-display` | **Date**: 2026-06-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/011-fix-doc-content-display/spec.md`

## Summary

When a document is created, the API creates a `DocumentVersion` record but never links it to the document via `current_version_id`. The `GET /v1/documents/{id}` endpoint uses that pointer to retrieve the content; when it is `None`, the frontend displays "No content available for this document." The fix is a single `set_current_version` call inside the `create_document` endpoint, within the same database session, immediately after the version is persisted.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI 0.115, SQLAlchemy 2.0 (async), psycopg 3.1 (PostgreSQL)

**Storage**: PostgreSQL — `documents` table has `current_version_id` FK column already; no schema change required

**Testing**: pytest with `unittest.mock` for unit/contract tests; integration tests use a real database via fixtures

**Target Platform**: Linux server (Docker/Kubernetes per constitution)

**Project Type**: Web service (REST API)

**Performance Goals**: No change to existing targets — the fix adds one `UPDATE` statement to the creation flow, negligible overhead

**Constraints**: Must remain within the existing `async with get_db() as session:` block so the entire creation is atomic. Ruff + Black must pass (Constitution V).

**Scale/Scope**: Single-endpoint fix, no cross-service impact

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | ✅ PASS | Fix lives in the router (infrastructure layer), calling an existing repository method. No domain model changes. |
| II. Separation of Concerns | ✅ PASS | The spec change is purely in the API adapter layer. Domain entities and persistence models are untouched. |
| III. Data Locality & Consent | ✅ PASS | No client-side persistence introduced. |
| IV. Test-Driven Development | ✅ REQUIRED | A failing test for `current_version_id` being set on creation MUST be written before the fix. 85% coverage gate applies. |
| V. Quality Gates | ✅ REQUIRED | Ruff and Black must pass before commit. |
| Stack: PostgreSQL | ✅ PASS | No new storage introduced. Existing `current_version_id` column is used. |
| Stack: IaC | ✅ PASS | No infrastructure change. |
| Security: JWT Auth | ✅ PASS | Existing `require_user` guard is unchanged. |
| Security: Audit Logging | ✅ PASS | Document creation does not currently emit a separate audit event (beyond the DB record itself); this fix does not alter that behaviour. The publish flow emits audit events and remains unchanged. |

## Project Structure

### Documentation (this feature)

```text
specs/011-fix-doc-content-display/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
apps/api/
├── tessera_api/
│   └── routers/
│       └── documents.py          ← single-line fix: set_current_version call
└── tests/
    └── contract/
        └── test_documents.py     ← new contract test (write-first)
```

## Complexity Tracking

No constitution violations. No additional complexity entries required.
