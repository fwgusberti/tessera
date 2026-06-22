---
description: "Task list for AI-First Interface with Doc Access"
---

# Tasks: AI-First Interface with Doc Access

**Input**: Design documents from `/specs/027-ai-first-doc-access/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/assistant-answer.md ✅

**Tests**: Included — constitution principle IV (TDD) is non-negotiable; plan.md confirms all changed code has companion tests written first.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to ([US1], [US2], [US3])
- Exact file paths included in every task description

---

## Phase 1: Setup

**Purpose**: Baseline verification — confirm existing suite is green before making changes.

No new project structure is required. Feature 027 modifies ~6 existing files with no DB migrations.

- [X] T001 Run frontend (`cd apps/web && npm test -- --run`) and backend (`cd apps/api && uv run pytest tests/ -v`) test suites to establish a passing baseline before any changes

**Checkpoint**: All pre-existing tests pass — ready to begin implementation.

---

## Phase 2: Foundational (Blocking Prerequisite for US3)

**Purpose**: Extend the Citation DTO so the backend surfaces `document_id` and the frontend type system reflects it. US3 (MessageBubble citation links) cannot be implemented without these changes.

**⚠️ CRITICAL**: US3 implementation (Phase 5) MUST NOT start until T003 and T004 are complete.

- [X] T002 Write failing unit tests asserting `build_citation` output contains `document_id` equal to `str(chunk_row["document_id"])` in `apps/api/tests/unit/test_citations.py`
- [X] T003 Add `"document_id": str(chunk_row["document_id"])` to the dict returned by `build_citation` in `apps/api/tessera_api/rag/citations.py` (run T002 tests — they must pass after this change)
- [X] T004 [P] Add `document_id: string` field to the `Citation` interface in `apps/web/lib/types.ts` (position between `chunk_id` and `document_version_id` per data-model.md)

**Checkpoint**: `test_citations.py` passes; `Citation` interface carries `document_id`; US3 work can begin.

---

## Phase 3: User Story 1 — AI Chat as the Default Home (Priority: P1)

**Goal**: The root path renders the AI chat interface as the primary landing view.

**Independent Test**: Navigate to `http://localhost:3000/` while authenticated; verify the chat input renders as the primary content with no document list in the main area.

**Status**: **DELIVERED** by feature 026. `apps/web/app/page.tsx` already renders `ChatInterface`; `AuthGuard` wraps it. FR-001 is satisfied with zero additional code changes (confirmed in research.md).

- [X] T005 [US1] Confirm US1 acceptance by verifying `apps/web/tests/home.test.tsx` passes and covers "renders the chat interface as the primary content element" (no code changes expected; this is a checkpoint task)

**Checkpoint**: US1 acceptance confirmed — home page renders chat interface by default.

---

## Phase 4: User Story 2 — Document Browser Accessible from Chat (Priority: P2)

**Goal**: Add clearly labelled "Chat" and "Documents" nav links to `NavBar` with active-state highlighting and mobile hamburger support.

**Independent Test**: From the chat home, click "Documents" in the nav bar; verify the document browser renders at `/documents`. Click "Chat"; verify you return to `/`. Both links visible in desktop nav and mobile hamburger without scrolling.

**Dependency**: Independent of Phases 2 and 5 — can be developed in parallel with US3.

- [X] T006 [US2] Write failing NavBar tests covering: Chat link → `/`, Documents link → `/documents`, active styling when `pathname === "/"`, active styling when `pathname === "/documents"`, and both entries visible in mobile menu — in `apps/web/tests/navbar.test.tsx`
- [X] T007 [US2] Add "Chat" (`href="/"`) and "Documents" (`href="/documents"`) as the first two items in the desktop nav link row in `apps/web/components/NavBar.tsx`; use `usePathname` to apply `text-indigo-600 font-medium` to the active link (inactive: `text-slate-600`)
- [X] T008 [US2] Add "Chat" and "Documents" entries at the top of the mobile hamburger menu list in `apps/web/components/NavBar.tsx`; apply the same `usePathname` active-state class logic as the desktop nav

**Checkpoint**: `navbar.test.tsx` passes; "Chat" and "Documents" nav links visible on desktop and mobile; active state highlights the current view.

---

## Phase 5: User Story 3 — In-Chat Document Discovery (Priority: P3)

**Goal**: Render a "Sources" section below each completed AI response listing citation links that open `/documents/{document_id}` in a new tab.

**Independent Test**: Ask the AI a question that returns citations; verify the "Sources" heading appears below the answer with one link per citation; click a link and confirm it opens `/documents/{document_id}` in a new tab without clearing the chat.

