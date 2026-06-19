# Tasks: Add Document — Frontend

**Input**: Design documents from `specs/009-add-document-frontend/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared state dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- TDD order: write failing test → implement → confirm test passes

---

## Phase 1: Setup

**Purpose**: Confirm scaffolding is in place; no new dependencies or infrastructure required.

- [x] T001 Verify `Document` and `Space` types in `apps/web/lib/types.ts` fully cover `POST /v1/documents` response shape (title, space_id, language, confidentiality, state, id fields)
- [x] T002 Create directory `apps/web/components/documents/` (will hold `AddDocumentModal.tsx`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared test infrastructure and baseline assertion that the modal entry point (`AddDocumentModal`) can be imported. These tasks establish the test scaffold before any user story is implemented.

**⚠️ CRITICAL**: Complete before starting any user story phase.

- [x] T003 Add `describe("Add Document modal", ...)` block and import scaffolding to `apps/web/tests/documents.test.tsx`
- [x] T004 Write failing test — "Add Document button is visible on Documents page" in `apps/web/tests/documents.test.tsx` (run; confirm it fails before T007)

**Checkpoint**: Test infra ready; button-visibility test is red.

---

## Phase 3: User Story 1 — Create a New Document (Priority: P1) 🎯 MVP

**Goal**: User clicks "Add Document", fills in the modal form, submits, and the new document row appears in the list without a page reload.

**Independent Test**: Render `DocumentsPage`, click "Add Document", submit a valid form, assert new document row appears in list — delivers complete creation workflow.

### Tests for User Story 1 (TDD-first — write before implementation)

- [x] T005 [P] [US1] Write failing test — modal opens on "Add Document" click and renders a dialog in `apps/web/tests/documents.test.tsx`
- [x] T006 [P] [US1] Write failing test — successful form fill and submit calls `POST /v1/documents` and new document row appears in `apps/web/tests/documents.test.tsx`
- [x] T007 [US1] Run test suite; confirm T004, T005, T006 all fail (red)

### Implementation for User Story 1

- [x] T008 [US1] Create `apps/web/components/documents/AddDocumentModal.tsx` — component skeleton accepting props `{ open, spaces, onClose, onCreated }` per `specs/009-add-document-frontend/contracts/AddDocumentModal.ts`
- [x] T009 [US1] Implement modal overlay structure in `AddDocumentModal.tsx`: full-screen backdrop `div` + centered panel `div`; `role="dialog"`, `aria-modal="true"`; close on backdrop click and `Escape` key (`onKeyDown` on the wrapper)
- [x] T010 [US1] Implement form fields in `AddDocumentModal.tsx`: title `<input>` (`autoFocus`), space `<select>` (renders `spaces` prop), language `<select>` (options: `pt-BR`, `en`; default `pt-BR`), confidentiality `<select>` (options: `internal`, `restricted`, `public`; default `internal`), content `<textarea>` (plain, no preview). Also renders "No spaces available" message and disables Save when `spaces.length === 0`.
- [x] T011 [US1] Implement submit handler in `AddDocumentModal.tsx`: calls `api.post<{ document: Document; version: DocumentVersion }>("/v1/documents", { space_id, title, language, confidentiality, content_markdown, tags: [], frontmatter: {} })`, then calls `onCreated(response.document)` and `onClose()`
- [x] T012 [US1] Add "Add Document" button and `showModal` state to `apps/web/app/documents/page.tsx`; render `<AddDocumentModal open={showModal} spaces={spaces} onClose={() => setShowModal(false)} onCreated={handleCreated} />`
- [x] T013 [US1] Implement `handleCreated` in `apps/web/app/documents/page.tsx`: prepend the new document to `documents` state only when `newDoc.space_id === selectedSpaceId` (or no filter active)
- [x] T014 [US1] Run tests; confirm T004, T005, T006 are green

**Checkpoint**: User Story 1 fully functional and independently testable. "Add Document" → fill → save → list updates.

---

## Phase 4: User Story 2 — Form Validation and Error Handling (Priority: P2)

**Goal**: Required-field validation prevents submission with blank title or no space selected; API errors surface as a banner inside the open modal.

**Independent Test**: Submit form with empty title → inline error shown, no network request. Submit with API mocked to error → banner appears, modal stays open.

### Tests for User Story 2 (TDD-first — write before implementation)

- [x] T015 [P] [US2] Write failing test — submitting with empty title shows inline validation error and does not call `api.post` in `apps/web/tests/documents.test.tsx`
- [x] T016 [P] [US2] Write failing test — submitting with no space selected shows inline validation error in `apps/web/tests/documents.test.tsx`
- [x] T017 [P] [US2] Write failing test — when `api.post` rejects, error banner appears at top of form and modal stays open in `apps/web/tests/documents.test.tsx`
- [x] T018 [US2] Run test suite; confirm T015, T016, T017 all fail (red)

### Implementation for User Story 2

- [x] T019 [US2] Add `errors` state object to `AddDocumentModal.tsx`; validate `title.trim()` non-empty and `spaceId` non-empty on submit; render inline error `<p>` below each field when invalid; skip API call if any error
- [x] T020 [US2] Add `apiError` state to `AddDocumentModal.tsx`; catch `api.post` rejection; set `apiError` with `err.message`; render error banner `<div>` at top of the form; keep modal open on error
- [x] T021 [US2] Add `submitting` boolean state to `AddDocumentModal.tsx`; disable Save button and show "Saving…" label while request is in flight
- [x] T022 [US2] Run tests; confirm T015, T016, T017 are green

**Checkpoint**: US1 + US2 both independently functional. Validation and error handling work.

---

## Phase 5: User Story 3 — Cancel / Dismiss Without Saving (Priority: P3)

**Goal**: "Cancel" button and Escape key dismiss the modal without saving; form resets to defaults on re-open.

**Independent Test**: Open modal, type in title, click Cancel → modal closes, document list unchanged, reopening shows empty form.

### Tests for User Story 3 (TDD-first — write before implementation)

- [x] T023 [P] [US3] Write failing test — clicking "Cancel" closes modal and does not call `api.post` in `apps/web/tests/documents.test.tsx`
- [x] T024 [P] [US3] Write failing test — form fields are reset to defaults when modal is re-opened after a cancel in `apps/web/tests/documents.test.tsx`
- [x] T025 [US3] Run test suite; confirm T023, T024 all fail (red)

### Implementation for User Story 3

- [x] T026 [US3] Add "Cancel" button to `AddDocumentModal.tsx` that calls `onClose()`; Escape key handler already present from T009 — verify it also calls `onClose()`
- [x] T027 [US3] Reset all form state (`title`, `spaceId`, `language`, `confidentiality`, `contentMarkdown`, `errors`, `apiError`) when `open` transitions from `true` to `false` in `AddDocumentModal.tsx` — use `useEffect([open])` to clear on close
- [x] T028 [US3] Run tests; confirm T023, T024 are green

**Checkpoint**: All three user stories independently functional and tested.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Accessibility, type safety, and final validation pass.

- [x] T029 [P] Confirm `aria-modal="true"`, `role="dialog"`, and `autoFocus` on title input are present in `apps/web/components/documents/AddDocumentModal.tsx`
- [x] T030 [P] Run TypeScript type-check across frontend: `cd apps/web && npx tsc --noEmit`; resolve any type errors
- [x] T031 Run full test suite: `npx vitest run`; confirm all tests pass (including pre-existing document browser and detail page tests) — **84/84 tests pass**
- [ ] T032 Manually validate quickstart.md scenarios S-1 through S-5 against running dev stack (`make dev`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1)**: Depends on Phase 2 — MVP deliverable
- **Phase 4 (US2)**: Depends on Phase 3 (US2 adds validation to the modal created in US1)
- **Phase 5 (US3)**: Depends on Phase 3 (US3 adds cancel behaviour to the same modal)
- **Phase 6 (Polish)**: Depends on Phases 3, 4, 5

### User Story Dependencies

- **US1 (P1)**: Core modal + button — foundational for US2 and US3
- **US2 (P2)**: Adds validation to the modal built in US1; depends on T008–T013
- **US3 (P3)**: Adds cancel/reset to the modal built in US1; can be developed in parallel with US2 (different modal state fields)

### Within Each Story

1. Write all failing tests first and confirm they fail
2. Implement until tests go green
3. Validate checkpoint before moving to next story

### Parallel Opportunities

- T005, T006 (US1 tests) can be written in parallel
- T015, T016, T017 (US2 tests) can be written in parallel
- T023, T024 (US3 tests) can be written in parallel
- T029, T030 (Polish) can run in parallel
- US2 and US3 implementation can proceed in parallel after US1 is complete (they modify the same file but different state fields — coordinate if pair-programming)

---

## Parallel Example: User Story 1

```bash
# Write all US1 tests together (before any implementation):
Task T005: "Write failing test — modal opens on click in documents.test.tsx"
Task T006: "Write failing test — successful submit adds document row in documents.test.tsx"

# Then implement in order (T008 → T009 → T010 → T011 → T012 → T013)
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (write button-visibility test)
3. Complete Phase 3: US1 — implement modal + page wiring
4. **STOP and VALIDATE**: All US1 tests green; manually open modal and create a document
5. Ship/demo if ready

### Incremental Delivery

1. Setup + Foundational → ready
2. US1 → "Add Document" works end-to-end → demo
3. US2 → Validation and error handling → demo
4. US3 → Cancel/reset → polish
5. Phase 6 → full QA pass → ship

---

## Notes

- `[P]` tasks operate on separate state variables or test blocks — safe to parallelize
- TDD order per constitution: failing test → implementation → green
- `AddDocumentModal.tsx` is modified across US1/US2/US3 — coordinate to avoid conflicts if working in parallel
- No new npm packages; no backend changes; no migrations
