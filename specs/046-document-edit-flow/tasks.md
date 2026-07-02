---

description: "Task list for Document Edit Flow"

---

# Tasks: Document Edit Flow

**Input**: Design documents from `/specs/046-document-edit-flow/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/draft-endpoints.md, quickstart.md

**Tests**: Included and REQUIRED — `plan.md`'s Constitution Check commits this feature to Test-Driven Development (Constitution Principle IV, NON-NEGOTIABLE): pytest tests for the three new endpoints and Vitest tests for the edit view are written first and must fail before the corresponding implementation exists.

**Organization**: Tasks are grouped by user story (from `spec.md`) to enable independent implementation and testing of each story. Unlike feature 045, this feature touches both `apps/api` (3 new endpoints, 1 new table) and `apps/web` (1 new route).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task includes an exact file path

## Path Conventions

Backend: `apps/api/` (FastAPI/SQLAlchemy) and `packages/core/` (domain/ports). Frontend: `apps/web/` (Next.js App Router). Database: `db/migrations/versions/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the new `DocumentDraft` shape at the domain and frontend-type level before anything is built on top of it. No new package dependencies are needed (research.md — zero new runtime deps).

- [X] T001 [P] Create the `DocumentDraft` domain entity in `packages/core/tessera_core/domain/document_draft.py` as a Pydantic `BaseModel` (mirroring `packages/core/tessera_core/domain/document_version.py`'s style): `document_id: UUID`, `content_markdown: str`, `editor_user_id: UUID`, `started_at: datetime`, `last_autosaved_at: datetime`. Register it in `packages/core/tessera_core/domain/entities.py`'s import list and `__all__`, alongside `DocumentVersion` (data-model.md)
- [X] T002 [P] Create the repository port `DocumentDraftRepository` (ABC) in `packages/core/tessera_core/ports/repositories/document_draft.py`, mirroring `packages/core/tessera_core/ports/repositories/document_version.py`'s style, with abstract async methods `get_by_document_id_for_company(document_id: UUID, company_id: UUID) -> DocumentDraft | None`, `upsert_for_company(document_id: UUID, company_id: UUID, editor_user_id: UUID, content_markdown: str) -> DocumentDraft`, `delete_for_company(document_id: UUID, company_id: UUID) -> None` (depends on T001; Constitution VI — no method may accept a bare `document_id` without `company_id`)
- [X] T003 [P] Add the `DocumentDraft` TypeScript interface to `apps/web/lib/types.ts` (`content_markdown: string`, `editor_user_id: string`, `started_at: string`, `last_autosaved_at: string`), mirroring the existing `DocumentVersion` interface

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The persistence layer for drafts — SQLAlchemy model, migration, and repository implementation — plus shared test-file scaffolding, all needed by both User Story 2 and User Story 3

**⚠️ CRITICAL**: No User Story 2 or 3 implementation can begin until this phase is complete. User Story 1 does not depend on this phase (it does not touch persistence).

- [X] T004 [P] Create the SQLAlchemy model `DocumentDraftModel` in `apps/api/tessera_api/adapters/models/document_draft.py`: `document_id` (UUID, primary key, `ForeignKey("documents.id", ondelete="CASCADE")`), `content_markdown` (Text, not null), `editor_user_id` (UUID, `ForeignKey("users.id")`), `started_at` (DateTime with timezone, not null), `last_autosaved_at` (DateTime with timezone, not null) — mirroring the column style of `apps/api/tessera_api/adapters/models/document_version.py` (data-model.md)
- [X] T005 Create Alembic migration `db/migrations/versions/0014_document_drafts.py` (next sequential number after `0013_backfill_space_memberships.py`) creating the `document_drafts` table matching T004's columns exactly, `document_id` as primary key, `ON DELETE CASCADE` on the foreign key to `documents(id)` (data-model.md "Migration"; depends on T004)
- [X] T006 Implement `SqlDocumentDraftRepository(DocumentDraftRepository)` in `apps/api/tessera_api/adapters/repositories/document_draft.py`: all three methods join `DocumentDraftModel` → `DocumentModel` → `SpaceModel` and filter `SpaceModel.company_id == company_id` before returning/mutating a row, mirroring `SqlDocumentRepository.get_by_id_for_company`'s join pattern in `apps/api/tessera_api/adapters/repositories/document.py` exactly (Constitution VI Tenant Isolation section of plan.md) (depends on T001, T002, T004)
- [X] T007 [P] Register `SqlDocumentDraftRepository` in `apps/api/tessera_api/adapters/repo.py`'s imports and `__all__`, alongside the existing `SqlDocumentRepository`/`SqlDocumentVersionRepository` entries (depends on T006)
- [X] T008 [P] Create `apps/api/tests/unit/test_documents_draft_router.py` skeleton: `TestClient` setup, reuse (or extract to a shared fixture if not already importable) the `_bypass_onboarding`/`_with_company_context`/`_with_db` context managers from `apps/api/tests/unit/test_documents_router.py`, mock `SqlDocumentRepository`, `SqlSpaceMembershipRepository`, `SqlDocumentDraftRepository`, `SqlDocumentVersionRepository` — no test cases yet
- [X] T009 [P] Create `apps/web/tests/documents-edit.test.tsx` skeleton: mock `@/lib/api` (`get`/`put`/`post`), `@/lib/auth` (`useAuth`), `next/navigation` (`useParams`/`useRouter`), following `apps/web/tests/documents-reindex-admin.test.tsx`'s pattern; shared fixtures for a document + current version, an EDITOR-role `{ membership: { role: "editor" } }` response for `/v1/spaces/{id}/members/me`, and a VIEWER-role equivalent — no test cases yet

**Checkpoint**: Foundation ready — User Story 2 and 3 work can begin (User Story 1 could already have started in parallel)

---

## Phase 3: User Story 1 - Edit document content with a live preview (Priority: P1) 🎯 MVP

**Goal**: A split-pane edit view — raw Markdown source on the left, live rendered preview on the right — reachable only by space members with write access.

**Independent Test**: As a space EDITOR/ADMIN, open a document, enter edit mode, confirm the split view renders, type a Markdown change, and confirm the preview updates within ~1s with no manual refresh. As a user without write access, confirm no Edit entry point is shown and the edit route itself declines to render the editor.

### Tests for User Story 1 ⚠️

> Write these tests FIRST, run them, and confirm they FAIL before implementing anything below

- [X] T010 [P] [US1] In `apps/web/tests/documents-edit.test.tsx`, add a test asserting `/documents/{id}/edit` renders a `<textarea>` seeded with the current version's `content_markdown` on the left and a rendered preview (heading/list/code elements, not raw markdown text) on the right, for the EDITOR-role fixture user (FR-003, Acceptance Scenario 1)
- [X] T011 [P] [US1] In the same file, add a test asserting that firing a change event on the textarea with new Markdown content updates the preview pane's rendered output synchronously (no debounce, no network call asserted) (FR-004, SC-001)
- [X] T012 [P] [US1] In the same file, add a test asserting the preview supports the same GFM elements as the read-only view (table, fenced code block, list) and that no raw HTML from the textarea is ever rendered unescaped (FR-005, FR-006)
- [X] T013 [P] [US1] In the same file, add a test asserting `/documents/{id}` does NOT render an "Edit" link for the VIEWER-role fixture user, and a separate test asserting that rendering `/documents/{id}/edit` directly as that same VIEWER-role user redirects back to `/documents/{id}` without showing the textarea/preview (FR-001, FR-002, Acceptance Scenario 3)

### Implementation for User Story 1

- [X] T014 [P] [US1] Create `apps/web/app/documents/[id]/edit/page.tsx`: client component (`"use client"`); on mount, `GET /v1/documents/{id}` (existing endpoint) for the document + current version; render a two-column layout — left `<textarea>` bound to local `content` React state (seeded from `current_version.content_markdown`), right `<DocumentContent version={{ content_markdown: content } as DocumentVersion} />` reusing the feature-045 component from `apps/web/components/documents/DocumentContent.tsx` unmodified, re-rendering on every `content` change (T010-T012)
- [X] T015 [US1] On `apps/web/app/documents/[id]/page.tsx`, on mount fetch `GET /v1/spaces/{document.space_id}/members/me` (same endpoint/shape already used in `apps/web/components/NavBar.tsx` and `apps/web/app/spaces/[id]/members/page.tsx` — `{ membership: { role: "admin" | "editor" | "viewer" } }`); show an "Edit" link to `/documents/{id}/edit` if the resolved role is `"editor"` or `"admin"`, OR if `user?.isAdmin === true` (company admin — a 404 from `members/me` means "not a direct member," which company admins without a direct membership row would get, mirroring the existing `canReindex` fallback at `page.tsx:107-110`) (FR-001)
- [X] T016 [US1] In `apps/web/app/documents/[id]/edit/page.tsx`, perform the same role check as T015 on mount; if the user is neither EDITOR/ADMIN in the space nor a company admin, redirect to `/documents/{id}` instead of rendering the textarea/preview (FR-002; note: this is a UX guard only — real enforcement is completed server-side once T024/T025's 403 checks land in User Story 2)

**Checkpoint**: User Story 1 is fully functional and independently testable — split view, live preview, and entry-point/route gating all work. (Nothing is persisted yet; that begins in User Story 2.)

---

## Phase 4: User Story 2 - Edits are protected against accidental loss (Priority: P2)

**Goal**: Periodic autosave of in-progress content to the new `document_drafts` table, with resume-on-reopen and a visible failure warning that never discards in-pane content.

**Independent Test**: Type a change, wait past the autosave debounce, reload the tab without finishing the session, and confirm the autosaved content (not the original) is restored. Separately, simulate an autosave failure and confirm a warning appears while the typed content remains editable.

### Tests for User Story 2 ⚠️

> Write these tests FIRST, run them, and confirm they FAIL before implementing anything below

- [X] T017 [P] [US2] In `apps/api/tests/unit/test_documents_draft_router.py`, add a test asserting `PUT /v1/documents/{id}/draft` as an EDITOR-role caller creates/updates the draft row and returns `{"draft": {...}}` (200) (FR-007)
- [X] T018 [P] [US2] In the same file, add a test asserting `PUT /v1/documents/{id}/draft` as a caller with no write access (VIEWER role, non-member) returns 403 (FR-002, SC-004)
- [X] T019 [P] [US2] In the same file, add a test asserting `PUT /v1/documents/{id}/draft` and `GET /v1/documents/{id}/draft` against a document belonging to another company return the generic 404 body and write a `cross_tenant_denied` audit record, matching the existing pattern for `GET /documents/{id}` (Constitution VI Tenant Isolation section)
- [X] T020 [P] [US2] In the same file, add a test asserting `GET /v1/documents/{id}/draft` returns `{"draft": null}` when no draft row exists, and the persisted draft's shape after a prior `PUT`
- [X] T021 [P] [US2] In `apps/web/tests/documents-edit.test.tsx`, add a test (fake timers) asserting that after the user types, a debounced `PUT /v1/documents/{id}/draft` call fires with the latest `content_markdown` after the autosave interval elapses, and not before (FR-007)
- [X] T022 [P] [US2] In the same file, add a test asserting that when `GET /v1/documents/{id}/draft` resolves with a non-null draft on mount, the textarea is seeded from the draft's `content_markdown` instead of the current version's (Acceptance Scenario 2)
- [X] T023 [P] [US2] In the same file, add a test asserting that when the autosave `PUT` call rejects, a visible warning message renders and the textarea's content is left unchanged (not cleared or reverted) (FR-008, Acceptance Scenario 3)

### Implementation for User Story 2

- [X] T024 [US2] Implement `GET /v1/documents/{document_id}/draft` in `apps/api/tessera_api/routers/documents.py`: resolve the document via `SqlDocumentRepository.get_by_id_for_company` (404 + `cross_tenant_denied` audit on miss, matching the existing `get_document`/`list_versions` handlers), check `can_write_document` via `SqlSpaceMembershipRepository.list_by_space` (403 on failure, matching `create_document`'s check), call `SqlDocumentDraftRepository.get_by_document_id_for_company`, return `{"draft": draft.model_dump() if draft else None}` (contracts/draft-endpoints.md)
- [X] T025 [US2] Implement `PUT /v1/documents/{document_id}/draft` in the same router file, sharing T024's resolve/permission logic; request body `{content_markdown: str}` (new Pydantic `BaseModel`); call `SqlDocumentDraftRepository.upsert_for_company(document_id, company_id, editor_user_id=caller_id, content_markdown=body.content_markdown)`; return `{"draft": ...}`; no audit record is written (research.md §7) (depends on T024)
- [X] T026 [US2] In `apps/web/app/documents/[id]/edit/page.tsx`, add a parallel `GET /v1/documents/{id}/draft` fetch alongside the existing document fetch (T014); if a non-null draft is returned, seed `content` state from `draft.content_markdown` instead of `current_version.content_markdown`
- [X] T027 [US2] In the same file, add a debounced autosave effect: ~4s after the last keystroke, hard-capped to flush at least every ~15s while the user types continuously (research.md §3), calling `PUT /v1/documents/{id}/draft`; render a "Saving…" / "Saved" / "Save failed" indicator; on failure, leave the textarea's `content` state untouched and show the warning (FR-007, FR-008)

**Checkpoint**: User Stories 1 AND 2 both work independently — editing, live preview, autosave with resume, and failure warnings, without yet writing to version history.

---

## Phase 5: User Story 3 - Finishing an edit session creates a new version (Priority: P3)

**Goal**: Finalizing an edit session (explicit exit, tab close, or inactivity timeout) creates exactly one new `DocumentVersion` from the draft's final content, or none if nothing changed.

**Independent Test**: Edit a document, leave the edit view via the explicit exit action, and confirm a new version appears in version history with the edited content. Separately, open and leave the edit view with no changes and confirm no new version is created.

### Tests for User Story 3 ⚠️

> Write these tests FIRST, run them, and confirm they FAIL before implementing anything below

- [X] T028 [P] [US3] In `apps/api/tests/unit/test_documents_draft_router.py`, add a test asserting `POST /v1/documents/{id}/draft/finish` with an existing draft whose content differs from the current version creates a new `DocumentVersion` (next `version_number` via `next_version_number`), repoints `Document.current_version_id` to it, deletes the draft row, and writes exactly one `document_edited` audit record (FR-009, FR-013)
- [X] T029 [P] [US3] In the same file, add a test asserting `POST .../draft/finish` with no draft row present returns `{"version": null}` and creates no new version (FR-011)
- [X] T030 [P] [US3] In the same file, add a test asserting `POST .../draft/finish` with a draft whose `content_markdown` is identical to the current version's returns `{"version": null}`, deletes the draft row, and creates no new version (FR-011)
- [X] T031 [P] [US3] In the same file, add a test asserting `POST .../draft/finish` as a caller without write access returns 403, and against another company's document returns the generic 404 + `cross_tenant_denied` audit (Constitution VI; mirrors T018/T019)
- [X] T032 [P] [US3] In `apps/web/tests/documents-edit.test.tsx`, add a test asserting that clicking an explicit "Done editing" control calls `POST /v1/documents/{id}/draft/finish` and then navigates to `/documents/{id}` (Acceptance Scenario 1)
- [X] T033 [P] [US3] In the same file, add a test asserting that a `pagehide` event while there is autosaved-but-unfinalized content triggers a `fetch(..., {keepalive: true})` call to the finish endpoint (Edge Cases — abrupt browser/tab close)
- [X] T034 [P] [US3] In the same file, add a test (fake timers) asserting that once the configured inactivity threshold elapses with no keystrokes, the finish endpoint is called automatically without further user action, and the timer resets on each keystroke before that threshold (FR-010, Edge Cases — returns before timeout)

### Implementation for User Story 3

- [X] T035 [US3] Implement `POST /v1/documents/{document_id}/draft/finish` in `apps/api/tessera_api/routers/documents.py`, sharing T024's resolve/permission logic: read the draft via `SqlDocumentDraftRepository.get_by_document_id_for_company`; if absent, or its `content_markdown` equals the current version's, delete any draft row and return `{"version": null}`; otherwise create a new `DocumentVersion` via `SqlDocumentVersionRepository.create` (`version_number` = `next_version_number(document_id)`, `content_markdown` = draft content, `author_user_id` = the draft's `editor_user_id`, `frontmatter` copied unchanged from the current version), call `SqlDocumentRepository.set_current_version`, delete the draft row via `SqlDocumentDraftRepository.delete_for_company`, `write_audit(actor_type="user", actor_id=<editor_user_id>, action="document_edited", entity_type="document", entity_id=document_id, metadata={"version_id": str(new_version.id), "editor_user_id": str(editor_user_id)})`, commit, return `{"document": ..., "version": ...}` (contracts/draft-endpoints.md; depends on T024, T025)
- [X] T036 [US3] In `apps/web/app/documents/[id]/edit/page.tsx`, add an explicit "Done editing" button that calls `POST /v1/documents/{id}/draft/finish` then `router.push('/documents/{id}')`
- [X] T037 [US3] In the same file, add a `pagehide` event listener that, when unsaved/autosaved-but-unfinalized changes exist, fires `fetch(`${API_URL}/v1/documents/{id}/draft/finish`, { method: "POST", keepalive: true, headers: {...auth} })` (research.md §2)
- [X] T038 [US3] In the same file, add a client-side inactivity timer (reset on every keystroke) that, after the configured idle threshold (research.md/spec.md Assumptions — on the order of tens of minutes), calls the finish endpoint and redirects to `/documents/{id}` with a "session ended due to inactivity" notice (FR-010)

**Checkpoint**: All three user stories independently functional — this is the full feature.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T039 [P] Run `quickstart.md` scenarios 1-4 manually against local `apps/api` + `apps/web` dev servers (migration apply, split view + preview, autosave + resume + failure warning, finalize + no-op finalize)
- [X] T040 [P] Run `cd apps/api && pytest tests/unit/test_documents_draft_router.py --cov --cov-fail-under=85` and confirm zero regressions in `tests/unit/test_documents_router.py`
- [X] T041 [P] Run `cd apps/web && npx vitest run tests/documents-edit.test.tsx` then the full suite (`npx vitest run`) and confirm zero regressions (`documents.test.tsx`, `documents-reindex-admin.test.tsx`, etc.)
- [X] T042 Run `ruff check .` and `black --check .` in `apps/api` on all new/modified Python files (Constitution V)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: T004-T007 depend on Setup's T001/T002 (domain entity + port must exist first); T008/T009 (test skeletons) have no dependency on Setup and can start immediately — BLOCKS User Story 2 and User Story 3
- **User Story 1 (Phase 3)**: Depends only on existing endpoints (`GET /documents/{id}`, `GET /spaces/{id}/members/me`) — can start immediately, in parallel with Foundational
- **User Story 2 (Phase 4)**: Depends on Foundational (T004-T009) and on User Story 1's edit page existing (T014) to attach autosave to
- **User Story 3 (Phase 5)**: Depends on User Story 2 (T024/T025's shared resolve/permission logic, and the edit page's autosave lifecycle to attach finalize triggers to) — this dependency is explicit in spec.md's own "Why this priority" for US3
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories — delivers the core split view + live preview + access gating
- **User Story 2 (P2)**: Builds on US1's edit page (T014); no functional dependency on US3
- **User Story 3 (P3)**: Builds on US2's draft persistence and shared endpoint logic (T024/T025) — spec.md states this dependency explicitly

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Backend resolve/permission logic (T024) is implemented once and shared by T025 and T035
- Story complete and checkpointed before moving to the next priority

### Parallel Opportunities

- T001, T002, T003 (Setup) can all run in parallel — different files
- T004 and T008/T009 can start in parallel; T005-T007 are sequential after T004
- T010-T013 (US1 tests) can run in parallel — same file, independent `it()` blocks
- T014 (US1: edit page) can be built in parallel with the US1 tests — different file
- T017-T023 (US2 tests) can run in parallel across the two test files
- T028-T034 (US3 tests) can run in parallel across the two test files
- User Story 1 (Phase 3) can proceed in parallel with Phase 2 (Foundational), since it touches no new persistence

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together (same file, independent it() blocks):
Task: "Add split-view render test to documents-edit.test.tsx"
Task: "Add live-preview-update test to documents-edit.test.tsx"
Task: "Add GFM-rendering/no-raw-HTML test to documents-edit.test.tsx"
Task: "Add entry-point/route-gating tests to documents-edit.test.tsx"

# The edit page itself can be built alongside the tests:
Task: "Create apps/web/app/documents/[id]/edit/page.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 3: User Story 1 (T010-T016) — Foundational (Phase 2) is not required for US1
3. **STOP and VALIDATE**: Run `quickstart.md` Scenario 2 (split view + live preview + access gating)
4. Demo if ready — this alone already delivers the core "edit with live preview" experience, without persistence

### Incremental Delivery

1. Setup (+ Foundational, in parallel) → foundation ready
2. User Story 1 → validate via `quickstart.md` Scenario 2 → demo (MVP)
3. User Story 2 → validate via `quickstart.md` Scenario 3 → demo (autosave protection)
4. User Story 3 → validate via `quickstart.md` Scenario 4 → demo (version history integration)
5. Polish (T039-T042) → full regression pass

### Parallel Team Strategy

1. One developer starts Foundational (T004-T009) while a second starts User Story 1 (T010-T016) — no shared files
2. Once both land, the first developer proceeds to User Story 2 (autosave), then User Story 3 (finalize) — these build sequentially on the same new endpoints and the same `edit/page.tsx` file, so are best kept with one owner to avoid merge conflicts

---

## Notes

- [P] tasks touch different files (or independent, non-conflicting additions to the same test file) with no unmet dependency
- Verify each test fails before writing its implementation (Constitution Principle IV)
- Commit after each task or logical group
- Stop at any checkpoint (end of Phase 3, 4, or 5) to validate a story independently before continuing
- T024's resolve/permission logic is intentionally implemented once and reused by T025 and T035, matching the existing router's style of small, self-contained handlers rather than introducing a service layer