**Dependency**: Requires Foundational phase (T003 + T004) to be complete before implementation (T010).

- [X] T009 [P] [US3] Write failing tests in `apps/web/tests/chat.test.tsx` covering: renders "Sources" heading and one `<a>` per citation when answer is complete and non-dont_know; each link has `href="/documents/{document_id}"` and `target="_blank"`; Sources section absent when `dont_know: true`; Sources section absent when `citations` is empty or absent
- [X] T010 [US3] Render a "Sources" section in `apps/web/components/chat/MessageBubble.tsx` — shown only when `turn.status === "complete"` AND `!turn.answer.dont_know` AND `citations.length > 0`; section heading `<p class="text-xs text-slate-400 mt-2">Sources</p>`; each citation as `<a href="/documents/{citation.document_id}" target="_blank" rel="noopener noreferrer" class="text-xs text-indigo-600 hover:underline">{citation.quote.slice(0, 80)}</a>`

**Checkpoint**: `chat.test.tsx` passes; "Sources" section renders correctly for completed answers with citations; absent for dont_know and empty-citation cases.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation and TypeScript compilation check.

- [X] T011 Run TypeScript compiler (`cd apps/web && npx tsc --noEmit`) to confirm no type errors from the `Citation` interface change
- [X] T012 Run the full test suite (`cd apps/web && npm test -- --run` and `cd apps/api && uv run pytest tests/ -v`) and confirm all tests pass
- [X] T013 Execute the quickstart validation steps from `specs/027-ai-first-doc-access/quickstart.md` against the local dev stack to confirm all three user stories work end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Baseline)
  └─▶ Phase 2 (Foundational — Citation DTO)
        └─▶ Phase 5 (US3 — MessageBubble citation links)

Phase 2 (Foundational)
  └─▶ Phase 3 (US1 — confirm delivery, checkpoint only)

Phase 4 (US2 — NavBar) — INDEPENDENT; can start after Phase 1
```

### User Story Dependencies

- **US1 (P1)**: Already delivered. T005 is a checkpoint, not implementation.
- **US2 (P2)**: Independent of US3. Can start after baseline (T001).
- **US3 (P3)**: Depends on Foundational phase (T003 + T004). Implementation (T010) must follow T009 and T004.

### Within Each User Story

- Tests (T006, T009) MUST be written BEFORE implementation; confirm they FAIL before proceeding
- T007 and T008 are sequential (same file: `NavBar.tsx`)
- T010 requires T004 (frontend type) and T009 (failing test) to be complete

---

## Parallel Opportunities

### Parallel Group A (after T001)

```
# These can run concurrently — different files, no shared dependencies:
T002  →  T003   (backend citation tests + implementation)
T004           (frontend types.ts — parallel with T003)
T006           (NavBar tests — independent of citation chain)
```

### Parallel Group B (after T004 and T006)

```
# Once T004 is done and T006 has failing tests:
T007  →  T008  (NavBar implementation, sequential — same file)
T009           (chat.test.tsx failing tests — parallel with T007/T008)
```

### Parallel Group C (after T008 and T009)

```
# T010 requires both T004 and T009:
T010           (MessageBubble implementation)
```

---

## Implementation Strategy

### MVP (User Story 1 only)

US1 is already delivered (feature 026). Confirm with T005. No additional implementation needed.

### Incremental Delivery

1. **Baseline** (T001): Confirm tests are green
2. **Foundation** (T002–T004): Extend Citation DTO — backend + frontend
3. **US1 confirm** (T005): Checkpoint — no code change
4. **US2** (T006–T008): NavBar nav links — independently testable, independently deployable
5. **US3** (T009–T010): Citation links in MessageBubble — independently testable
6. **Polish** (T011–T013): TypeScript check, full suite, quickstart

### Parallel Team Strategy

With two developers:
- **Dev A**: Phase 2 (T002 → T003 → T004) then Phase 5 (T009 → T010)
- **Dev B**: Phase 4 (T006 → T007 → T008) — fully independent track

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks — safe to run in parallel
- [Story] label traces every task to its user story for independent verification
- TDD is mandatory per constitution §IV: write failing test → confirm failure → implement → confirm pass
- `document_id` is already a column in every chunk row from `acl_first_search` — no migration needed
- NavBar already links to `/documents`; only the explicit "Chat" entry and active-state logic are new
- Citation links open `target="_blank"` to preserve chat conversation state (FR-006)
- Commit after each logical group (e.g., after T003+T004, after T007+T008, after T010)
