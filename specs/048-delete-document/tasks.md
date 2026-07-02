# Tasks: Delete Document

**Input**: Design documents from `specs/048-delete-document/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**TDD**: Constitution Principle IV is non-negotiable — each new test below MUST be written and confirmed FAILING before its corresponding implementation task, except where explicitly noted (US2/US3 tests that prove behavior already delivered by an earlier task, mirroring the pattern in `specs/047-fix-edit-reindex/tasks.md`).

**Organization**: Tasks are grouped by user story (spec.md priorities P1/P2/P3). US1 delivers the full owner-delete stack (permission function, endpoint, button) as the MVP. US2 reuses the same permission function and endpoint — it adds admin coverage to the domain/router tests (already satisfied by US1's implementation) plus one small frontend visibility change. US3 is test-only, proving the confirm-cancel guard US1 already wrote.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Verify Environment)

**Purpose**: Confirm the test environment is functional across all three touched layers before making changes.

- [X] T001 Confirm a passing baseline: `cd packages/core && .venv/bin/python -m pytest tests/ -v --no-cov`, `cd apps/api && .venv/bin/python -m pytest tests/unit -v --no-cov`, and `cd apps/web && npx vitest run`

---

## Phase 2: Foundational (Shared Repository Method — Blocks All User Stories)

**Purpose**: Add the one piece of infrastructure every user story depends on: a way to actually delete a `documents` row and prove the database cascade (`document_versions`, `document_drafts`, `update_proposals`, `chunks`) works as [research.md §2](./research.md#2-cascade-deletion-mechanics) documents. No story can be delivered without this.

**⚠️ CRITICAL**: No user story task can begin until this phase is complete.

- [X] T002 [P] Add abstract `async def delete(self, document_id: UUID) -> None: ...` to `DocumentRepository` in `packages/core/tessera_core/ports/repositories/document.py` (alongside the existing `set_owner` method).
- [X] T003 [P] Write a new integration test file `apps/api/tests/integration/test_document_delete_cascade.py`, following the exact structure of `apps/api/tests/integration/test_document_draft_repository.py` (same `_db_reachable()`/`requires_db` skip-if-no-DB pattern, same `DB_URL` env var). Build a document with one `DocumentVersionModel`, one `DocumentDraftModel`, and one `chunks` row (raw `INSERT INTO chunks (...) VALUES (...)` with a null `embedding`, matching the columns in `db/migrations/versions/0001_initial_schema.py`) via direct model/SQL inserts. Call `SqlDocumentRepository(session).delete(document_id)`, commit, then assert zero rows remain in `documents`, `document_versions`, `document_drafts`, and `chunks` for that `document_id`. Run it and confirm it FAILS (method doesn't exist yet) if a DB is reachable; note in a comment that it's skipped otherwise.
- [X] T004 Implement `delete` in `SqlDocumentRepository` in `apps/api/tessera_api/adapters/repositories/document.py`: `await self._session.execute(delete(DocumentModel).where(DocumentModel.id == document_id))` (import `delete` from `sqlalchemy` alongside the existing `select`/`update` import), no explicit `flush`/`commit` (the router commits, matching every other write method in this file). Run T003 and confirm it now passes (or is skipped if no DB is configured locally). (depends on T002, T003)

**Checkpoint**: The database can now actually delete a document and everything that cascades from it. User story implementation can begin.

---

## Phase 3: User Story 1 - Owner removes an obsolete document (Priority: P1) 🎯 MVP

**Goal**: A document's owner can delete it from the document detail page, after confirming, and it is fully gone (data + search) immediately.

**Independent Test**: Sign in as the document's owner, open `/documents/{id}`, click Delete, confirm, and verify the document 404s afterward and no longer appears in its space's listing.

### Tests for User Story 1 (TDD — MUST FAIL before implementation)

> **⚠️ Write and confirm FAILING before starting T008**

- [X] T005 [P] [US1] Add a `TestCanDeleteDocument` class to `packages/core/tests/test_membership.py`, following the exact style of `TestCanManageMembers` (add a local `_document(space_id, owner_user_id)` helper returning `Document(space_id=space_id, title="Test Doc", owner_user_id=owner_user_id)` from `tessera_core.domain.entities`). Cases: `test_owner_can_delete` (document owner, no membership, `is_company_admin=False` → `True`), `test_non_owner_editor_cannot_delete` (EDITOR membership, not owner → `False`), `test_non_owner_viewer_cannot_delete` (VIEWER membership, not owner → `False`), `test_non_member_non_owner_cannot_delete` (no membership, not owner → `False`). Import `can_delete_document` (does not exist yet) from `tessera_core.permissions.access`. Run and confirm it FAILS with an `ImportError`.
- [X] T006 [P] [US1] Add delete-endpoint tests to `apps/api/tests/unit/test_documents_router.py`, reusing the `_bypass_onboarding`/`_with_db`/`_build_doc`/`_build_version` helpers already in that file plus the `CompanyMemberContext`-style helpers from `test_documents_draft_router.py` (`_with_company_context` overriding `require_company_member`, `_build_membership`, `_build_user`). Add: `test_owner_delete_returns_200_and_calls_repo_delete` (build a doc owned by the calling user, mock `doc_repo.delete = AsyncMock()`, assert it's called with the document id and the response is `{"deleted": True, "document_id": str(doc_id)}`), `test_delete_writes_audit_record` (assert `write_audit` is called with `action="document_deleted"`, `entity_type="document"`, `entity_id=document_id`), `test_non_owner_non_admin_delete_returns_403` (editor membership, not owner → 403, and assert `doc_repo.delete` was NOT called), `test_delete_cross_tenant_returns_404_and_audits` (mock `doc_repo.get_by_id_for_company` returning `None`, assert 404 + `cross_tenant_denied` audit, same pattern as the existing cross-tenant tests in this file). Run and confirm these FAIL (endpoint doesn't exist yet — 404/405 from FastAPI's router).
- [X] T007 [P] [US1] Create `apps/web/tests/document-delete.test.tsx`, following the exact mocking structure of `apps/web/tests/documents-reindex-admin.test.tsx` (mock `@/lib/api` including a `delete: vi.fn()`, mock `@/lib/auth`/`@/lib/auth-guard`, mock `next/navigation` with both `useParams: () => ({ id: "d1" })` and `useRouter: () => ({ push: mockPush })` per the pattern in `documents-edit.test.tsx`). Build a document owned by `u1`. Cases: `it("shows a Delete button for the document owner")` (auth mock `user: { id: "u1", ... }`, assert `screen.getByRole("button", { name: /delete/i })` exists), `it("does not show a Delete button for a non-owner without admin rights")` (auth mock `user: { id: "u2", isAdmin: false }`, mock `/v1/spaces/s1/members/me` to resolve `{ membership: { role: "editor" } }`, assert `screen.queryByRole("button", { name: /delete/i })` is null), `it("does not call the delete API when the confirm dialog is cancelled")` (owner user, stub `window.confirm` to return `false` via `vi.spyOn(window, "confirm").mockReturnValue(false)`, click Delete, assert `mockApi.delete` was not called and the page still shows the document title). Run and confirm these FAIL (no Delete button exists yet).

### Implementation for User Story 1

- [X] T008 [US1] Implement `can_delete_document(user: User, document: Document, memberships: list[SpaceMembership], is_company_admin: bool = False) -> bool` in `packages/core/tessera_core/permissions/access.py`, placed after `can_read_space_document`: `if document.owner_user_id == user.id: return True` then `return effective_space_role(user, document.space_id, memberships, is_company_admin) == SpaceRole.ADMIN`. Run T005 and confirm it now passes. (depends on T005)
- [X] T009 [US1] Add `DELETE /documents/{document_id}` to `apps/api/tessera_api/routers/documents.py`, appended after `reindex_document`. Signature: `async def delete_document(document_id: UUID, ctx: CompanyMemberContext, session: SessionDep) -> dict`. Body: unpack `user_info, company_id, caller_membership = ctx`; resolve `doc = await doc_repo.get_by_id_for_company(document_id, company_id)`, on `None` write the `cross_tenant_denied` audit and raise `_not_found()` exactly like `_resolve_document_for_draft_write`; resolve the caller `User` via `SqlUserRepository` (same `get_by_id`-then-`get_by_subject` fallback used in `_resolve_document_for_draft_write`); load `memberships = await SqlSpaceMembershipRepository(session).list_by_space(doc.space_id)`; call `can_delete_document(actor, doc, memberships, is_company_admin=is_company_admin(caller_membership))`, raising `HTTPException(status_code=403, detail="You must be the document owner or a space admin to delete this document")` if it returns `False` or `actor is None`; on success call `await doc_repo.delete(document_id)`, then `write_audit(session, actor_type="user", actor_id=actor.id, action="document_deleted", entity_type="document", entity_id=document_id, metadata={"space_id": str(doc.space_id), "title": doc.title})`, then `return {"deleted": True, "document_id": str(document_id)}`. Import `can_delete_document` at module level alongside the existing `can_write_document` import. Run T006 and confirm it now passes. (depends on T004, T008, T006)
- [X] T010 [US1] In `apps/web/app/documents/[id]/page.tsx`: add `const [deleting, setDeleting] = useState(false);` and `const [deleteError, setDeleteError] = useState<string | null>(null);` near the other action-state hooks; add a `handleDelete` async function that does `if (!confirm("Delete this document? This cannot be undone.")) return;` then `setDeleting(true); setDeleteError(null);` then `try { await api.delete(`/v1/documents/${id}`); router.push(`/spaces/${document.space_id}`); } catch (err) { setDeleteError(err instanceof Error ? err.message : "Failed to delete document"); setDeleting(false); }`; add `const canDeleteDocument = document !== null && document.owner_user_id === user?.id;` (owner-only for this task — US2 extends it); render a Delete button (styled with the `red-*` destructive-action colors per the constitution's UI Design System, e.g. `bg-white text-red-600 border border-red-200 hover:bg-red-50`) next to the existing Edit button, guarded by `canDeleteDocument`, calling `handleDelete`, disabled while `deleting`, showing `deleteError` in the same `role="alert"` red inline-error style already used for `publishError`/`reindexError`. Run T007's first and third cases and confirm they now pass. (depends on T007)
- [X] T011 [US1] Run `cd packages/core && .venv/bin/python -m pytest tests/test_membership.py -v --no-cov`, `cd apps/api && .venv/bin/python -m pytest tests/unit/test_documents_router.py -v --no-cov`, and `cd apps/web && npx vitest run tests/document-delete.test.tsx`, and confirm all US1 tests pass with no regressions in neighboring tests in the same files. (depends on T008, T009, T010)

**Checkpoint**: MVP complete — a document's owner can delete it end-to-end, with tenant isolation, audit logging, and a working confirm/cancel UI.

---

## Phase 4: User Story 2 - Admin removes another user's document (Priority: P2)

**Goal**: A space admin or platform admin can delete a document they do not own.

**Independent Test**: Sign in as a space admin (or platform admin) who is not the document's owner, delete it, and confirm it's removed for everyone.

### Tests for User Story 2

> Note: `can_delete_document` (T008) and the `DELETE` endpoint (T009) already implement the admin branch via `effective_space_role`/`is_company_admin` — these tests prove that existing behavior from a new angle, per the pattern used for US2/US3 in `specs/047-fix-edit-reindex/tasks.md`. If any of them fail, fix T008/T009, do not add new production code.

- [X] T012 [P] [US2] Extend `TestCanDeleteDocument` in `packages/core/tests/test_membership.py` with `test_space_admin_non_owner_can_delete` (ADMIN membership, `document.owner_user_id` a *different* user, `is_company_admin=False` → `True`) and `test_company_admin_non_owner_can_delete` (no membership, different owner, `is_company_admin=True` → `True`). Run and confirm they pass immediately.
- [X] T013 [P] [US2] Extend `apps/api/tests/unit/test_documents_router.py` with `test_space_admin_non_owner_delete_returns_200` and `test_company_admin_non_owner_delete_returns_200`, each building a document owned by a *different* user than the caller, with the caller holding an ADMIN `SpaceMembership` (first case) or `is_company_admin=True` via the `CompanyMembership` role passed to `_with_company_context` (second case). Run and confirm they pass immediately.
- [X] T014 [P] [US2] Extend `apps/web/tests/document-delete.test.tsx` with `it("shows a Delete button for a space admin who does not own the document")` (mock `/v1/spaces/s1/members/me` to resolve `{ membership: { role: "admin" } }`, auth user id different from `owner_user_id`) and `it("shows a Delete button for a platform admin who does not own the document")` (auth mock `isAdmin: true`, user id different from owner). Run and confirm these FAIL (T010's `canDeleteDocument` is currently owner-only).

### Implementation for User Story 2

- [X] T015 [US2] In `apps/web/app/documents/[id]/page.tsx`, extend `canDeleteDocument` to `document !== null && (document.owner_user_id === user?.id || spaceRole === "admin" || user?.isAdmin === true)` — the same three-way condition already used by `canEditDocument` two lines above, just applied to delete. Run T014 and confirm both cases now pass. (depends on T014)
- [X] T016 [US2] Run `cd packages/core && .venv/bin/python -m pytest tests/test_membership.py -v --no-cov`, `cd apps/api && .venv/bin/python -m pytest tests/unit/test_documents_router.py -v --no-cov`, and `cd apps/web && npx vitest run tests/document-delete.test.tsx` and confirm all US1 + US2 tests pass. (depends on T012, T013, T015)

**Checkpoint**: US1 and US2 both verified — space admins and platform admins can clean up documents they don't own.

---

## Phase 5: User Story 3 - User backs out of an accidental deletion (Priority: P3)

**Goal**: Cancelling the confirmation prompt leaves the document completely untouched.

**Independent Test**: Click Delete, dismiss the confirm prompt, and verify no request was sent and the document is still fully intact.

> Note: T010 already wrote the `if (!confirm(...)) return;` guard and T007's third test case already covers the "cancel" path. This phase exists to make the story's independent value explicit in the task list and to add the one case that test didn't cover — re-opening delete after a cancel still works.

### Tests for User Story 3

- [X] T017 [US3] Extend `apps/web/tests/document-delete.test.tsx` with `it("allows deleting after a previously cancelled confirmation")`: stub `window.confirm` with `vi.fn().mockReturnValueOnce(false).mockReturnValueOnce(true)`, click Delete twice, and assert `mockApi.delete` is called exactly once (after the second click) with `/v1/documents/d1`, and `mockPush` is called with `/spaces/s1`. Run and confirm it passes (no new production code expected — if it fails, fix T010, not this test).

### Implementation for User Story 3

*No new production code — T010's existing `confirm()` guard already satisfies this story. This phase is test-only, confirming FR-003's "cancel leaves the document untouched, and the action remains available afterward" behavior.*

**Checkpoint**: All three user stories independently verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Meet Constitution Principle V (Ruff + Black) and confirm the full suite and the manual quickstart both pass.

- [X] T018 [P] Run Ruff on all modified/added Python files: `cd apps/api && .venv/bin/ruff check tessera_api/routers/documents.py tessera_api/adapters/repositories/document.py tests/unit/test_documents_router.py tests/integration/test_document_delete_cascade.py` and `cd packages/core && .venv/bin/ruff check tessera_core/permissions/access.py tessera_core/ports/repositories/document.py tests/test_membership.py`
- [X] T019 [P] Run Black on the same files: `cd apps/api && .venv/bin/black tessera_api/routers/documents.py tessera_api/adapters/repositories/document.py tests/unit/test_documents_router.py tests/integration/test_document_delete_cascade.py` and `cd packages/core && .venv/bin/black tessera_core/permissions/access.py tessera_core/ports/repositories/document.py tests/test_membership.py`
- [X] T020 Run the full backend suite to confirm no regressions: `cd packages/core && .venv/bin/python -m pytest -v --no-cov` and `cd apps/api && .venv/bin/python -m pytest tests/unit tests/integration -v --no-cov` (integration test skips cleanly if no local Postgres is running)
- [X] T021 Run the full frontend suite: `cd apps/web && npx vitest run` and confirm no regressions in `documents.test.tsx`, `documents-edit.test.tsx`, `documents-reindex-admin.test.tsx`, `document-detail-modernized.test.tsx`
- [X] T022 Walk through `specs/048-delete-document/quickstart.md` Scenarios 1-6 against a local `make dev` stack (owner delete, admin delete, cancel, unauthorized 403, search removal, double-delete 404)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user story tasks (nothing can delete a document without T004).
- **User Story 1 (Phase 3)**: Depends on Foundational. Delivers the full stack (permission function, endpoint, UI) — this is the MVP.
- **User Story 2 (Phase 4)**: Depends on US1's T008/T009/T010 existing — adds admin-coverage tests (pass immediately) plus one frontend visibility line (T015).
- **User Story 3 (Phase 5)**: Depends on US1's T010 existing — test-only.
- **Polish (Phase 6)**: Depends on Phases 3-5 being complete.

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on other stories — the MVP.
- **User Story 2 (P2)**: Builds on US1's `can_delete_document`/endpoint (no new backend code) and extends US1's frontend visibility condition (T015).
- **User Story 3 (P3)**: Builds on US1's confirm-guard (T010) — proves it, adds no new production code.

### Within Each User Story

- Tests are written and confirmed failing before implementation in US1 (true TDD, since T008/T009/T010 are new production code).
- US2's domain/router tests (T012/T013) are written after T008/T009 exist and are expected to pass immediately, proving those tasks already generalize correctly — per the same convention used in `specs/047-fix-edit-reindex/tasks.md` for its US2/US3. US2's frontend test (T014) is expected to FAIL until T015 lands, since frontend visibility genuinely needs a new line of code.
- US3's test (T017) is written after T010 exists and is expected to pass immediately.

### Parallel Opportunities

- T002 and T003 (Foundational) touch different files and can run in parallel.
- T005, T006, T007 (US1 tests) touch three different files (`packages/core`, `apps/api`, `apps/web`) and can be written in parallel.
- T012, T013, T014 (US2 tests) similarly touch three different files and can run in parallel.
- T018 and T019 (Ruff/Black) are non-conflicting tooling passes over the same file set and can run back-to-back or in parallel processes.

---

## Parallel Example: User Story 1 tests

```bash
# Launch all three US1 test-writing tasks together (different files, no shared state):
Task: "Add TestCanDeleteDocument to packages/core/tests/test_membership.py"
Task: "Add delete-endpoint tests to apps/api/tests/unit/test_documents_router.py"
Task: "Create apps/web/tests/document-delete.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (repository `delete()` + cascade proof).
3. Complete Phase 3: User Story 1 (T005-T007 failing tests → T008-T010 implementation → T011 green).
4. **STOP and VALIDATE**: A document's owner can delete it end-to-end, with tenant isolation and audit logging. This alone satisfies the feature's core request ("add delete button").

### Incremental Delivery

1. Setup + Foundational → the database can delete documents and everything cascades correctly.
2. US1 → owner-delete ships as the MVP.
3. US2 → space admins and platform admins get the same capability for documents they don't own (mostly test coverage + one UI line).
4. US3 → the cancel-safety guarantee is explicitly proven.
5. Polish → lint/format/full-suite/quickstart pass.

### Notes

- [P] tasks touch different files and have no shared state.
- Commit after each checkpoint (end of Phase 2, Phase 3, Phase 4, Phase 5, Phase 6), not after every individual task.
- T003's integration test requires a local Postgres instance to actually execute (it skips cleanly otherwise, per the existing `test_document_draft_repository.py` convention) — do not treat a skip as a failure, but do run it against a real database at least once before considering this feature done, since it's the only automated proof of the cascade the whole design relies on.
