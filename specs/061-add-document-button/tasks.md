# Tasks: Add Document Button in Space

**Input**: Design documents from `/specs/061-add-document-button/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-and-api.md, quickstart.md

**Tests**: Included — the constitution (Principle IV: Test-Driven Development) and plan.md require the new Vitest suite to be written first and fail before implementation.

**Organization**: Tasks are grouped by user story. US1 (create from space page) is the MVP; US2 (permission-aware visibility) layers role gating on top and is independently testable.

**Scope reminder**: Frontend-only. `apps/api` and `packages/core` are untouched; all backend enforcement already exists.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in descriptions

## Path Conventions

Web app monorepo — all changes under `apps/web/`:

- Page: `apps/web/app/spaces/[id]/page.tsx`
- Shared component: `apps/web/components/documents/AddDocumentModal.tsx`
- Tests: `apps/web/tests/space-add-document.test.tsx` (new), `apps/web/tests/documents.test.tsx` (regression guard, unchanged)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish a green baseline so regressions introduced by this feature are unambiguous.

- [X] T001 Verify web workspace baseline: in `apps/web`, run `npx vitest run tests/documents.test.tsx tests/space-add.test.tsx` and confirm both existing suites pass before any change (they are the FR-007 regression guards and the test-pattern references)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

*No foundational tasks required.* The API (`POST /v1/documents`, `GET /v1/spaces` with `effective_role`), the `AddDocumentModal` component, `mapSpaceAccesses`, and all types (`Document`, `Space`, `SpaceRole`, `SpaceAccess`) already exist. Both user stories build directly on them.

**Checkpoint**: Baseline green — user story implementation can begin.

---

## Phase 3: User Story 1 - Create a document from within a space (Priority: P1) 🎯 MVP

**Goal**: An "Add Document" button on the space folder page opens the existing creation dialog with the current space preselected; on save, the new document appears in the grid immediately (replacing the empty state if needed), without a reload.

**Independent Test**: Open a space page, click "Add Document", enter a title, save — the document appears in that space's grid with no reload or navigation (quickstart US1 steps 1–7).

### Tests for User Story 1 (write first, confirm they FAIL) ⚠️

- [X] T002 [US1] Create `apps/web/tests/space-add-document.test.tsx` with the test scaffold: mock `@/lib/api` following the pattern in `apps/web/tests/space-add.test.tsx` and `apps/web/tests/documents.test.tsx`; fixtures for `GET /v1/spaces` (accesses including the current folder with `effective_role: "editor"`) and `GET /v1/documents?space_id=` (empty and non-empty variants); render helper for `app/spaces/[id]/page.tsx`
- [X] T003 [US1] Add US1 acceptance tests to `apps/web/tests/space-add-document.test.tsx`: (a) "Add Document" button renders next to "Add Space" for an editor (US1-AC1/FR-001); (b) clicking it opens the dialog with the current space preselected in the destination select (US1-AC1/FR-002); (c) entering a title and saving calls `POST /v1/documents` with `space_id` = current folder and appends the created document to the grid without reload (US1-AC2/FR-004); (d) creating from an empty space replaces the empty-state message with the grid (US1-AC5); (e) cancel/dismiss creates nothing and leaves the page unchanged (US1-AC3); (f) submitting without a title shows validation and creates nothing (US1-AC4); (g) changing the destination to a different space in the dialog creates the document but does NOT add it to the current grid (edge case/SC-002)
- [X] T004 [US1] Run `npx vitest run tests/space-add-document.test.tsx` in `apps/web` and confirm the new tests FAIL (red) before implementation

### Implementation for User Story 1

- [X] T005 [P] [US1] Add optional `initialSpaceId?: string` prop to `apps/web/components/documents/AddDocumentModal.tsx` per contracts/ui-and-api.md: the reset effect initializes the destination `spaceId` to `initialSpaceId ?? ""` when the dialog opens/closes, all other fields reset as today; callers omitting the prop (Documents page) observe zero behavior change (FR-007); the AI-assist role probe fires for the preselected space on open (FR-003)
- [X] T006 [US1] Add the "Add Document" button and modal wiring to `apps/web/app/spaces/[id]/page.tsx`: `addingDocument` boolean state; button rendered next to the existing "Add Space" action (design system: `bg-indigo-600`, hover `indigo-700`); on click open `AddDocumentModal` with `open={addingDocument}`, `initialSpaceId={folderId}`, and `spaces={accesses.map(a => a.space)}` (FR-001, FR-002; role gating comes in US2)
- [X] T007 [US1] Implement the `onCreated` handler in `apps/web/app/spaces/[id]/page.tsx`: append the created document to the `documents` state only if `document.space_id === folderId` (destination-change edge case), then close the modal; the existing `isEmpty` derivation swaps the empty state for the grid automatically (FR-004, SC-003)
- [X] T008 [US1] Run `npx vitest run tests/space-add-document.test.tsx tests/documents.test.tsx tests/space-add.test.tsx` in `apps/web`: US1 tests pass (green) and the existing suites still pass, proving the global Documents entry point is unchanged (FR-007)

**Checkpoint**: US1 fully functional — an editor can create a document from a space page and see it in the grid immediately. (Note: until US2, the button is visible to viewers too; server-side enforcement still blocks their saves.)

---

## Phase 4: User Story 2 - Permission-aware visibility (Priority: P2)

**Goal**: The "Add Document" button is shown only to users whose `effective_role` in the space is `editor` or `admin`; a rejected save (stale-page case) surfaces a clear error in the dialog without losing entered content.

**Independent Test**: View the same space page as an editor (button visible) and as a viewer (button absent) — quickstart US2 steps 1–3.

### Tests for User Story 2 (write first, confirm they FAIL) ⚠️

- [X] T009 [US2] Add US2 tests to `apps/web/tests/space-add-document.test.tsx`: (a) button absent when the current folder's `effective_role` is `"viewer"` (US2-AC2/FR-005/SC-004); (b) button visible for `"editor"` and for `"admin"` (US2-AC1); (c) stale-page rejection — `POST /v1/documents` mock rejects with a 403-style API error: the dialog stays open, shows the error message, the entered title/content are preserved, and no document is added to the grid (US2-AC3/FR-006)
- [X] T010 [US2] Run `npx vitest run tests/space-add-document.test.tsx` in `apps/web` and confirm the viewer-gating test FAILS (red) before implementation (the 403 test may already pass via the modal's existing `apiError` handling — record which) — *result: viewer-gating test failed red as required; the 403 stale-page test already passed via the modal's existing `apiError` handling*

### Implementation for User Story 2

- [X] T011 [US2] Add role gating to `apps/web/app/spaces/[id]/page.tsx`: derive `currentRole = accesses.find(a => a.space.id === folderId)?.effective_role` and `canAddDocument = currentRole === "editor" || currentRole === "admin"` (data-model.md); render the "Add Document" button only when `canAddDocument` is true (FR-001, FR-005) — no new API request
- [X] T012 [US2] Verify the error surface in `apps/web/components/documents/AddDocumentModal.tsx`: confirm the existing `apiError` display and submit-in-flight disabling satisfy US2-AC3 and FR-006 (dialog stays open, content preserved, double-click safe) — expected to require no code change; fix only if T009(c) exposes a gap — *verified: no code change needed, T009(c) passed against existing handling*
- [X] T013 [US2] Run `npx vitest run tests/space-add-document.test.tsx` in `apps/web` and confirm the full feature suite passes (green)

**Checkpoint**: Both stories complete — viewers never see the action; editors/admins get the full flow with server-enforced defense in depth.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates and end-to-end validation across both stories.

- [X] T014 Run the full web test suite in `apps/web` (`npx vitest run`) and confirm no regressions anywhere in the app — *370/370 pass; `document-detail-modernized.test.tsx` is flaky under parallel runs (untouched by this feature, passes in isolation and on re-run)*
- [X] T015 [P] Run quality gates in `apps/web`: `npx eslint .` (or `npm run lint`) and `npx tsc --noEmit` — zero errors on the changed files (constitution V) — *`tsc --noEmit` clean; ESLint has no config/dependency/script in `apps/web` (pre-existing), so typecheck is the operative gate*
- [ ] T016 Execute the manual validation scenarios in `specs/061-add-document-button/quickstart.md` against a running stack (US1 steps 1–7, US2 steps 1–3, edge cases) and confirm the success-criteria mapping (SC-001…SC-004)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Empty — no blockers beyond Setup
- **User Story 1 (Phase 3)**: Depends on T001 (green baseline)
- **User Story 2 (Phase 4)**: Depends on US1's button existing (T006) to gate it; tests extend the same file created in T002
- **Polish (Phase 5)**: Depends on Phases 3–4 complete

### User Story Dependencies

- **US1 (P1)**: Independent — deliverable as MVP on its own
- **US2 (P2)**: Builds on US1's button (T006) and test scaffold (T002); its acceptance criteria are still independently testable (viewer vs. editor rendering of the same page)

### Within Each User Story

- Tests written and confirmed failing (T004, T010) before implementation
- Component prop (T005) and page wiring (T006–T007) before the green run (T008)
- Gating (T011) before the final green run (T013)

### Parallel Opportunities

- **T005 ∥ T006**: different files (`AddDocumentModal.tsx` vs. `page.tsx`) with no mutual dependency — the prop change and the page wiring can be done simultaneously once T004 is red
- **T015** can run in parallel with T016 (lint/typecheck vs. manual validation)
- Everything else is sequential: both stories share `page.tsx` and the single test file, so cross-story parallelism is intentionally avoided

## Parallel Example: User Story 1

```bash
# After T004 (tests red), launch the two implementation files together:
Task: "Add optional initialSpaceId prop in apps/web/components/documents/AddDocumentModal.tsx"   # T005
Task: "Add Add Document button + modal wiring in apps/web/app/spaces/[id]/page.tsx"              # T006
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Phase 2 is empty — proceed directly
3. Complete Phase 3: US1 (T002–T008)
4. **STOP and VALIDATE**: run the new suite + regression suites; manually create a document from a space page
5. US1 alone is shippable for permitted users (server-side enforcement already protects viewers; only the UI gating polish is missing)

### Incremental Delivery

1. T001 → baseline green
2. US1 (T002–T008) → test independently → MVP: create-from-space works end to end
3. US2 (T009–T013) → test independently → viewers no longer see the button; stale-page errors surface cleanly
4. Polish (T014–T016) → full suite, lint/typecheck, quickstart manual pass

---

## Notes

- [P] tasks = different files, no dependencies
- Verify tests fail before implementing (T004, T010) — constitution Principle IV
- No backend, schema, or API contract changes anywhere in this feature (plan.md constraints)
- `apps/web/tests/documents.test.tsx` must remain untouched and passing at every checkpoint (FR-007)
- Commit after each task or logical group
