# Tasks: Delete Space

**Input**: Design documents from `specs/052-delete-space/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**TDD**: Constitution Principle IV is non-negotiable — each new test below MUST be written and confirmed FAILING before its corresponding implementation task, except where explicitly noted (US2/US3 tests that prove behavior already delivered by an earlier task, mirroring the pattern used in `specs/048-delete-document/tasks.md`).

**Organization**: Tasks are grouped by user story (spec.md priorities P1/P2/P3). US1 delivers the full delete stack (repository cascade, `SpaceHierarchyService.delete`, the endpoint with password re-verification and ADMIN-or-company-admin authorization, and the two-step confirm→password frontend modal) as the MVP — this necessarily includes a basic wrong-password and non-admin rejection case, since a delete endpoint can't be shipped safely without them. US2 extends the same test files with the retry-after-wrong-password and both-cancel-paths cases, proving the safety net already built in US1 from additional angles. US3 adds one new end-to-end isolation test proving non-admin/cross-company rejection through the real request pipeline, mirroring the pattern used for US2 in `specs/051-add-space/tasks.md`.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Verify Environment)

**Purpose**: Confirm the test environment is functional across all three touched layers before making changes.

- [X] T001 Confirm a passing baseline: `cd packages/core && .venv/bin/python -m pytest tests/ -v --no-cov`, `cd apps/api && .venv/bin/python -m pytest tests/unit tests/test_space_hierarchy_isolation.py -v --no-cov`, and `cd apps/web && npx vitest run`

---

## Phase 2: Foundational (Subtree Cascade — Blocks All User Stories)

**Purpose**: Add the one piece of infrastructure every user story depends on: a way to resolve a space's full descendant subtree and delete it in one bulk operation, proving against a real database that this correctly removes descendant spaces (rather than orphaning them via `parent_space_id`'s `ON DELETE SET NULL`, per [research.md §1](./research.md#1-cascading-deletion-given-parent_space_id-on-delete-set-null)) and that everything else (documents, versions, drafts, chunks, memberships, permissions, connectors) cascades automatically.

**⚠️ CRITICAL**: No user story task can begin until this phase is complete.

- [X] T002 [P] Add abstract `async def delete_subtree(self, space_id: UUID) -> tuple[int, int]: ...` to `SpaceRepository` in `packages/core/tessera_core/ports/repositories/space.py`, placed directly after `list_accessible_by_user`, with a docstring `"""Delete space_id and every descendant space; cascades documents/memberships/etc via FK. Returns (deleted_space_count, deleted_document_count)."""`.
- [X] T003 [P] Write a new integration test file `apps/api/tests/integration/test_space_delete_cascade.py`, following the exact structure of `apps/api/tests/integration/test_document_draft_repository.py` (same `_db_reachable()`/`requires_db` skip-if-no-DB pattern, same `DB_URL` env var). Build: a company; a parent `SpaceModel`; a child `SpaceModel` with `parent_space_id=parent.id`; one `DocumentModel` in the parent and one in the child, each with one `DocumentVersionModel`; one raw `INSERT INTO chunks (...)` row for one of the documents (null `embedding`, matching the columns in `db/migrations/versions/0001_initial_schema.py`); one `SpaceMembershipModel` and one `RolePermissionModel` on the parent; one `ConnectorModel` on the child. Call `SqlSpaceRepository(session).delete_subtree(parent.id)`, assert it returns `(2, 2)`. Commit, then assert zero rows remain in `spaces` for *both* the parent and child ids (proving the child is actually removed, not merely orphaned), `documents` for both documents, `document_versions`, `chunks`, `space_memberships`, `role_permissions`, and `connectors` for the relevant ids. Run it and confirm it FAILS (method doesn't exist yet) if a DB is reachable; skips cleanly otherwise.
- [X] T004 Implement `delete_subtree` in `SqlSpaceRepository` in `apps/api/tessera_api/adapters/repositories/space.py`, placed directly after `list_accessible_by_user`: a `WITH RECURSIVE subtree AS (SELECT id FROM spaces WHERE id = :space_id UNION ALL SELECT s.id FROM spaces s JOIN subtree t ON s.parent_space_id = t.id) SELECT id FROM subtree` raw-SQL query (mirroring `get_ancestor_chain`'s `text()` CTE style) to collect `subtree_ids`; `SELECT COUNT(*) FROM documents WHERE space_id = ANY(CAST(:ids AS uuid[]))` (mirroring the `ANY(CAST(... AS uuid[]))` pattern already used in `chunk.py`) for `deleted_document_count`; `await self._session.execute(delete(SpaceModel).where(SpaceModel.id.in_(subtree_ids)))`; return `(len(subtree_ids), deleted_document_count)`. Import `delete` from `sqlalchemy` alongside the existing `select`/`update`/`text` import. Run T003 and confirm it now passes (or is skipped if no DB is configured locally). (depends on T002, T003)

**Checkpoint**: The database can now resolve and remove a full space subtree in one operation, proven against a real cascade. User story implementation can begin.

---

## Phase 3: User Story 1 - Admin permanently removes a space and everything in it (Priority: P1) 🎯 MVP

**Goal**: A user holding ADMIN on a space (or a company admin) can delete it — plus every descendant space and all their documents — from the spaces page, after confirming the cascading scope and re-entering their password.

**Independent Test**: Sign in as the space's admin, open the spaces page, click **Delete** on a space with children and documents, confirm, enter the correct password, and verify the space, its descendants, and all their documents are gone everywhere (listings, search, direct navigation).

### Tests for User Story 1 (TDD — MUST FAIL before implementation)

> **⚠️ Write and confirm FAILING before starting T008**

- [X] T005 [P] [US1] Add a `TestDeleteValidations` class to `packages/core/tests/test_space_hierarchy.py`, directly after `TestRenameValidations`, following its exact mocking style (`AsyncMock()` for `space_repo`/`membership_repo`, the file's existing `_space`/`_membership` helpers). Cases: `test_admin_deletes_successfully_and_returns_counts` (space resolves via `get_by_id_for_company`, `membership_repo.get` returns an `ADMIN` membership, `space_repo.delete_subtree` mocked to return `(3, 5)` → assert `svc.delete(actor_id=..., space_id=..., company_id=...)` returns `(3, 5)` and `space_repo.delete_subtree` was awaited with the space id), `test_company_admin_bypasses_membership_check` (`is_company_admin=True`, `membership_repo.get` mocked to return `None` → still succeeds, and `membership_repo.get` is NOT called), `test_missing_space_raises_not_found_value_error` (`get_by_id_for_company` returns `None` → `ValueError` matching `"not_found"`, `space_repo.delete_subtree` NOT called), `test_non_admin_raises_permission_error` (`membership_repo.get` returns a `VIEWER` membership, `is_company_admin=False` → `PermissionError`, `space_repo.delete_subtree` NOT called), `test_no_membership_and_not_company_admin_raises_permission_error` (`membership_repo.get` returns `None`, `is_company_admin=False` → `PermissionError`, `space_repo.delete_subtree` NOT called). Call `svc.delete(actor_id=..., space_id=..., company_id=..., is_company_admin=...)` (does not exist yet). Run and confirm all FAIL with an `AttributeError`.
- [X] T006 [P] [US1] Add a `TestDeleteSpace` class to `apps/api/tests/unit/test_spaces_router.py`, patching `SqlSpaceRepository`/`SqlSpaceMembershipRepository`/`SqlUserRepository`/`SpaceHierarchyService`/`verify_password`/`write_audit` exactly like `TestRenameSpace`. Cases: `test_admin_with_correct_password_deletes_returns_200_with_counts` (`mock_svc.delete` resolves `(2, 4)`, `verify_password` patched to return `True` → `200`, response body `{"deleted": True, "space_id": ..., "deleted_space_count": 2, "deleted_document_count": 4}`), `test_wrong_password_returns_401_and_service_not_called` (`verify_password` patched to return `False` → `401`, `mock_svc.delete` NOT called), `test_non_admin_returns_403` (`verify_password` returns `True`, `mock_svc.delete` raises `PermissionError(...)` → `403`), `test_missing_or_cross_tenant_space_returns_404_and_audits_cross_tenant_denied` (`verify_password` returns `True`, `mock_svc.delete` raises `ValueError("not_found")` → `404`, and `mock_audit` was awaited with `action="cross_tenant_denied"`), `test_success_writes_space_deleted_audit_with_counts` (assert `mock_audit.call_args_list[-1].kwargs["action"] == "space_deleted"` and `mock_audit.call_args_list[-1].kwargs["metadata"]` contains `deleted_space_count`/`deleted_document_count`). Run and confirm all FAIL (endpoint doesn't exist yet — 404/405 from FastAPI's router).
- [X] T007 [P] [US1] Create `apps/web/tests/space-delete.test.tsx`, following the exact mocking structure of `apps/web/tests/space-add.test.tsx` (`vi.mock("@/lib/api", ...)` with `get`, `post`, and `delete` all mocked). Cases: `it("shows a Delete action only on admin-accessible tiles")` (render `SpacesPage` with one admin-role and one viewer-role space in the mocked list, assert a "Delete" control exists only for the admin one), `it("shows a confirmation step first, then a password step, without calling the API")` (click Delete on the admin tile, assert confirmation text mentioning the space name and cascading removal appears; click confirm; assert a password input now appears and `mockApi.delete` was NOT called yet), `it("does nothing when cancelled at the confirmation step")` (open Delete, click Cancel before confirming → `mockApi.delete` NOT called, tile still present), `it("shows an error and keeps the tile when the password is wrong")` (progress to the password step, `mockApi.delete.mockRejectedValueOnce(new Error("Current password is incorrect"))`, submit → `screen.getByRole("alert")` shows the error, tile still present), `it("removes the tile immediately on successful deletion")` (progress to the password step, `mockApi.delete.mockResolvedValueOnce({ deleted: true, space_id: "s1", deleted_space_count: 1, deleted_document_count: 0 })`, submit → tile disappears without any new `api.get` call). Run and confirm all FAIL (no Delete action exists yet).

### Implementation for User Story 1

- [X] T008 [US1] Implement `delete(self, actor_id: UUID, space_id: UUID, company_id: UUID, is_company_admin: bool = False) -> tuple[int, int]` in `SpaceHierarchyService` (`packages/core/tessera_core/services/space_hierarchy.py`), placed after `create`. Body: resolve `space = await self._spaces.get_by_id_for_company(space_id, company_id)`, `None` → `ValueError("not_found")`; unless `is_company_admin`, resolve `membership = await self._memberships.get(space_id, actor_id)` and raise `PermissionError("Actor must be admin of space")` if it's `None` or not `SpaceRole.ADMIN`; otherwise `return await self._spaces.delete_subtree(space_id)`. Run T005 and confirm it now passes. (depends on T002, T005)
- [X] T009 [US1] In `apps/api/tessera_api/routers/spaces.py`: add `class DeleteSpaceRequest(BaseModel): password: str`, near `RenameSpaceRequest`; add imports `CompanyMemberContext`, `is_company_admin` from `tessera_api.auth.oidc`, `SqlUserRepository` from `tessera_api.adapters.repo`, and `verify_password` from `tessera_api.auth.jwt_auth`. Add `@router.delete("/spaces/{space_id}")\nasync def delete_space(space_id: UUID, body: DeleteSpaceRequest, ctx: CompanyMemberContext, session: SessionDep) -> dict`, placed after `create_permission`. Body: unpack `user_info, company_id, caller_membership = ctx`; `actor_id = UUID(user_info["sub"])`; fetch `user = await SqlUserRepository(session).get_by_id(actor_id)`; if `user is None or not user.password_hash or not verify_password(body.password, user.password_hash)` raise `HTTPException(status_code=401, detail={"error": {"code": "invalid_credentials", "message": "Current password is incorrect"}})` (nothing else touched yet); then `try: deleted_space_count, deleted_document_count = await SpaceHierarchyService(SqlSpaceRepository(session), SqlSpaceMembershipRepository(session)).delete(actor_id=actor_id, space_id=space_id, company_id=company_id, is_company_admin=is_company_admin(caller_membership))`; on `PermissionError` raise `_forbidden()`; on `ValueError` (only `"not_found"` is possible here) write the `cross_tenant_denied` audit (matching `rename_space`'s not-found branch exactly: `actor_type="user", actor_id=actor_id, action="cross_tenant_denied", entity_type="space", entity_id=space_id, metadata={"company_id": str(company_id)}`, then `await session.commit()`) and raise `_not_found()`; on success, write one audit record (`action="space_deleted", entity_type="space", entity_id=space_id, metadata={"company_id": str(company_id), "deleted_space_count": deleted_space_count, "deleted_document_count": deleted_document_count}`) and `return {"deleted": True, "space_id": str(space_id), "deleted_space_count": deleted_space_count, "deleted_document_count": deleted_document_count}`. Run T006 and confirm it now passes. (depends on T004, T008, T006)
- [X] T010 [P] [US1] In `apps/web/lib/api.ts`, change `delete: <T>(path: string) => request<T>(path, { method: "DELETE" })` to `delete: <T>(path: string, body?: unknown) => request<T>(path, { method: "DELETE", ...(body !== undefined ? { body: JSON.stringify(body) } : {}) })`.
- [X] T011 [P] [US1] Create `apps/web/components/spaces/DeleteSpaceModal.tsx`, structurally mirroring `RenameSpaceModal.tsx` but with two internal steps via `const [step, setStep] = useState<"confirm" | "password">("confirm")`. Props: `{ space: Space; allAccesses: SpaceAccess[]; onClose: () => void; onDeleted: (deletedSpaceId: string) => void }`. In the `"confirm"` step: show `Delete "{space.name}"?` and body text `This will permanently delete "{space.name}"${childCount > 0 ? ` and its ${childCount} sub-space(s)` : ""}, along with all documents inside them. This cannot be undone.` where `childCount` is computed client-side by counting entries in `allAccesses` whose `space.id !== space.id` and are descendants of `space.id` (reuse the descendant-walk logic already in `apps/web/lib/spaces.ts`, exported as described in T013); **Cancel** closes the modal with no request; **Continue** moves to `"password"`. In the `"password"` step: a `type="password"` input bound to local `password` state, an inline `role="alert"` error area, **Cancel** closes the modal with no request, and a **Delete** button (styled with the constitution's destructive-action `red-*` colors, e.g. `bg-red-600 hover:bg-red-700`) that calls `await api.delete<{ deleted: boolean; space_id: string }>(`/v1/spaces/${space.id}`, { password })`, then `onDeleted(space.id); onClose();`, catching failures into the local `error` state (same `err instanceof Error ? err.message : "Failed to delete space."` pattern as `RenameSpaceModal`) while remaining on the `"password"` step so the user can retry without re-confirming.
- [X] T012 [US1] In `apps/web/components/spaces/FolderTile.tsx`: add an `onDelete?: () => void` prop; render a `"Delete"` text-link (styled `text-xs text-red-500 hover:text-red-700 underline`, distinct from the existing slate-colored Rename/Set parent links) next to them, gated by `isAdmin && onDelete`. In `apps/web/components/spaces/FolderGrid.tsx`: add an `onDelete?: (space: Space) => void` prop and forward it to each `FolderTile` as `onDelete={onDelete ? () => onDelete(access.space) : undefined}`.
- [X] T013 [US1] In `apps/web/lib/spaces.ts`: export the existing private `isDescendant` function (remove the leading nothing needed — just drop the missing `export` keyword it currently lacks) so it can compute descendant counts/filters from other modules. In both `apps/web/app/spaces/page.tsx` and `apps/web/app/spaces/[id]/page.tsx`: add `const [deletingSpace, setDeletingSpace] = useState<Space | null>(null);`; add a `handleSpaceDeleted(deletedId: string)` function that does `setAccesses((prev) => prev.filter((a) => a.space.id !== deletedId && !isDescendant(prev, deletedId, a.space.id)))`; pass `onDelete={(space) => setDeletingSpace(space)}` to the page's `<FolderGrid>`; render `{deletingSpace && <DeleteSpaceModal space={deletingSpace} allAccesses={accesses} onClose={() => setDeletingSpace(null)} onDeleted={(deletedId) => { handleSpaceDeleted(deletedId); setDeletingSpace(null); }} />}`, importing `DeleteSpaceModal`. (depends on T010, T011, T012)
- [X] T014 [US1] Run T005-T007 and confirm all now pass. Then run `cd packages/core && .venv/bin/python -m pytest tests/test_space_hierarchy.py -v --no-cov`, `cd apps/api && .venv/bin/python -m pytest tests/unit/test_spaces_router.py -v --no-cov`, and `cd apps/web && npx vitest run tests/space-delete.test.tsx tests/spaces.test.tsx tests/space-folder-view.test.tsx`, confirming no regressions. (depends on T008, T009, T013)

**Checkpoint**: MVP complete — an admin (or company admin) can delete a space and its full subtree end-to-end, with tenant isolation, password re-verification, audit logging, and a working two-step confirm/password UI.

---

## Phase 4: User Story 2 - Incorrect password blocks the deletion (Priority: P2)

**Goal**: A wrong password, or cancelling at either step, always leaves the space and its contents completely untouched, and the user can retry.

**Independent Test**: Trigger delete, confirm, enter a wrong password, verify nothing was deleted and an error is shown; retry with the correct password and verify it now succeeds; separately, cancel at each step and verify no request was ever sent.

> Note: T009's password check and T011's two-step modal already implement this safety net — these tests prove it from angles not exercised in Phase 3, per the pattern used for US3 in `specs/048-delete-document/tasks.md`. If any of them fail, fix T009/T011, do not add new production code.

### Tests for User Story 2

- [X] T015 [P] [US2] Extend `apps/web/tests/space-delete.test.tsx` with: `it("stays on the password step after a wrong-password error and allows retry")` (`mockApi.delete.mockRejectedValueOnce(new Error("Current password is incorrect"))` then `mockApi.delete.mockResolvedValueOnce({ deleted: true, space_id: "s1", deleted_space_count: 1, deleted_document_count: 0 })`; submit a wrong password, assert the error and the password input are both still visible; submit again, assert the tile is now removed and `mockApi.delete` was called exactly twice), `it("sends no request when cancelling at the confirmation step")` (open Delete, click Cancel before confirming, assert `mockApi.delete` was never called), `it("sends no request when cancelling at the password step")` (open Delete, confirm, then click Cancel on the password step, assert `mockApi.delete` was never called and the tile is still present). Run and confirm all pass immediately (no new production code expected — if any fails, fix T011).

### Implementation for User Story 2

*No new production code — T009's password verification and T011's two-step modal (which remains on the `"password"` step on failure, per its task description) already satisfy this story.*

**Checkpoint**: US1 and US2 both verified — the delete flow's safety net is proven from every angle (wrong password, retry, cancel at either step).

---

## Phase 5: User Story 3 - Non-admins cannot delete a space (Priority: P3)

**Goal**: A user without ADMIN on the target space (and not a company admin) can never delete it, in the UI or via a direct request, and this holds even across a full request pipeline (not just a mocked service call).

**Independent Test**: Sign in as a space's EDITOR/VIEWER, confirm no Delete action is visible; issue the raw `DELETE /v1/spaces/{id}` request directly and confirm it's rejected with nothing removed.

> Note: T008's `PermissionError` branch and T012's `isAdmin`-gated Delete link already implement this — Phase 3's T005/T006/T007 already unit-test it with mocks. This phase adds one new end-to-end proof through the real request pipeline, mirroring `test_create_space_rejects_cross_company_parent` in `specs/051-add-space/tasks.md`.

### Tests for User Story 3

- [X] T016 [P] [US3] Add a `test_delete_space_rejects_non_admin_and_cross_company_callers` case (or two cases, one per condition) to `apps/api/tests/test_space_hierarchy_isolation.py`'s `TestCrossTenantIsolation` class, mirroring `test_create_space_rejects_cross_company_parent`'s `two_company_setup` fixture and `_bypass_onboarding` pattern: (a) as a Company A user with only `VIEWER`/`EDITOR` access on a Company A space, `DELETE /v1/spaces/{id}` with the correct password → expect `403`, and a subsequent `GET /v1/spaces` still lists it; (b) as a Company A user, `DELETE /v1/spaces/{id}` targeting a real Company B space with the correct password → expect `404`, and the Company B space is unaffected. Run and confirm both pass immediately (T008/T009 already implement both rejections).

### Implementation for User Story 3

*No new production code — T008's authorization check and T009's endpoint wiring already satisfy this story.*

**Checkpoint**: All three user stories independently verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Meet Constitution Principle V (Ruff + Black) and confirm the full suite and the manual quickstart both pass.

- [X] T017 [P] Run Ruff on all modified/added Python files: `cd packages/core && .venv/bin/ruff check tessera_core/services/space_hierarchy.py tessera_core/ports/repositories/space.py tests/test_space_hierarchy.py` and `cd apps/api && .venv/bin/ruff check tessera_api/adapters/repositories/space.py tessera_api/routers/spaces.py tests/unit/test_spaces_router.py tests/test_space_hierarchy_isolation.py tests/integration/test_space_delete_cascade.py`
- [X] T018 [P] Run Black on the same files: `cd packages/core && .venv/bin/black tessera_core/services/space_hierarchy.py tessera_core/ports/repositories/space.py tests/test_space_hierarchy.py` and `cd apps/api && .venv/bin/black tessera_api/adapters/repositories/space.py tessera_api/routers/spaces.py tests/unit/test_spaces_router.py tests/test_space_hierarchy_isolation.py tests/integration/test_space_delete_cascade.py`
- [X] T019 Run the full backend suite to confirm no regressions: `cd packages/core && .venv/bin/python -m pytest -v --no-cov` and `cd apps/api && .venv/bin/python -m pytest tests/unit tests/test_space_hierarchy_isolation.py tests/integration -v --no-cov` (the cascade integration test skips cleanly if no local Postgres is running)
- [X] T020 Run the full frontend suite: `cd apps/web && npx vitest run` and confirm no regressions in `spaces.test.tsx`, `space-add.test.tsx`, `space-rename.test.tsx`, `space-drag-drop.test.tsx`, `space-folder-view.test.tsx`
- [ ] T021 Walk through `specs/052-delete-space/quickstart.md` Scenarios 1-7 against a local `make dev` stack (admin cascade delete, wrong password, cancel at both steps, non-admin 403, company-admin bypass, cross-tenant 404, double-delete 404)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user story tasks (nothing can delete a subtree without T004).
- **User Story 1 (Phase 3)**: Depends on Foundational. Delivers the full stack (service, endpoint, modal, page wiring) — this is the MVP.
- **User Story 2 (Phase 4)**: Depends on US1's T009 (password check) and T011 (two-step modal) existing — test-only.
- **User Story 3 (Phase 5)**: Depends on US1's T008 (authorization) and T009 (endpoint) existing — test-only.
- **Polish (Phase 6)**: Depends on Phases 3-5 being complete.

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on other stories — the MVP.
- **User Story 2 (P2)**: Builds on US1's T009/T011 — proves the safety net from new angles, adds no new production code.
- **User Story 3 (P3)**: Builds on US1's T008/T009 — proves authorization end-to-end, adds no new production code.

### Within Each User Story

- Tests are written and confirmed failing before implementation in US1 (true TDD, since T008-T013 are new production code).
- US2's tests (T015) are written after T009/T011 exist and are expected to pass immediately, proving the already-built safety net from the retry/cancel angles.
- US3's test (T016) is written after T008/T009 exist and is expected to pass immediately, proving authorization through the real request pipeline rather than a mocked service.

### Parallel Opportunities

- T002 and T003 (Foundational) touch different files/packages and can run in parallel.
- T005, T006, T007 (US1 tests) touch three different files (`packages/core`, `apps/api`, `apps/web`) and can be written in parallel.
- T010 and T011 (frontend `api.ts` change and new modal) touch different files and can be written in parallel with each other, and in parallel with T008/T009 (backend), since the modal only depends on the endpoint's *contract* (already fixed in `contracts/delete-space-endpoint.md`), not its implementation.
- T017 and T018 (Ruff/Black) are non-conflicting tooling passes over the same file set and can run back-to-back or in parallel processes.

---

## Parallel Example: User Story 1 tests

```bash
# Launch all three US1 test-writing tasks together (different files, no shared state):
Task: "Add TestDeleteValidations to packages/core/tests/test_space_hierarchy.py"
Task: "Add TestDeleteSpace to apps/api/tests/unit/test_spaces_router.py"
Task: "Create apps/web/tests/space-delete.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (subtree cascade proven against a real DB).
3. Complete Phase 3: User Story 1 (T005-T007 failing tests → T008-T013 implementation → T014 green).
4. **STOP and VALIDATE**: An admin can delete a space and everything inside it, end-to-end, with password re-verification, tenant isolation, and audit logging. This alone satisfies the feature's core request.

### Incremental Delivery

1. Setup + Foundational → the database can resolve and remove a full space subtree correctly.
2. US1 → cascading delete ships as the MVP, including its own necessary password and permission checks.
3. US2 → the wrong-password/cancel safety net is explicitly proven from every angle.
4. US3 → non-admin rejection is explicitly proven end-to-end.
5. Polish → lint/format/full-suite/quickstart pass.

### Notes

- [P] tasks touch different files and have no shared state.
- Commit after each checkpoint (end of Phase 2, Phase 3, Phase 4, Phase 5, Phase 6), not after every individual task.
- No database migration is required anywhere in this feature — every FK cascade it relies on (`documents`, `document_versions`, `document_drafts`, `chunks`, `space_memberships`, `role_permissions`, `connectors`) already exists; only the recursive descendant-resolution query is new application code.
- T003's integration test requires a local Postgres instance to actually execute (it skips cleanly otherwise, per the existing `test_document_draft_repository.py` convention) — do not treat a skip as a failure, but do run it against a real database at least once before considering this feature done, since it's the only automated proof that descendant spaces are actually removed rather than orphaned.
