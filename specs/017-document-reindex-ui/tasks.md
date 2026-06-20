---

description: "Task list for Document Reindex UI feature"
---

# Tasks: Document Reindex UI

**Input**: Design documents from `specs/017-document-reindex-ui/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/reindex-button.md ✅

**Tests**: Included per Constitution IV (TDD is non-negotiable). Write each test group first, confirm failure, then implement.

**Organization**: Tasks grouped by user story. All 4 user stories share one implementation file; test files differentiate the coverage.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[Story]**: Maps to user story from spec.md (US1–US4)

---

## Phase 1: Setup

No project initialization needed — existing Next.js app with all required dependencies (`useAuth`, `api.post`, Vitest).

**Checkpoint**: Ready to proceed immediately.

---

## Phase 2: Foundational

No foundational prerequisites — `useAuth()` hook, `api.post()`, `Document` type, and `AuthUser` type are all in place. The target file `apps/web/app/documents/[id]/page.tsx` exists.

**Checkpoint**: Proceed to user story implementation.

---

## Phase 3: User Story 1 — Owner Triggers Reindex (Priority: P1) 🎯 MVP

**Goal**: Document owner sees and can click a "Reindex" button on a published document, triggering reindexing with 3-second success auto-dismiss and inline error on failure.

**Independent Test**: Log in as document owner, open a published document — "Reindex" button is visible; clicking it shows "Reindexing…" then "Reindex queued" for 3 seconds, then resets.

### Tests for User Story 1 (TDD — write and confirm failure BEFORE T002)

- [x] T001 [US1] Write 4 failing tests in `apps/web/tests/documents.test.tsx` — new describe "Document detail page — Reindex button": (1) owner of published doc sees Reindex button, (2) clicking Reindex shows "Reindex queued" then re-enables after timer (use `vi.useFakeTimers` + `vi.runAllTimers`), (3) API error shows inline red message and re-enables button, (4) button is disabled while request is in-flight

### Implementation for User Story 1

- [x] T002 [US1] Add `useAuth` import from `@/lib/auth` and `useRef` import to `apps/web/app/documents/[id]/page.tsx`
- [x] T003 [US1] Add `reindexing`, `reindexMessage`, `reindexError` state fields and `reindexTimerRef` ref to `apps/web/app/documents/[id]/page.tsx`
- [x] T004 [US1] Implement `handleReindex` async function with timer ref (3-second auto-dismiss, re-enable button after success; immediate re-enable on error) in `apps/web/app/documents/[id]/page.tsx`
- [x] T005 [US1] Add `canReindex` visibility derivation (`document.state === "published" && (user?.id === document.owner_user_id || user?.isAdmin === true)`) in `apps/web/app/documents/[id]/page.tsx`
- [x] T006 [US1] Add Reindex button JSX to header actions area in `apps/web/app/documents/[id]/page.tsx`: conditional on `canReindex`, shows "Reindexing…" when `reindexing`, green "Reindex queued" message when `reindexMessage`, red error when `reindexError`

**Checkpoint**: US1 tests from T001 must now pass — `cd apps/web && npx vitest run tests/documents.test.tsx`

---

## Phase 4: User Story 2 — Admin Triggers Reindex on Any Document (Priority: P2)

**Goal**: An admin user sees the Reindex button on a published document they do not own and can trigger reindexing.

**Independent Test**: Log in as admin, open a published document owned by another user — "Reindex" button is visible.

### Tests for User Story 2 (TDD — write and confirm failure BEFORE T008)

- [x] T007 [P] [US2] Create `apps/web/tests/documents-reindex-admin.test.tsx` — mock `useAuth` with `isAdmin: true`, `id: "u99"`; test: admin sees Reindex button on published doc with `owner_user_id: "u1"` (different from admin id)

### Implementation for User Story 2

- [x] T008 [US2] Verify T007 admin test passes with no code change (already covered by `canReindex` in T005): `cd apps/web && npx vitest run tests/documents-reindex-admin.test.tsx`

**Checkpoint**: Admin test must pass. If it fails, review `canReindex` condition from T005.

---

## Phase 5: User Story 3 — Non-Owner, Non-Admin Cannot Reindex (Priority: P2)

**Goal**: A regular user who neither owns the document nor is an admin sees no Reindex button.

**Independent Test**: Log in as non-owner, open a published document — no Reindex button visible.

### Tests for User Story 3 (TDD — add to existing describe block)

- [x] T009 [US3] Add failing test to `apps/web/tests/documents.test.tsx` describe "Reindex button": non-owner (`owner_user_id: "u2"`, `user.id: "u1"`, `isAdmin: false`) does not see Reindex button

### Implementation for User Story 3

- [x] T010 [US3] Verify T009 test passes — covered by `canReindex` condition from T005 (no code change needed): `cd apps/web && npx vitest run tests/documents.test.tsx`

**Checkpoint**: T009 must pass. Both US1 and US3 owner/non-owner tests pass together.

---

## Phase 6: User Story 4 — Reindex Unavailable for Non-Published Documents (Priority: P3)

**Goal**: Even the document owner sees no Reindex button on ingested or archived documents.

**Independent Test**: Log in as document owner, open an ingested document — Reindex button is absent, Publish button is present.

### Tests for User Story 4 (TDD — add to existing describe block)

- [x] T011 [US4] Add failing test to `apps/web/tests/documents.test.tsx` describe "Reindex button": document owner does not see Reindex button when `state: "ingested"`

### Implementation for User Story 4

- [x] T012 [US4] Verify T011 test passes — covered by `canReindex` state guard from T005 (no code change needed): `cd apps/web && npx vitest run tests/documents.test.tsx`

**Checkpoint**: T011 must pass. All 4 user stories' tests now pass together.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T013 Run full test suite and confirm all tests pass (existing + new): `cd apps/web && npx vitest run --reporter=verbose`
- [x] T014 [P] TypeScript check — no type errors: `cd apps/web && npx tsc --noEmit`
- [ ] T015 Manual end-to-end validation per `specs/017-document-reindex-ui/quickstart.md` scenarios T001–T007 (start stack with `bash scripts/dev.sh`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1–2** (Setup/Foundational): No dependencies — skip directly
- **Phase 3 (US1)**: No dependencies — start here
- **Phase 4 (US2)**: Depends on Phase 3 implementation (T002–T006); test file T007 can be written in parallel with T001
- **Phase 5 (US3)**: Depends on Phase 3 implementation — verify only
- **Phase 6 (US4)**: Depends on Phase 3 implementation — verify only
- **Phase 7 (Polish)**: Depends on all prior phases complete

### User Story Dependencies

- **US1 (P1)**: Core story — all others depend on its implementation (T002–T006)
- **US2 (P2)**: Test only (T007); no code change; can be written in parallel with T001
- **US3 (P2)**: Test only (T009); sequential with T001 (same file)
- **US4 (P3)**: Test only (T011); sequential with T009 (same file)

### Within Each Story

- Tests written FIRST and confirmed to fail (Constitution IV)
- Implementation tasks T002–T006 are sequential (same file, each builds on previous)
- Verify tasks run after implementation

### Parallel Opportunities

- T001 (US1 tests) and T007 (US2 test file) can be written in parallel — different files
- T013 (full test run) and T014 (TypeScript check) can run in parallel

---

## Parallel Example: Writing Tests

```bash
# Developer A:
# Write US1 tests in apps/web/tests/documents.test.tsx
# T001: owner visibility, success, error, in-flight

# Developer B (simultaneous):
# Create apps/web/tests/documents-reindex-admin.test.tsx
# T007: admin visibility test
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Skip Phase 1–2 (nothing to do)
2. Complete Phase 3 (T001–T006) — delivers the owner reindex button with full UX
3. **STOP and VALIDATE**: run `npx vitest run` and manual quickstart T001/T005/T006
4. US2/US3/US4 are pure test additions — add at any time without risk

### Incremental Delivery

1. Phase 3 complete → Owner can reindex published docs (MVP)
2. Phase 4 complete → Admin coverage confirmed  
3. Phase 5–6 complete → Negative cases verified
4. Phase 7 complete → Full validation done

---

## Notes

- [P] tasks = different files, no blocking dependencies
- Tests T009 and T011 are added to `apps/web/tests/documents.test.tsx` — sequential with T001 (same file)
- Timer-based test (T001 item 2) requires `vi.useFakeTimers()` in `beforeEach` and `vi.runAllTimers()` to advance the 3-second window
- US2, US3, US4 have no implementation tasks — all covered by the `canReindex` condition from T005
- The existing Publish button and the new Reindex button are mutually exclusive by document state and will never appear simultaneously
