---

description: "Task list for Spaces as Drive-Style Folders (UI)"
---

# Tasks: Spaces as Drive-Style Folders (UI)

**Input**: Design documents from `/specs/044-spaces-folder-navigation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/reused-endpoints.md, quickstart.md

**Tests**: Included and REQUIRED — `plan.md`'s Constitution Check commits this feature to Test-Driven Development (Constitution Principle IV): Vitest tests for each user story are written first and must fail before the corresponding implementation exists.

**Organization**: Tasks are grouped by user story (from `spec.md`) to enable independent implementation and testing of each story. This is a frontend-only feature confined to `apps/web` — no `apps/api` or database changes (see `research.md` and `contracts/reused-endpoints.md`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task includes an exact file path

## Path Conventions

All paths are under `apps/web/` (existing Next.js App Router frontend). No backend paths are touched by this feature.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Small groundwork shared by every later phase. No new dependencies are introduced (research.md §1 — native HTML5 Drag and Drop API, no new package).

- [X] T001 [P] Promote the `Ancestor` interface currently declared locally in `apps/web/components/spaces/SpaceBreadcrumb.tsx` into `apps/web/lib/types.ts`, and update `SpaceBreadcrumb.tsx` to import it from there (data-model.md "Ancestor")

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared plumbing that every user story phase builds on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] Implement `topLevelSpaces(accesses: SpaceAccess[]): SpaceAccess[]` and `directChildren(accesses: SpaceAccess[], parentId: string): SpaceAccess[]` pure helpers in `apps/web/lib/spaces.ts`, applying the existing root-detection rule from `SpaceHierarchyView.buildTree` (a space is top-level if `parent_space_id` is null OR its parent is absent from the accessible set) — see `data-model.md` derivation rules and `research.md` §3
- [X] T003 [P] Create `apps/web/app/spaces/[id]/page.tsx` route skeleton: on mount, fetch `GET /v1/spaces` (full accessible list) and `GET /v1/spaces/{id}/ancestors`, resolve the current folder from the flat list by the route's `id` param, and render the existing loading/error-state pattern from `apps/web/app/spaces/page.tsx` — no folder-contents rendering yet (added in US1/US2)

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Browse spaces by drilling into folders (Priority: P1) 🎯 MVP

**Goal**: Replace the flat, fully-expanded, indented space list with a top-level grid of folder tiles; opening a tile drills into that space's direct sub-folders with a clickable breadcrumb trail; direct URLs deep-link into a folder.

**Independent Test**: Load `/spaces`, confirm only top-level spaces render as tiles; open a folder with sub-folders and confirm the view narrows to just its direct children with a correct breadcrumb; click the breadcrumb to go back up; load a folder's URL directly and confirm it opens straight into that folder's view.

### Tests for User Story 1 ⚠️

> Write these tests FIRST, run them, and confirm they FAIL before implementing anything below

- [X] T004 [P] [US1] Extend `apps/web/tests/spaces.test.tsx`: add a fixture pair (a space with a child space) and assert the top-level grid on `/spaces` renders only the parent, never the child
- [X] T005 [P] [US1] Create `apps/web/tests/space-folder-view.test.tsx`: tests for opening a folder tile updating the view to that folder's direct sub-folders only, the breadcrumb reading `Root › {folder name}`, clicking a breadcrumb segment returning to that ancestor, and loading `/spaces/{id}` directly rendering that folder's view with the correct breadcrumb (FR-002, FR-005, FR-006, FR-009)

### Implementation for User Story 1

- [X] T006 [P] [US1] Create `apps/web/components/spaces/FolderTile.tsx`: a grid tile with a folder icon, space name, sector, role badge (reuse `RoleBadge`), and a Members link, that navigates to `/spaces/{id}` on click/open (FR-002, FR-015, FR-016)
- [X] T007 [US1] Create `apps/web/components/spaces/FolderGrid.tsx` rendering a grid of `FolderTile`s for a given `SpaceAccess[]` (depends on T006)
- [X] T008 [US1] Update `apps/web/app/spaces/page.tsx` to use `topLevelSpaces()` (T002) and `FolderGrid` (T007) in place of `SpaceHierarchyView`, preserving the existing loading/error/empty-state handling (FR-001, FR-008)
- [X] T009 [US1] Update `apps/web/app/spaces/[id]/page.tsx` (T003 skeleton) to use `directChildren()` (T002) and `FolderGrid` (T007) to render the opened folder's direct sub-folders (FR-002)
- [X] T010 [US1] Extend `apps/web/components/spaces/SpaceBreadcrumb.tsx` to render a leading "Root" crumb linking to `/spaces` plus the ancestor chain as clickable links to `/spaces/{ancestorId}`, and mount it in `apps/web/app/spaces/[id]/page.tsx` (FR-005, FR-006)
- [X] T011 [US1] Delete `apps/web/components/spaces/SpaceHierarchyView.tsx`, `apps/web/components/spaces/SpaceCard.tsx`, and `apps/web/tests/space-card.test.tsx` — fully superseded by `FolderTile`/`FolderGrid` with no remaining references (confirmed via repo-wide search before deleting)

**Checkpoint**: User Story 1 is fully functional and independently testable — drill-down navigation and breadcrumbs work end-to-end.

---

## Phase 4: User Story 2 - See sub-folders and documents together inside a folder (Priority: P2)

**Goal**: An opened folder shows its direct sub-folders and its directly-assigned documents together in one grid, visually distinguishable, matching Google Drive's mixed folder+file listing.

**Independent Test**: Open a folder with both sub-folders and documents and confirm all items render together with distinguishable icons; open folder variants with only one category or neither and confirm correct rendering (including the empty-state); open a document tile and confirm it navigates to that document.

### Tests for User Story 2 ⚠️

> Write these tests FIRST, run them, and confirm they FAIL before implementing anything below

- [X] T012 [P] [US2] Extend `apps/web/tests/space-folder-view.test.tsx`: tests for a folder with sub-folders + documents rendering both together, a folder with only sub-folders, a folder with only documents, and a folder with neither rendering the empty-state message (FR-003, FR-004, FR-007)
- [X] T013 [P] [US2] Extend `apps/web/tests/space-folder-view.test.tsx`: test that clicking a document tile links to `/documents/{id}` (User Story 2, Acceptance Scenario 4)

### Implementation for User Story 2

- [X] T014 [P] [US2] Create `apps/web/components/spaces/DocumentTile.tsx`: a card with a document icon, title, state badge, and a link to `/documents/{id}`, visually distinct from `FolderTile` (FR-004)
- [X] T015 [US2] Extend `apps/web/components/spaces/FolderGrid.tsx` to accept an optional `documents: Document[]` prop and render `DocumentTile`s alongside `FolderTile`s in the same grid (depends on T014; FR-003)
- [X] T016 [US2] Update `apps/web/app/spaces/[id]/page.tsx` to fetch `GET /v1/documents?space_id={id}` for the opened folder and pass the result into `FolderGrid` (root view passes no documents, per `data-model.md` derivation rules)
- [X] T017 [US2] Add the empty-state message in `apps/web/app/spaces/[id]/page.tsx` for when the opened folder has zero sub-folders and zero documents (FR-007)

**Checkpoint**: User Stories 1 AND 2 both work independently — folders show mixed contents.

---

## Phase 5: User Story 3 - Reorganize the hierarchy by dragging folders (Priority: P3)

**Goal**: A user with hierarchy-management permission can drag a folder tile onto another folder tile or a breadcrumb crumb to reparent it, with the existing explicit "Set parent" action kept as a non-drag fallback.

**Independent Test**: Drag a folder tile onto another folder tile and confirm the parent updates and persists; drag onto self/a descendant and confirm rejection with clear feedback and no change; attempt a drag without permission and confirm rejection; confirm the non-drag "Set parent" action still works for users who can't drag.

### Tests for User Story 3 ⚠️

> Write these tests FIRST, run them, and confirm they FAIL before implementing anything below

- [X] T018 [P] [US3] Create `apps/web/tests/space-drag-drop.test.tsx`: test that dragging a `FolderTile` and dropping it on another `FolderTile` calls `PATCH /v1/spaces/{id}/parent` with the target id and the view reflects the new parent immediately (FR-010, FR-012)
- [X] T019 [P] [US3] Extend `apps/web/tests/space-drag-drop.test.tsx`: tests that dropping a folder onto itself or a descendant is rejected with a clear message and no API call/hierarchy change, and that a drop attempted without admin `effective_role` is rejected (drag not started, or drop fails with a permission message) leaving the hierarchy unchanged (FR-011, FR-013)
- [X] T020 [P] [US3] Extend `apps/web/tests/space-drag-drop.test.tsx`: test that the existing `SetParentModal` trigger remains present and functional on a `FolderTile` independent of the drag gesture (FR-014)

### Implementation for User Story 3

- [X] T021 [US3] Add native HTML5 drag attributes/handlers (`draggable`, `onDragStart`, `onDragOver`, `onDrop`) to `apps/web/components/spaces/FolderTile.tsx`, enabled only when the tile's `effective_role` is admin (research.md §1; FR-010, FR-013)
- [X] T022 [US3] Implement a shared reparent handler in `apps/web/lib/spaces.ts` that calls `PATCH /v1/spaces/{id}/parent` (drop on a folder tile) or `DELETE /v1/spaces/{id}/parent` (drop on the "Root" crumb) per `contracts/reused-endpoints.md`, reused by both `FolderGrid.tsx` and `SpaceBreadcrumb.tsx`
- [X] T023 [US3] Make each crumb rendered by `apps/web/components/spaces/SpaceBreadcrumb.tsx` (including "Root", added in T010) a valid drop target invoking the T022 handler (research.md §5; FR-010)
- [X] T024 [US3] Wire the T022 handler's success/error result into the UI: on success, refresh the affected folder's contents in place (FR-012); on `invalid_parent` (`self_parent`/`cycle`/`cross_company`/`depth_limit`) or `403 forbidden`, show a clear user-facing message and leave the hierarchy unchanged (FR-011, FR-013)
- [X] T025 [US3] Confirm the `SetParentModal` trigger from `apps/web/components/spaces/SetParentModal.tsx` remains reachable from `FolderTile.tsx` alongside the new drag handle, satisfying the non-drag fallback (FR-014)

**Checkpoint**: All three user stories are independently functional — this is the full feature.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T026 [P] Run `quickstart.md` scenarios 1-3 manually against a local `make web` + `make api` and confirm each expected outcome
- [X] T027 [P] Search the repository for any remaining references to `SpaceHierarchyView` or the old `SpaceCard` (docs, comments, other components) left over after T011's deletion, and update or remove them
- [X] T028 Run the full `apps/web` Vitest suite (`npx vitest run` from `apps/web/`) and confirm all new/extended tests pass with no regressions in existing suites (`documents.test.tsx`, `members.test.tsx`, etc.)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001) only for `SpaceBreadcrumb`'s import path; T002/T003 can start immediately regardless — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (T002, T003) completion
- **User Story 2 (Phase 4)**: Depends on User Story 1 (`FolderGrid`, `FolderTile`, and `app/spaces/[id]/page.tsx` must exist to extend)
- **User Story 3 (Phase 5)**: Depends on User Story 1 (`FolderTile`, `SpaceBreadcrumb`'s Root crumb) — does not require User Story 2
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories — this is the foundation the other two extend
- **User Story 2 (P2)**: Extends US1's `FolderGrid`/`[id]/page.tsx`; not independently deployable before US1 exists, but independently *testable* once US1 lands
- **User Story 3 (P3)**: Extends US1's `FolderTile`/`SpaceBreadcrumb`; independent of US2 — could be built in parallel with US2 by a second developer once US1 is done

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Tiles/components before the pages that assemble them
- Story complete and checkpointed before moving to the next priority

### Parallel Opportunities

- T001 (Setup) can run alongside T002/T003 (Foundational)
- T004 and T005 (US1 tests) can run in parallel — different files
- T006 (US1: FolderTile) has no dependency on T004/T005 landing first as long as tests are written and failing; can be built in parallel with T005 once T004 is committed
- T012, T013 (US2 tests) can run in parallel
- T014 (US2: DocumentTile) can be built in parallel with the US2 tests
- T018, T019, T020 (US3 tests) can run in parallel
- Once US1 (Phase 3) is complete, US2 (Phase 4) and US3 (Phase 5) can be built in parallel by different developers — they touch different files except both extending `apps/web/app/spaces/[id]/page.tsx` (T016 vs T024), which should be sequenced or carefully merged if done concurrently

---

## Parallel Example: User Story 1

```bash
# Launch both US1 tests together:
Task: "Extend apps/web/tests/spaces.test.tsx with top-level-only fixture"
Task: "Create apps/web/tests/space-folder-view.test.tsx with drill-down/breadcrumb/deep-link tests"

