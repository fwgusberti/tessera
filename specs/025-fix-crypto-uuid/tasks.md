---
description: "Task list for 025-fix-crypto-uuid"
---

# Tasks: Fix Chat Submit Crash on UUID Generation

**Input**: Design documents from `/specs/025-fix-crypto-uuid/`

**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/generate-id.md ✅ quickstart.md ✅

**Tests**: Included — TDD is non-negotiable per constitution Principle IV.

**Organization**: Single user story (US1, P1). No blocking foundational phase — project structure already exists.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Confirm baseline before adding new code.

No new project structure is required — `apps/web` already exists with Vitest, TypeScript, and the `lib/utils/` convention in place.

- [X] T001 Verify baseline test suite passes by running `npx vitest run` in `apps/web/` (confirms no pre-existing failures before changes land)

---

## Phase 2: Foundational (Blocking Prerequisites)

No foundational prerequisites beyond Phase 1 — the existing project infrastructure is sufficient for this fix.

**Checkpoint**: Baseline verified — US1 implementation can begin.

---

## Phase 3: User Story 1 — Submit a Chat Question Without Error (Priority: P1) 🎯 MVP

**Goal**: Replace the bare `crypto.randomUUID()` call in `ChatInterface.tsx` with a `generateId()` utility that falls back to `crypto.getRandomValues()` in non-secure browser contexts, so chat submissions no longer crash on HTTP.

**Independent Test**: Open the chat page over HTTP (non-localhost) and submit any question — no `TypeError: crypto.randomUUID is not a function` should appear; the turn renders as pending then resolves.

### Tests for User Story 1 (TDD — write FIRST, confirm they FAIL before implementing)

- [X] T002 [US1] Write unit tests for `generateId()` — happy path, fallback path, uniqueness — in `apps/web/tests/generate-id.test.ts`

> **NOTE**: Run `npx vitest run tests/generate-id.test.ts` in `apps/web/` after writing tests and confirm they FAIL (file does not exist yet). Only then proceed to T003.

### Implementation for User Story 1

- [X] T003 [US1] Create `generateId()` utility with `getRandomValues` fallback in `apps/web/lib/utils/generate-id.ts` (depends on T002 failing)
- [X] T004 [US1] Update `ChatInterface.tsx` to import and call `generateId()` instead of `crypto.randomUUID()` in `apps/web/components/chat/ChatInterface.tsx` (depends on T003)

**Checkpoint**: At this point run `npx vitest run tests/generate-id.test.ts` — all three tests must pass (T002 green). User Story 1 is fully functional and testable independently.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Validate TypeScript and confirm no regressions across the existing suite.

- [X] T005 [P] Run TypeScript compilation check with `npx tsc --noEmit` in `apps/web/` — zero errors required
- [X] T006 [P] Run full test suite with `npx vitest run` in `apps/web/` — existing `chat.test.tsx` tests must continue to pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Trivially satisfied; no blocking work
- **User Story 1 (Phase 3)**: Depends on baseline confirmation from Phase 1
  - T002 → T003 → T004 (sequential within story; TDD requires test failure before implementation)
- **Polish (Phase 4)**: Depends on Phase 3 completion; T005 and T006 can run in parallel

### Within User Story 1

- T002 (tests) MUST be written and FAIL before T003 (implementation)
- T003 (utility) MUST exist before T004 (call-site update in ChatInterface.tsx)
- T004 is the final implementation step; run tests again to confirm all pass

### Parallel Opportunities

- T005 and T006 (Polish phase) can run in parallel — different commands, no shared output

---

## Parallel Example: Polish Phase

```bash
# Run both final validation gates at the same time:
npx tsc --noEmit          # in apps/web/ — T005
npx vitest run            # in apps/web/ — T006
```

---

## Implementation Strategy

### MVP (This is the entire feature — one story, four tasks)

1. Complete Phase 1: Verify baseline
2. Complete Phase 3 in order: T002 → T003 → T004
3. Complete Phase 4: T005 + T006 in parallel
4. **VALIDATE**: All three `generate-id` tests pass; existing chat tests pass; zero TypeScript errors

### TDD Sequence

```bash
# Step 1: Write tests (T002)
# Step 2: Confirm they fail
cd apps/web && npx vitest run tests/generate-id.test.ts   # → FAIL

# Step 3: Implement utility (T003)
# Step 4: Update ChatInterface.tsx (T004)
# Step 5: Confirm all pass
cd apps/web && npx vitest run tests/generate-id.test.ts   # → PASS

# Step 6: Full validation (T005, T006)
cd apps/web && npx tsc --noEmit && npx vitest run
```

---

## Notes

- [P] tasks = different files, no shared dependencies
- Constitution Principle IV (TDD non-negotiable): tests MUST be written before implementation and confirmed failing
- Constitution Principle V (Quality Gates): `tsc --noEmit` must pass — enforced in T005
- No new npm runtime dependencies introduced; `crypto` is a browser built-in
- `ChatTurn` type in `lib/types.ts` is unchanged — no model migration required
