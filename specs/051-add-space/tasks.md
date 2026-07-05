# Tasks: Add Space

**Input**: Design documents from `specs/051-add-space/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**TDD**: Constitution Principle IV is non-negotiable — each new test below MUST be written and confirmed FAILING before its corresponding implementation task, except where explicitly noted (US2/US3 tests that prove behavior already delivered by an earlier task, mirroring the pattern used in `specs/049-space-rename/tasks.md`).

**Organization**: Tasks are grouped by user story (spec.md priorities P1/P2/P3). US1 delivers the full top-level "Add Space" stack — and, because it is one cohesive domain method, also the backend logic for nested (sub-space) creation — as the MVP. US2 exposes that already-implemented nested-creation capability through a second UI entry point (the folder-view "Add Space" button) and adds dedicated backend isolation coverage for it. US3 is test-only, proving the failure-feedback behavior US1's modal already implements for both entry points.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Verify Environment)

**Purpose**: Confirm the test environment is functional across all three touched layers before making changes.

- [X] T001 Confirm a passing baseline: `cd packages/core && .venv/bin/python -m pytest tests/ -v --no-cov`, `cd apps/api && .venv/bin/python -m pytest tests/unit tests/test_space_hierarchy_isolation.py -v --no-cov`, and `cd apps/web && npx vitest run`

---

## Phase 2: Foundational (Slug Generation Infrastructure — Blocks All User Stories)

**Purpose**: Add the one piece of infrastructure every creation path depends on: deriving a globally-unique `slug` from a user-supplied `name` when the caller doesn't provide one, so the "Add Space" form never has to ask the user for it.

**⚠️ CRITICAL**: No user story task can begin until this phase is complete.

- [X] T002 [P] Create `packages/core/tests/test_slug.py` with a `slugify()` test suite: `test_lowercases_and_hyphenates_spaces` (`"Marketing Ops"` → `"marketing-ops"`), `test_strips_accents` (`"Jurídico"` → `"juridico"`), `test_collapses_symbols_and_repeated_hyphens` (`"Q3 -- Campaigns!!"` → `"q3-campaigns"`), `test_strips_leading_and_trailing_hyphens` (`"---Ops---"` → `"ops"`), `test_falls_back_to_space_when_result_is_empty` (`"🎉🎉🎉"` → `"space"`), `test_truncates_to_max_length` (a 150-char name with `max_length=20` produces a ≤20-char, non-hyphen-terminated result). Run and confirm all FAIL with `ModuleNotFoundError` (the module doesn't exist yet).
- [X] T003 [P] Add an abstract `async def slug_exists(self, slug: str) -> bool: ...` to `SpaceRepository` in `packages/core/tessera_core/ports/repositories/space.py`, placed directly after the existing `rename` abstract method, with a docstring `"""Return True if a space with this slug already exists (slugs are globally unique)."""`.
- [X] T004 Implement `slugify(value: str, max_length: int = 100) -> str` in new `packages/core/tessera_core/services/slug.py` (stdlib `unicodedata` + `re` only): NFKD-normalize and strip combining marks, lowercase, replace runs of non `[a-z0-9]` characters with a single hyphen, strip leading/trailing hyphens, truncate to `max_length` re-stripping any trailing hyphen left by truncation, and return `"space"` if the result is empty. Run T002 and confirm it now passes. (depends on T002)
- [X] T005 [P] Implement `slug_exists` in `SqlSpaceRepository` in `apps/api/tessera_api/adapters/repositories/space.py`, placed directly after `rename`: `result = await self._session.execute(select(SpaceModel.id).where(SpaceModel.slug == slug)); return result.scalar_one_or_none() is not None`. (depends on T003)

**Checkpoint**: A name can now be turned into a unique slug. User story implementation can begin.

---

## Phase 3: User Story 1 - Create a new top-level space from the Spaces page (Priority: P1) 🎯 MVP

**Goal**: Any user belonging to an active company can create a new top-level space from the Spaces page by entering just a name, and is immediately granted full admin access to it.

**Independent Test**: Sign in as a company member, open `/spaces`, click **Add Space**, submit a name, and verify a new tile appears immediately, persists after reload, and the creator has admin controls (Rename, Set parent, Members) on it.

> **Scope note**: Because `SpaceHierarchyService.create` is one cohesive method, this phase also implements the nested-creation (`parent_space_id`) branch and its validation (reusing `set_parent`'s parent-admin and depth-limit checks) — User Story 2 only adds the *second UI entry point* (the folder-view button) and dedicated isolation coverage for a capability the backend already has after this phase.

### Tests for User Story 1 (TDD — MUST FAIL before implementation)

> **⚠️ Write and confirm FAILING before starting T009**

- [X] T006 [P] [US1] Add a `TestCreateValidations` class to `packages/core/tests/test_space_hierarchy.py`, directly after `TestRenameValidations`, following its exact mocking style (`AsyncMock()` for `space_repo`/`membership_repo`, the file's existing `_space`/`_membership` helpers). Cases: `test_empty_name_raises_value_error` (`name="   "` → `ValueError` matching `"empty_name"`), `test_name_too_long_raises_value_error` (`name="x" * 256` → `ValueError` matching `"name_too_long"`), `test_root_creation_generates_slug_and_defaults_sector` (no `slug`/`sector` given, `space_repo.slug_exists` mocked to return `False`, `space_repo.create` mocked to return its input unchanged → assert `space_repo.create` was awaited with a `Space` whose `slug == "marketing"` for `name="Marketing"` and `sector == "General"`, and `parent_space_id is None`), `test_slug_collision_appends_numeric_suffix` (`space_repo.slug_exists` mocked with `side_effect=[True, False]` → assert the created `Space.slug == "marketing-2"`), `test_explicit_slug_and_sector_pass_through_unchanged` (`slug="eng"`, `sector="tech"` given → assert `space_repo.slug_exists` was NOT called and the created `Space` has `slug="eng"`, `sector="tech"`), `test_missing_parent_raises_cross_company_value_error` (`parent_space_id` given, `space_repo.get_by_id_for_company` returns `None` → `ValueError` matching `"cross_company"`, and `space_repo.create` NOT called), `test_non_admin_of_parent_raises_permission_error` (parent resolves, `membership_repo.get(parent_id, actor_id)` returns a `VIEWER` membership → `PermissionError`, `space_repo.create` NOT called), `test_depth_limit_raises_value_error` (parent resolves, actor is `ADMIN` of parent, `space_repo.get_ancestor_chain(parent_id)` returns a 9-element list → `ValueError` matching `"depth_limit"`, `space_repo.create` NOT called), `test_nested_creation_sets_parent_space_id` (parent resolves, actor is `ADMIN` of parent, ancestor chain short → assert the created `Space.parent_space_id == parent_id`). Call `svc.create(actor_id=..., company_id=..., name=..., sector=..., slug=..., parent_space_id=...)` (does not exist yet). Run and confirm all FAIL with an `AttributeError`.
- [X] T007 [P] [US1] In `apps/api/tests/unit/test_spaces_router.py`: (a) update the two existing tests in `TestCreateSpaceGrantsCreatorMembership` (`test_create_space_adds_admin_membership_for_caller`, `test_create_space_response_shape_unchanged`) to patch `tessera_api.routers.spaces.SpaceHierarchyService` (returning a `mock_svc = AsyncMock()` with `mock_svc.create` resolving to the same stub currently returned by `mock_space_repo.create`) instead of asserting against `SqlSpaceRepository` directly — mirror the `TestRenameSpace` patching style. Update the audit assertion from `mock_audit.assert_awaited_once()` to asserting `mock_audit.await_count == 2`, with `mock_audit.call_args_list[0].kwargs["action"] == "space_created"` and `mock_audit.call_args_list[1].kwargs["action"] == "member_invited"`. (b) Add a new `TestCreateSpaceRequestDefaults` class: `test_name_only_defaults_slug_sector_and_parent_to_none` (`CreateSpaceRequest(name="Eng")` → `.slug is None`, `.sector == "General"`, `.parent_space_id is None`). (c) Add a new `TestCreateSpaceValidationErrors` class, patching `SpaceHierarchyService`/`SqlSpaceRepository`/`SqlSpaceMembershipRepository`/`write_audit` exactly like `TestRenameSpace`: `test_invalid_name_returns_400_and_no_membership` (`mock_svc.create` raises `ValueError("empty_name")` → `HTTPException` `status_code=400`, `mock_membership_repo.add` NOT called, `mock_audit` NOT called), `test_invalid_parent_returns_400` (`mock_svc.create` raises `ValueError("cross_company")` → `status_code=400`), `test_depth_limit_returns_400` (`mock_svc.create` raises `ValueError("depth_limit")` → `status_code=400`), `test_non_admin_of_parent_returns_403_and_no_membership` (`mock_svc.create` raises `PermissionError(...)` → `status_code=403`, `mock_membership_repo.add` NOT called), `test_success_with_parent_writes_space_created_audit_with_parent_metadata` (`mock_svc.create` resolves to a stub with a `parent_space_id`; body includes `parent_space_id` → assert `mock_audit.call_args_list[0].kwargs["metadata"]["parent_space_id"] == str(parent_id)`). Run (a)-(c) and confirm the updated/new tests FAIL (router doesn't call `SpaceHierarchyService.create` yet, and `CreateSpaceRequest` still requires `slug`/`sector`).
- [X] T008 [P] [US1] Create `apps/web/tests/space-add.test.tsx`, following the exact mocking structure of `apps/web/tests/space-rename.test.tsx` (`vi.mock("@/lib/api", ...)` with both `get` and `post` mocked, since `SpacesPage` fetches on mount). Cases: `it("shows an Add Space button on the Spaces page")` (mock `api.get` to resolve an empty space list, render `SpacesPage`, assert `screen.getByRole("button", { name: /add space/i })` exists), `it("does nothing on Cancel")` (open the modal, type a name, click **Cancel**, assert `mockApi.post` was NOT called and no new tile appears), `it("rejects an empty name without calling the API")` (open the modal, submit with an empty/whitespace name, assert an inline error appears and `mockApi.post` was NOT called), `it("creates a top-level space and shows it immediately without a reload")` (mock `api.post` to resolve `{ space: { id, name: "Marketing", slug: "marketing", sector: "General", parent_space_id: null, ... } }`, open the modal, type "Marketing", click **Create**, assert `mockApi.post` was called with `"/v1/spaces"` and `{ name: "Marketing" }` (no `parent_space_id` key), and a new tile with that name appears in the grid without any additional `api.get` call). Run and confirm all FAIL (`AddSpaceModal` and the button don't exist yet).

### Implementation for User Story 1

- [X] T009 [US1] Implement `create(self, actor_id: UUID, company_id: UUID, name: str, sector: str = "General", slug: str | None = None, parent_space_id: UUID | None = None, default_language: str = "pt-BR", retention_policy: dict | None = None, confidence_threshold: float = 0.7) -> Space` in `SpaceHierarchyService` (`packages/core/tessera_core/services/space_hierarchy.py`), placed after `rename`, importing `slugify` from `tessera_core.services.slug`. Body: trim/validate `name` exactly like `rename` (`ValueError("empty_name")` / `ValueError("name_too_long")`); if `parent_space_id` is not `None`, resolve it via `get_by_id_for_company` (miss → `ValueError("cross_company")`), check the actor holds `SpaceRole.ADMIN` there via `self._memberships.get` (miss/non-admin → `PermissionError`), and check `len(await self._spaces.get_ancestor_chain(parent_space_id)) + 1 >= _MAX_DEPTH` (→ `ValueError("depth_limit")`); resolve the slug via a private `_resolve_slug(slug, trimmed_name)` helper (pass through if truthy, else loop `slugify(name)`, `f"{base}-2"`, `f"{base}-3"`, ... against `self._spaces.slug_exists` until unique, truncating each candidate to 100 chars); construct and `return await self._spaces.create(Space(slug=resolved_slug, name=trimmed, sector=sector.strip() or "General", company_id=company_id, parent_space_id=parent_space_id, retention_policy=retention_policy or {}, confidence_threshold=confidence_threshold, default_language=default_language))`. Run T006 and confirm it now passes. (depends on T004, T005, T006)
- [X] T010 [US1] In `apps/api/tessera_api/routers/spaces.py`: change `CreateSpaceRequest` to `slug: str | None = None`, `sector: str = "General"`, add `parent_space_id: UUID | None = None`; add an `_invalid_parent`-reuse branch inside `create_space`'s exception handling. Rewrite `create_space` to build `repo`/`membership_repo`/`svc = SpaceHierarchyService(repo, membership_repo)` (mirroring `set_space_parent`) and call `created = await svc.create(actor_id=actor_id, company_id=company_id, name=body.name, sector=body.sector, slug=body.slug, parent_space_id=body.parent_space_id, default_language=body.default_language, retention_policy=body.retention_policy, confidence_threshold=body.confidence_threshold)` inside a `try`; on `PermissionError` raise `_forbidden()`; on `ValueError` as `exc`, if `str(exc) in ("cross_company", "depth_limit")` raise `_invalid_parent(str(exc))`, else raise `_invalid_name(str(exc))`. On success, keep the existing membership-grant (`membership_repo.add(SpaceMembership(space_id=created.id, user_id=actor_id, role=SpaceRole.ADMIN))`), and write **two** audit records in order: `action="space_created"`, `entity_type="space"`, `entity_id=created.id`, `metadata={"company_id": str(company_id), "parent_space_id": str(body.parent_space_id) if body.parent_space_id else None}`, then the existing `action="member_invited"` call (unchanged). Run T007 and confirm all cases now pass. (depends on T009, T007)
- [X] T011 [P] [US1] Create `apps/web/components/spaces/AddSpaceModal.tsx`, structurally mirroring `RenameSpaceModal.tsx`: props `{ parentSpaceId?: string; onClose: () => void; onCreated: (created: Space) => void }`; local state `name` (initialized to `""`), `error`, `loading`; a `handleCreate` async function that trims `name`, and if empty sets a local validation `error` without calling the API, otherwise calls `await api.post<{ space: Space }>("/v1/spaces", parentSpaceId ? { name: trimmed, parent_space_id: parentSpaceId } : { name: trimmed })`, then `onCreated(data.space); onClose();`, catching failures into `error` via the same `err instanceof Error ? err.message : "Failed to create space."` pattern as `RenameSpaceModal`; render a labeled text `<input>` (empty, autofocused), an inline `role="alert"` error message when `error` is set, and **Cancel**/**Create** buttons matching `RenameSpaceModal`'s styling.
- [X] T012 [US1] In `apps/web/app/spaces/page.tsx`: add `const [addingSpace, setAddingSpace] = useState(false);`; add an **"Add Space"** button next to the `<h1>Spaces</h1>` heading (wrap both in a `flex items-center justify-between` row) that sets `addingSpace(true)`; add a `handleSpaceCreated(created: Space)` function that appends `{ space: created, effective_role: "admin" as const, is_direct: true }` to `accesses` via `setAccesses((prev) => [...prev, ...])`; render `{addingSpace && <AddSpaceModal onClose={() => setAddingSpace(false)} onCreated={(created) => { handleSpaceCreated(created); setAddingSpace(false); }} />}`, importing `AddSpaceModal`.
- [X] T013 [US1] Run T008 and confirm all four cases now pass. Then run `cd packages/core && .venv/bin/python -m pytest tests/test_slug.py tests/test_space_hierarchy.py -v --no-cov`, `cd apps/api && .venv/bin/python -m pytest tests/unit/test_spaces_router.py -v --no-cov`, and `cd apps/web && npx vitest run tests/space-add.test.tsx tests/spaces.test.tsx`, confirming no regressions. (depends on T009, T010, T011, T012)

**Checkpoint**: MVP complete — any company member can create a top-level space from the Spaces page, end-to-end, with tenant isolation, audit logging, and a working create/cancel/validation UI. The backend also already supports nested creation (exercised only via direct service/API calls so far).

---

## Phase 4: User Story 2 - Create a nested sub-space from within a space (Priority: P2)

**Goal**: A user browsing a space's folder view can create a new space that is automatically nested under the space being viewed, via a second "Add Space" entry point.

**Independent Test**: Navigate into a space's folder view, click **Add Space**, submit a name, and verify the new space appears as a sub-space tile in that folder view immediately, and is confirmed nested under it via the top-level Spaces page.

> Note: `SpaceHierarchyService.create`'s parent-handling branch (T009) already implements admin-of-parent and depth-limit validation, generalized from the same logic `set_parent` uses. This phase adds the *second UI entry point* (new production code in `apps/web`) plus dedicated isolation-test coverage proving the already-existing backend branch is tenant-safe, per the pattern used for US2/US3 in `specs/049-space-rename/tasks.md`.

### Tests for User Story 2

- [X] T014 [P] [US2] Add a `test_create_space_rejects_cross_company_parent` case to `apps/api/tests/test_space_hierarchy_isolation.py` (mirroring `test_set_parent_rejects_cross_company_parent`'s `two_company_setup` fixture usage and `_bypass_onboarding` pattern): as a user in company A, `POST /v1/spaces` with `parent_space_id` set to a real space belonging to company B → expect `400`, and mock/assert that no space or membership row results (query `GET /v1/spaces` afterward and confirm no space named the attempted name exists). Run and confirm it passes immediately (T009/T010 already implement this rejection).
- [X] T015 [P] [US2] Extend `apps/web/tests/space-add.test.tsx` with: `it("shows an Add Space button in a space's folder view")` (mock `api.get` calls for `/v1/spaces`, `/v1/spaces/{id}/ancestors`, `/v1/documents?space_id=...`, render `SpaceFolderPage` for a given folder ID, assert the button exists — including when the folder is otherwise empty), `it("creates a sub-space nested under the folder being viewed")` (open **Add Space** from the folder view, submit a name, assert `mockApi.post` was called with `{ name: "...", parent_space_id: "<folderId>" }` and the new tile appears in that folder view immediately). Run and confirm both FAIL (the folder-view button doesn't exist yet).

### Implementation for User Story 2

- [X] T016 [US2] In `apps/web/app/spaces/[id]/page.tsx`: add the identical `addingSpace` state and `handleSpaceCreated` function as T012 (reusing the page's existing `handleSpaceUpdated`-adjacent pattern); add an **"Add Space"** button next to the folder's `<h1>{folder.name}</h1>` heading, rendered whenever `folder` is loaded — i.e., **outside** the `isEmpty` conditional, so it's visible even when the folder has no sub-folders or documents; render `{addingSpace && <AddSpaceModal parentSpaceId={folderId} onClose={() => setAddingSpace(false)} onCreated={(created) => { handleSpaceCreated(created); setAddingSpace(false); }} />}`, importing `AddSpaceModal`.
- [X] T017 [US2] Run T014 and T015 and confirm all now pass. Then run `cd apps/api && .venv/bin/python -m pytest tests/test_space_hierarchy_isolation.py -v --no-cov` and `cd apps/web && npx vitest run tests/space-add.test.tsx tests/space-folder-view.test.tsx`, confirming no regressions. (depends on T016)

**Checkpoint**: US1 and US2 both verified — spaces can be created at the top level and nested inside any space the actor administers, from both Spaces-menu surfaces.

---

## Phase 5: User Story 3 - Clear feedback when creation fails (Priority: P3)

**Goal**: A failed creation (validation, permission, or network error) shows a clear error, creates no space, and lets the user retry from either entry point.

**Independent Test**: Simulate a failed creation request from both the top-level Spaces page and a folder view, and confirm the UI shows an error, no tile appears, and resubmitting follows the same flow.

> Note: T011's `AddSpaceModal` already wraps `api.post` in a `try`/`catch` that sets a local `error` and does not call `onCreated` on failure, so no tile is ever inserted for a creation that didn't actually succeed. This phase is test-only, per the same convention used for US3 in `specs/049-space-rename/tasks.md`.

### Tests for User Story 3

- [X] T018 [US3] Extend `apps/web/tests/space-add.test.tsx` with `it("shows an error, adds no tile, and allows retry when creation fails")`: `mockApi.post.mockRejectedValueOnce(new Error("Server error — please try again."))`, open **Add Space**, submit a name, assert `screen.getByRole("alert")` shows the error message, no new tile appears, and the attempted name is still in the input for editing; then `mockApi.post.mockResolvedValueOnce({ space: { ...} })`, click **Create** again and assert the tile now appears. Also add `it("shows a 403 error from a folder view without creating a nested tile")` covering the non-admin-of-parent rejection path (`mockApi.post.mockRejectedValueOnce(new Error("Access denied"))` from the folder-view entry point). Run and confirm both pass (no new production code expected — if either fails, fix T011, not the test).

### Implementation for User Story 3

*No new production code — T011's existing error-handling already satisfies this story for both entry points.*

**Checkpoint**: All three user stories independently verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Meet Constitution Principle V (Ruff + Black) and confirm the full suite and the manual quickstart both pass.

- [X] T019 [P] Run Ruff on all modified/added Python files: `cd packages/core && .venv/bin/ruff check tessera_core/services/slug.py tessera_core/services/space_hierarchy.py tessera_core/ports/repositories/space.py tests/test_slug.py tests/test_space_hierarchy.py` and `cd apps/api && .venv/bin/ruff check tessera_api/adapters/repositories/space.py tessera_api/routers/spaces.py tests/unit/test_spaces_router.py tests/test_space_hierarchy_isolation.py`
- [X] T020 [P] Run Black on the same files: `cd packages/core && .venv/bin/black tessera_core/services/slug.py tessera_core/services/space_hierarchy.py tessera_core/ports/repositories/space.py tests/test_slug.py tests/test_space_hierarchy.py` and `cd apps/api && .venv/bin/black tessera_api/adapters/repositories/space.py tessera_api/routers/spaces.py tests/unit/test_spaces_router.py tests/test_space_hierarchy_isolation.py`
- [X] T021 Run the full backend suite to confirm no regressions: `cd packages/core && .venv/bin/python -m pytest -v --no-cov` and `cd apps/api && .venv/bin/python -m pytest tests/unit tests/test_space_hierarchy_isolation.py -v --no-cov`
- [X] T022 Run the full frontend suite: `cd apps/web && npx vitest run` and confirm no regressions in `spaces.test.tsx`, `space-drag-drop.test.tsx`, `space-folder-view.test.tsx`, `space-rename.test.tsx`
- [X] T023 Walk through `specs/051-add-space/quickstart.md` Scenarios 1-9 against a local `make dev` stack (top-level create, empty-name rejection, cancel, duplicate names, nested create, non-admin-of-parent 403, depth limit, cross-tenant parent, admin-console backward compatibility)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user story tasks (creation can't derive a slug without T004/T005).
- **User Story 1 (Phase 3)**: Depends on Foundational. Delivers the full stack (domain service including its nested-creation branch, endpoint, modal, top-level page wiring) — this is the MVP.
- **User Story 2 (Phase 4)**: Depends on US1's T009/T010 (the parent-handling branch already exists) and T011 (`AddSpaceModal` already accepts `parentSpaceId`) — adds the folder-view button and isolation-test coverage.
- **User Story 3 (Phase 5)**: Depends on US1's T011 existing — test-only.
- **Polish (Phase 6)**: Depends on Phases 3-5 being complete.

### User Story Dependencies

- **User Story 1 (P1)**: No dependency on other stories — the MVP.
- **User Story 2 (P2)**: Builds on US1's `SpaceHierarchyService.create` parent branch (T009) and `AddSpaceModal`'s `parentSpaceId` prop (T011) — adds one new page wiring task (T016) and isolation tests.
- **User Story 3 (P3)**: Builds on US1's `AddSpaceModal` error handling (T011) — proves it, adds no new production code.

### Within Each User Story

- Tests are written and confirmed failing before implementation in US1 (true TDD, since T009-T012 are new production code).
- US2's tests (T014/T015) are written after T009/T010/T011 exist; T014 (isolation) is expected to pass immediately, while T015 (folder-view button) is expected to FAIL until T016 lands, since the button itself is new.
- US3's test (T018) is written after T011 exists and is expected to pass immediately.

### Parallel Opportunities

- T002, T003 (Foundational) touch different files/packages and can run in parallel; T005 depends on T003 but not T002/T004.
- T006, T007, T008 (US1 tests) touch three different files (`packages/core`, `apps/api`, `apps/web`) and can be written in parallel.
- T011 (frontend modal) can be written in parallel with T009/T010 (backend) since the modal only depends on the endpoint's *contract* (already fixed in `contracts/create-space-endpoint.md`), not its implementation.
- T014 and T015 (US2 tests) touch different files and can run in parallel.
- T019 and T020 (Ruff/Black) are non-conflicting tooling passes over the same file set and can run back-to-back or in parallel processes.

---

## Parallel Example: User Story 1 tests

```bash
# Launch all three US1 test-writing tasks together (different files, no shared state):
Task: "Add TestCreateValidations to packages/core/tests/test_space_hierarchy.py"
Task: "Update/add create-endpoint tests in apps/api/tests/unit/test_spaces_router.py"
Task: "Create apps/web/tests/space-add.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (slug generation).
3. Complete Phase 3: User Story 1 (T006-T008 failing tests → T009-T012 implementation → T013 green).
4. **STOP and VALIDATE**: Any company member can create a top-level space end-to-end from the Spaces page, with tenant isolation, audit logging, and full admin access granted immediately. This alone satisfies the feature's core request ("create add space feature in spaces page").

### Incremental Delivery

1. Setup + Foundational → names can be turned into unique slugs.
2. US1 → top-level creation ships as the MVP (backend already supports nesting internally).
3. US2 → the folder-view entry point exposes nested creation, with dedicated isolation coverage.
4. US3 → the failure-feedback guarantee is explicitly proven for both entry points.
5. Polish → lint/format/full-suite/quickstart pass.

### Notes

- [P] tasks touch different files and have no shared state.
- Commit after each checkpoint (end of Phase 2, Phase 3, Phase 4, Phase 5, Phase 6), not after every individual task.
- No database migration is required anywhere in this feature — `spaces.slug` and `spaces.sector` already exist as non-null columns that already accept any string value.