# FolderTile can be built alongside the tests:
Task: "Create apps/web/components/spaces/FolderTile.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002-T003)
3. Complete Phase 3: User Story 1 (T004-T011)
4. **STOP and VALIDATE**: Run `quickstart.md` Scenario 1 — top-level grid, drill-down, breadcrumb, deep link
5. Demo if ready — this alone already replaces the unreadable flat indented list with real navigation

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. User Story 1 → validate via `quickstart.md` Scenario 1 → demo (MVP)
3. User Story 2 → validate via `quickstart.md` Scenario 2 → demo
4. User Story 3 → validate via `quickstart.md` Scenario 3 → demo
5. Polish (T026-T028) → full regression pass

### Parallel Team Strategy

1. One developer completes Setup + Foundational + User Story 1 (the shared foundation)
2. Once US1 lands, a second developer can pick up User Story 3 (drag-and-drop) while the first continues to User Story 2 (mixed contents) — they touch different files apart from `app/spaces/[id]/page.tsx`, which should be coordinated

---

## Notes

- No backend/database tasks appear in this list — every endpoint used already exists and is already tenant-scoped and authorization-checked (see `contracts/reused-endpoints.md`); this is deliberate, not an oversight
- [P] tasks touch different files with no unmet dependency
- Verify each test fails before writing its implementation (Constitution Principle IV)
- Commit after each task or logical group
- Stop at either checkpoint (end of Phase 3 or Phase 4) to validate a story independently before continuing
