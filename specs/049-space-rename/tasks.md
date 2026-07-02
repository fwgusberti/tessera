# Tasks: Space Rename

**Input**: Design documents from `specs/049-space-rename/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**TDD**: Constitution Principle IV is non-negotiable — each new test below MUST be written and confirmed FAILING before its corresponding implementation task, except where explicitly noted (US2/US3 tests that prove behavior already delivered by an earlier task, mirroring the pattern in `specs/048-delete-document/tasks.md`).

**Organization**: Tasks are grouped by user story (spec.md priorities P1/P2/P3). US1 delivers the full admin-rename stack (domain service, endpoint, modal, wiring into both space-browsing pages) as the MVP. US2 reuses US1's admin gate — it adds explicit coverage proving non-admin roles are denied both in the UI and at the domain layer (mostly tests, one already-satisfied guard). US3 is test-only, proving the failure-feedback behavior US1's modal already implements.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Verify Environment)

**Purpose**: Confirm the test environment is functional across all three touched layers before making changes.

- [X] T001 Confirm a passing baseline: `cd packages/core && .venv/bin/python -m pytest tests/ -v --no-cov`, `cd apps/api && .venv/bin/python -m pytest tests/unit -v --no-cov`, and `cd apps/web && npx vitest run`

---

## Phase 2: Foundational (Repository Rename Capability — Blocks All User Stories)

**Purpose**: Add the one piece of infrastructure every user story depends on: a way to actually persist a new `name` on a `spaces` row, mirroring the existing `set_parent`/`remove_parent` methods this repository already has.

**⚠️ CRITICAL**: No user story task can begin until this phase is complete.

- [X] T002 [P] Add abstract `async def rename(self, space_id: UUID, name: str) -> Space: ...` to `SpaceRepository` in `packages/core/tessera_core/ports/repositories/space.py`, placed directly after the existing `remove_parent` abstract method, with a docstring `"""Set name on space_id; returns updated Space."""`.
- [X] T003 [P] Implement `rename` in `SqlSpaceRepository` in `apps/api/tessera_api/adapters/repositories/space.py`, placed directly after `remove_parent`. Mirror that method's exact shape: `await self._session.execute(update(SpaceModel).where(SpaceModel.id == space_id).values(name=name))`, then `await self._session.flush()`, then re-select and return via `_space_from_model`.

**Checkpoint**: The database can now persist a renamed space. User story implementation can begin.

---

## Phase 3: User Story 1 - Rename a space from the Spaces browser (Priority: P1) 🎯 MVP

**Goal**: A space admin can rename a space they administer from the Spaces menu (top-level Spaces page or a space's folder view), with the change reflected immediately and persisted.

**Independent Test**: Sign in as a space admin, open `/spaces`, click **Rename** on a tile, submit a new name, and verify the tile updates immediately and the name persists after reload.

### Tests for User Story 1 (TDD — MUST FAIL before implementation)

> **⚠️ Write and confirm FAILING before starting T007**

- [X] T004 [P] [US1] Add a `TestRenameValidations` class to `packages/core/tests/test_space_hierarchy.py`, directly after `TestSetParentValidations`, following its exact mocking style (`AsyncMock()` for `space_repo`/`membership_repo`, a local `_space`/`_membership` helper already defined in this file). Cases: `test_missing_space_raises_value_error` (`space_repo.get_by_id_for_company` returns `None` → `ValueError` matching `"not_found"`), `test_missing_admin_raises_permission_error` (space resolves, but `membership_repo.get` returns a `VIEWER` membership → `PermissionError`), `test_empty_name_raises_value_error` (space resolves, actor is `ADMIN`, `name="   "` → `ValueError` matching `"empty_name"`), `test_name_too_long_raises_value_error` (space resolves, actor is `ADMIN`, `name="x" * 256` → `ValueError` matching `"name_too_long"`), `test_admin_can_rename_returns_updated_space` (space resolves, actor is `ADMIN`, `name="New Name"`, `space_repo.rename` mocked to return the updated `Space` → asserts `space_repo.rename` was awaited with `(space.id, "New Name")` and the method returns that updated space). Call `svc.rename(actor_id=..., space_id=..., name=..., company_id=...)` (does not exist yet). Run and confirm all FAIL with an `AttributeError`.
- [X] T005 [P] [US1] Add rename-endpoint tests to `apps/api/tests/unit/test_spaces_router.py`, following the exact `_ctx` helper and `patch("tessera_api.routers.spaces.SqlSpaceRepository", ...)` / `patch("tessera_api.routers.spaces.SqlSpaceMembershipRepository", ...)` / `patch("tessera_api.routers.spaces.write_audit", new=AsyncMock())` style already in this file, but additionally patch `tessera_api.routers.spaces.SpaceHierarchyService` (constructed by the handler, so patch it to return a `mock_svc = AsyncMock()` and set `mock_svc.rename` directly) so the router is tested in isolation from the domain service. Add a class `TestRenameSpace` with: `test_admin_rename_returns_200_and_writes_audit` (`mock_svc.rename` resolves to an updated space stub with `model_dump` — reuse the `type("S", (), {...})()` pattern from `TestCreateSpaceGrantsCreatorMembership` — assert the response is `{"space": {...}}` and `mock_audit` was awaited once with `action="space_renamed"`), `test_non_admin_rename_returns_403` (`mock_svc.rename` raises `PermissionError` → assert the handler raises an `HTTPException` with `status_code=403` and `mock_audit` was NOT called), `test_missing_or_cross_tenant_rename_returns_404_and_audits` (`mock_svc.rename` raises `ValueError("not_found")` → assert `HTTPException` with `status_code=404` and `mock_audit` WAS awaited once with `action="cross_tenant_denied"`), `test_empty_name_rename_returns_400` (`mock_svc.rename` raises `ValueError("empty_name")` → assert `HTTPException` with `status_code=400` and `mock_audit` was NOT called). Import `RenameSpaceRequest, rename_space` from `tessera_api.routers.spaces` (do not exist yet). Run and confirm all FAIL with an `ImportError`.
- [X] T006 [P] [US1] Create `apps/web/tests/space-rename.test.tsx`, following the exact mocking structure of `apps/web/tests/space-drag-drop.test.tsx` (`vi.mock("@/lib/api", () => ({ api: { patch: vi.fn() } }))`, a local `makeAccess(id, name, parentId, role)` helper copied from that file). Cases: `it("shows a Rename control on an admin's folder tile")` (render `FolderTile` with an `admin`-role access and an `onRename` prop, assert `screen.getByRole("button", { name: /rename/i })` exists), `it("does not show a Rename control on a non-admin's folder tile")` (render `FolderTile` with a `viewer`-role access, assert `screen.queryByRole("button", { name: /rename/i })` is null), `it("pre-fills the current name and calls PATCH .../name on save")` (render `RenameSpaceModal` directly with a `space` prop and `onUpdated`/`onClose` callbacks, assert the text input's initial value is the space's current name, change it, click **Save**, assert `mockApi.patch` was called with `` `/v1/spaces/${space.id}/name` `` and `{ name: "New Name" }`, and `onUpdated` was called with the resolved space), `it("rejects an empty name without calling the API")` (render `RenameSpaceModal`, clear the input, click **Save**, assert `screen.getByRole("alert")` (or equivalent inline error) appears and `mockApi.patch` was NOT called), `it("does nothing on Cancel")` (render `RenameSpaceModal`, change the input, click **Cancel**, assert `mockApi.patch` was NOT called and `onClose` was called). Run and confirm all FAIL (neither `FolderTile`'s Rename control nor `RenameSpaceModal` exist yet).

### Implementation for User Story 1

- [X] T007 [US1] Implement `rename(self, actor_id: UUID, space_id: UUID, name: str, company_id: UUID) -> Space` in `SpaceHierarchyService` (`packages/core/tessera_core/services/space_hierarchy.py`), placed after `remove_parent`. Body: resolve `space = await self._spaces.get_by_id_for_company(space_id, company_id)`, raise `ValueError("not_found")` if `None`; check `membership = await self._memberships.get(space_id, actor_id)`, raise `PermissionError("Actor must be admin of space")` if `membership is None or membership.role != SpaceRole.ADMIN`; compute `trimmed = name.strip()`, raise `ValueError("empty_name")` if falsy, raise `ValueError("name_too_long")` if `len(trimmed) > 255`; return `await self._spaces.rename(space_id, trimmed)`. Run T004 and confirm it now passes. (depends on T002, T004)
- [X] T008 [US1] In `apps/api/tessera_api/routers/spaces.py`: add `class RenameSpaceRequest(BaseModel): name: str` next to `SetParentRequest`; add a `_invalid_name(reason: str) -> HTTPException` helper next to `_invalid_parent`, returning `400` with `{"error": {"code": "invalid_name", "message": reason}}`; add `@router.patch("/spaces/{space_id}/name")` handler `rename_space(space_id: UUID, body: RenameSpaceRequest, ctx: CompanyContext, session: SessionDep) -> dict`, placed after `remove_space_parent`. Body: unpack `user_info, company_id = ctx`, `user_id = UUID(user_info["sub"])`; build `repo`/`membership_repo`/`svc` exactly like `set_space_parent`; call `updated = await svc.rename(actor_id=user_id, space_id=space_id, name=body.name, company_id=company_id)` inside a `try`; on `PermissionError` raise `_forbidden()`; on `ValueError` as `exc`, if `str(exc) == "not_found"` write a `cross_tenant_denied` audit (same shape as `get_space`'s cross-tenant audit, `entity_type="space"`, `entity_id=space_id`, `metadata={"company_id": str(company_id)}`), `await session.commit()`, then raise `_not_found()`; otherwise raise `_invalid_name(str(exc))`; on success, write an audit record (`action="space_renamed"`, `entity_type="space"`, `entity_id=space_id`, `metadata={"new_name": updated.name}`) and return `{"space": _space_response(updated)}`. Run T005 and confirm it now passes. (depends on T003, T007, T005)
- [X] T009 [P] [US1] Create `apps/web/components/spaces/RenameSpaceModal.tsx`, structurally mirroring `SetParentModal.tsx`: props `{ space: Space; onClose: () => void; onUpdated: (updated: Space) => void }`; local state `name` (initialized to `space.name`), `error`, `loading`; a `handleSave` async function that trims `name`, and if empty sets a local validation `error` without calling the API, otherwise calls `await api.patch<{ space: Space }>(\`/v1/spaces/${space.id}/name\`, { name: trimmed })`, then `onUpdated(data.space); onClose();`, catching failures into `error` via the same `err instanceof Error ? err.message : "Failed to rename space."` pattern as `SetParentModal`; render a labeled text `<input>` pre-filled with `space.name`, an inline `role="alert"` error message when `error` is set, and **Cancel**/**Save** buttons matching `SetParentModal`'s button styling (`indigo-600`/`indigo-700` per the constitution's UI Design System).
- [X] T010 [US1] In `apps/web/components/spaces/FolderTile.tsx`: add an `onRename?: () => void` prop; render a "Rename" button next to the existing "Set parent" button, guarded by the same `isAdmin && onRename` condition, calling `onRename` on click, matching the existing button's `text-xs text-slate-400 hover:text-indigo-600 underline` styling.
- [X] T011 [US1] In `apps/web/components/spaces/FolderGrid.tsx`: add an `onRename?: (space: Space) => void` prop to `FolderGridProps`; pass `onRename={onRename ? () => onRename(access.space) : undefined}` to each `FolderTile`, alongside the existing `onSetParent` wiring.
- [X] T012 [US1] In `apps/web/app/spaces/page.tsx`: add `const [renamingSpace, setRenamingSpace] = useState<Space | null>(null);` next to `managingSpace`; pass `onRename={(space) => setRenamingSpace(space)}` to `FolderGrid`; render `{renamingSpace && <RenameSpaceModal space={renamingSpace} onClose={() => setRenamingSpace(null)} onUpdated={handleSpaceUpdated} />}` next to the existing `SetParentModal` render, importing `RenameSpaceModal`.
- [X] T013 [US1] In `apps/web/app/spaces/[id]/page.tsx`: apply the identical `renamingSpace` state, `onRename` wiring, and `RenameSpaceModal` render as T012, reusing the existing `handleSpaceUpdated` callback.
- [X] T014 [US1] Run T006 and confirm all five cases now pass. Then run `cd packages/core && .venv/bin/python -m pytest tests/test_space_hierarchy.py -v --no-cov`, `cd apps/api && .venv/bin/python -m pytest tests/unit/test_spaces_router.py -v --no-cov`, and `cd apps/web && npx vitest run tests/space-rename.test.tsx`, confirming no regressions in neighboring tests in the same files. (depends on T007, T008, T009, T010, T011, T012, T013)

**Checkpoint**: MVP complete — a space admin can rename a space end-to-end, from either space-browsing page, with tenant isolation, audit logging, and a working save/cancel/validation UI.

---

## Phase 4: User Story 2 - Rename restricted to authorized users (Priority: P2)

**Goal**: Non-admin members never see a Rename control, and a direct API rename attempt from a non-admin is rejected without changing the space.

**Independent Test**: Log in as a viewer or editor, confirm no Rename control appears on that space's tile; confirm a direct API rename request for that space returns 403 and leaves the name unchanged.

> Note: `SpaceHierarchyService.rename` (T007) and `FolderTile`'s `isAdmin && onRename` guard (T010) already implement the non-admin denial from both angles — these tasks prove that existing behavior for the specific roles this story calls out, per the pattern used for US2 in `specs/048-delete-document/tasks.md`. If any of them fail, fix T007/T010, do not add new production code.

### Tests for User Story 2

- [X] T015 [P] [US2] Extend `TestRenameValidations` in `packages/core/tests/test_space_hierarchy.py` with `test_editor_role_raises_permission_error` (space resolves, `membership_repo.get` returns an `EDITOR` membership → `PermissionError`), proving the admin gate rejects every non-admin role, not just `VIEWER`. Run and confirm it passes immediately.
- [X] T016 [P] [US2] Extend `apps/web/tests/space-rename.test.tsx` with `it("does not show a Rename control on an editor's folder tile")` (render `FolderTile` with an `editor`-role access, assert `screen.queryByRole("button", { name: /rename/i })` is null). Run and confirm it passes immediately.

### Implementation for User Story 2

*No new production code — T007's role check (`membership.role != SpaceRole.ADMIN`) and T010's `isAdmin` guard already reject every non-admin role. This phase is test-only, confirming FR-002/FR-005 and Acceptance Scenarios 1-2 of US2.*

**Checkpoint**: US1 and US2 both verified — only space admins can rename, from every layer (UI visibility and direct API access).

---

## Phase 5: User Story 3 - Feedback on rename failure (Priority: P3)

**Goal**: A failed rename shows a clear error, keeps the original name displayed, and lets the admin retry.

**Independent Test**: Simulate a failed rename request and confirm the UI shows an error, the tile still shows the original name, and resubmitting follows the same flow.

> Note: T009's `RenameSpaceModal` already wraps the `api.patch` call in a `try`/`catch` that sets a local `error` and does not call `onUpdated` on failure, so the tile is never updated with a name that wasn't actually saved. This phase is test-only, per the same convention used for US3 in `specs/048-delete-document/tasks.md`.

### Tests for User Story 3

- [X] T017 [US3] Extend `apps/web/tests/space-rename.test.tsx` with `it("shows an error and keeps the modal open with the original name displayed elsewhere when save fails")`: `mockApi.patch.mockRejectedValue(new Error("Server error — please try again."))`, render `RenameSpaceModal` with `onUpdated` and `onClose` spies, change the input, click **Save**, assert `screen.getByRole("alert")` shows the error message, `onUpdated` was NOT called, and `onClose` was NOT called (modal stays open for retry). Then, with `mockApi.patch.mockResolvedValueOnce({ space: { ...space, name: "Retried Name" } })`, click **Save** again and assert `onUpdated` is now called with the updated space. Run and confirm it passes (no new production code expected — if it fails, fix T009, not this test).

### Implementation for User Story 3

*No new production code — T009's existing error-handling already satisfies this story.*

**Checkpoint**: All three user stories independently verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Meet Constitution Principle V (Ruff + Black) and confirm the full suite and the manual quickstart both pass.

- [X] T018 [P] Run Ruff on all modified/added Python files: `cd packages/core && .venv/bin/ruff check tessera_core/ports/repositories/space.py tessera_core/services/space_hierarchy.py tests/test_space_hierarchy.py` and `cd apps/api && .venv/bin/ruff check tessera_api/adapters/repositories/space.py tessera_api/routers/spaces.py tests/unit/test_spaces_router.py`
- [X] T019 [P] Run Black on the same files: `cd packages/core && .venv/bin/black tessera_core/ports/repositories/space.py tessera_core/services/space_hierarchy.py tests/test_space_hierarchy.py` and `cd apps/api && .venv/bin/black tessera_api/adapters/repositories/space.py tessera_api/routers/spaces.py tests/unit/test_spaces_router.py`
- [X] T020 Run the full backend suite to confirm no regressions: `cd packages/core && .venv/bin/python -m pytest -v --no-cov` and `cd apps/api && .venv/bin/python -m pytest tests/unit -v --no-cov`
- [X] T021 Run the full frontend suite: `cd apps/web && npx vitest run` and confirm no regressions in `spaces.test.tsx`, `space-drag-drop.test.tsx`, `space-folder-view.test.tsx`
- [X] T022 Walk through `specs/049-space-rename/quickstart.md` Scenarios 1-6 against a local `make dev` stack (admin rename, empty-name rejection, cancel, non-admin 403, duplicate-name allowed, cross-tenant 404)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user story tasks (nothing can rename a space without T003).
- **User Story 1 (Phase 3)**: Depends on Foundational. Delivers the full stack (domain service, endpoint, modal, two-page wiring) — this is the MVP.
- **User Story 2 (Phase 4)**: Depends on US1's T007/T010 existing — adds role-coverage tests (pass immediately).
- **User Story 3 (Phase 5)**: Depends on US1's T009 existing — test-only.
- **Polish (Phase 6)**: Depends on Phases 3-5 being complete.

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on other stories — the MVP.
- **User Story 2 (P2)**: Builds on US1's `SpaceHierarchyService.rename` role check (T007) and `FolderTile`'s admin guard (T010) — no new production code.
- **User Story 3 (P3)**: Builds on US1's `RenameSpaceModal` error handling (T009) — proves it, adds no new production code.

### Within Each User Story

- Tests are written and confirmed failing before implementation in US1 (true TDD, since T007-T013 are new production code).
- US2's tests (T015/T016) are written after T007/T010 exist and are expected to pass immediately, proving those tasks already generalize correctly across non-admin roles — per the same convention used in `specs/048-delete-document/tasks.md` for its US2.
- US3's test (T017) is written after T009 exists and is expected to pass immediately.

### Parallel Opportunities

- T002 and T003 (Foundational) touch different packages (`packages/core` vs `apps/api`) and can run in parallel.
- T004, T005, T006 (US1 tests) touch three different files (`packages/core`, `apps/api`, `apps/web`) and can be written in parallel.
- T009 (frontend modal) can be written in parallel with T007/T008 (backend) since the modal only depends on the endpoint's *contract* (already fixed in contracts/rename-space-endpoint.md), not its implementation.
- T015 and T016 (US2 tests) touch different files and can run in parallel.
- T018 and T019 (Ruff/Black) are non-conflicting tooling passes over the same file set and can run back-to-back or in parallel processes.

---

## Parallel Example: User Story 1 tests

```bash
# Launch all three US1 test-writing tasks together (different files, no shared state):
Task: "Add TestRenameValidations to packages/core/tests/test_space_hierarchy.py"
Task: "Add rename-endpoint tests to apps/api/tests/unit/test_spaces_router.py"
Task: "Create apps/web/tests/space-rename.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (repository `rename()`).
3. Complete Phase 3: User Story 1 (T004-T006 failing tests → T007-T013 implementation → T014 green).
4. **STOP and VALIDATE**: A space admin can rename a space end-to-end, from either browsing page, with tenant isolation and audit logging. This alone satisfies the feature's core request ("add space rename feature in spaces menu").

### Incremental Delivery

1. Setup + Foundational → the database can persist a renamed space.
2. US1 → admin rename ships as the MVP.
3. US2 → non-admin denial is explicitly proven across roles and layers (mostly test coverage).
4. US3 → the failure-feedback guarantee is explicitly proven.
5. Polish → lint/format/full-suite/quickstart pass.

### Notes

- [P] tasks touch different files and have no shared state.
- Commit after each checkpoint (end of Phase 2, Phase 3, Phase 4, Phase 5, Phase 6), not after every individual task.
- No database migration is required anywhere in this feature — `spaces.name` already exists as `String(255) NOT NULL`.
