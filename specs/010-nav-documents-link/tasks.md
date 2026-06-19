---
description: "Task list for Documents Navigation Link feature"
---

# Tasks: Documents Navigation Link

**Input**: Design documents from `specs/010-nav-documents-link/`

**Prerequisites**: plan.md ✅, spec.md ✅, quickstart.md ✅

**Organization**: Single user story — tasks proceed sequentially (TDD: test first).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No project initialization needed — all dependencies already in place.

*(Skipped — existing NavBar component and test infrastructure require no setup.)*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational blockers — change is fully self-contained.

*(Skipped — single file component edit with no shared infrastructure changes.)*

---

## Phase 3: User Story 1 — Navigate to Documents via Nav (Priority: P1) 🎯 MVP

**Goal**: A logged-in user can reach `/documents` in one click from the navigation bar.

**Independent Test**: Log in → see "Documents" in the NavBar → click it → documents list page loads.

### Tests for User Story 1 (TDD — write first, confirm they FAIL before implementing)

- [x] T001 [US1] Add `expect(screen.getByRole("link", { name: /documents/i })).toBeInTheDocument()` assertion to the "renders navigation links" test in `apps/web/tests/navbar.test.tsx` — run `npx vitest run tests/navbar.test.tsx` and confirm it **FAILS**

### Implementation for User Story 1

- [x] T002 [P] [US1] Add `<a href="/documents" className="text-sm text-gray-600 hover:text-gray-900">Documents</a>` after the Search link in `apps/web/components/NavBar.tsx`
- [x] T003 [US1] Run `npx vitest run tests/navbar.test.tsx` in `apps/web/` and confirm all tests **PASS**

**Checkpoint**: NavBar shows "Documents" link; all 5 navbar tests pass; clicking Documents loads `/documents`.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Final validation.

- [x] T004 [P] Run quickstart.md validation: start dev server (`npm run dev` in `apps/web/`) and verify Documents link appears between Search and Proposals, navigates correctly, and redirects to `/login` when unauthenticated

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 3**: No phase dependencies — can start immediately
- **Phase 4**: Depends on T003 passing

### Within User Story 1

- T001 (test) MUST be written and **FAIL** before T002 (implementation)
- T002 and T003 are sequential (write → verify)
- T004 can run after T003

### Parallel Opportunities

- T002 and T004 have no file conflicts with other features in flight but must run after T001

---

## Parallel Example: User Story 1

```bash
# Sequential TDD flow (no parallelism within this tiny feature):
T001 → run tests → confirm FAIL
T002 → add link
T003 → run tests → confirm PASS
T004 → browser validation
```

---

## Implementation Strategy

### MVP (this feature IS the MVP — single user story)

1. T001: Write failing test
2. T002: Add nav link
3. T003: Confirm tests pass
4. T004: Browser validation

---

## Notes

- TDD is non-negotiable per Constitution Principle IV — T001 must fail before T002 is coded
- No new dependencies, no migrations, no backend changes
- Total change: 1 `<a>` tag in NavBar.tsx + 1 test assertion in navbar.test.tsx
