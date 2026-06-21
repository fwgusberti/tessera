---
description: "Task list for feature 019-responsive-ui"
---

# Tasks: Responsive UI for Smartphones

**Input**: Design documents from `/specs/019-responsive-ui/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/responsive-ui.md ✅, quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Exact file paths are included in every task description

---

## Phase 1: Setup

**Purpose**: Confirm the dev environment is stable before making layout changes.

- [X] T001 Start the dev server and confirm the app loads without errors (`cd apps/web && npm run dev`, open http://localhost:3000)

---

## Phase 2: Foundational (Baseline Verification)

**Purpose**: Establish a green test baseline before any changes. All user story phases depend on this checkpoint.

**⚠️ CRITICAL**: Run the full test suite first so any later failure can be attributed to this feature, not a pre-existing issue.

- [X] T002 Run the existing test suite to establish a green baseline (`cd apps/web && npm test`) and record the passing count

**Checkpoint**: Baseline green — all four user story phases can now proceed independently.

---

## Phase 3: User Story 1 — Browse and Read Documents on Mobile (Priority: P1) 🎯 MVP

**Goal**: Documents list, document detail, search, and Add Document modal render without horizontal overflow on 320px–767px viewports.

**Independent Test**: Open a 390px-wide viewport in DevTools, navigate to `/documents`, scroll the list, open a document — no horizontal scrollbar appears and all content is readable.

### Implementation for User Story 1

- [X] T003 [P] [US1] Wrap the documents `<table>` in `<div className="overflow-x-auto">` and add `hidden md:table-cell` to the Confidentiality `<th>` and every Confidentiality `<td>` in `apps/web/app/documents/page.tsx`
- [X] T004 [P] [US1] Change the document detail header container from `flex items-start justify-between gap-4` to `flex flex-col sm:flex-row items-start justify-between gap-4` so the title and action buttons (Publish / Reindex) stack vertically on mobile in `apps/web/app/documents/[id]/page.tsx`
- [X] T005 [P] [US1] Audit `apps/web/app/search/page.tsx` for any fixed-width or non-wrapping flex rows; add `flex-wrap` or responsive classes if overflow is found (plan says no changes expected — verify and confirm)
- [X] T006 [US1] Change the Language + Confidentiality selector grid from `grid grid-cols-2 gap-3` to `grid grid-cols-1 sm:grid-cols-2 gap-3` in `apps/web/components/documents/AddDocumentModal.tsx`

**Checkpoint**: User Story 1 fully functional — documents list, detail, and modal are usable on 390px viewport without horizontal scroll.

---

## Phase 4: User Story 2 — Navigate the App on Mobile (Priority: P1)

**Goal**: A hamburger menu overlay replaces the horizontal nav links on viewports narrower than 768px; SpaceSelector fills its container width.

**Independent Test**: At a 390px viewport, confirm the hamburger button is visible, tap it to open the nav overlay, tap each section link to navigate, and press Escape to close — no layout overflow on any page.

### Implementation for User Story 2

- [X] T007 [US2] Add `isMenuOpen` boolean state (`useState(false)`), a hamburger button (`md:hidden min-h-[44px] min-w-[44px]` with `aria-label="Open menu"`), hide the desktop link row behind `hidden md:flex`, and render a mobile overlay panel below the top bar with all nav links stacked vertically when `isMenuOpen` is true in `apps/web/components/NavBar.tsx`
- [X] T008 [US2] Add `onClick={() => setIsMenuOpen(false)}` to each mobile nav link, a `useEffect` keydown listener that calls `setIsMenuOpen(false)` on Escape, and an outside-click handler (overlay backdrop `onClick`) in `apps/web/components/NavBar.tsx` (depends on T007)
- [X] T009 [P] [US2] Add `w-full` to the `<select>` element's className in `apps/web/components/SpaceSelector.tsx`
- [X] T010 [P] [US2] Update `apps/web/tests/navbar.test.tsx` to cover: hamburger button is visible at mobile width, desktop links are hidden at mobile width, menu opens on hamburger click, menu closes on nav link click, menu closes on Escape key press

**Checkpoint**: User Story 2 fully functional — hamburger menu opens/closes, all nav destinations reachable at 390px, SpaceSelector fills its container.

---

## Phase 5: User Story 3 — Complete Onboarding on Mobile (Priority: P2)

**Goal**: All five onboarding steps (profile, company, invite, complete, pending) are usable on 390px and 320px viewports with the ProgressStepper fitting within 320px.

**Independent Test**: On a 390px viewport, complete the full onboarding flow end-to-end; at 320px, confirm the ProgressStepper does not overflow horizontally.

### Implementation for User Story 3

- [X] T011 [P] [US3] Change the white card padding from `p-8` to `p-4 sm:p-8` in `apps/web/app/onboarding/layout.tsx`
- [X] T012 [P] [US3] Reduce connector width from `w-12` to `w-6 sm:w-12`, step margins from `mx-2` to `mx-1 sm:mx-2`, and step label font size to `text-[10px] sm:text-xs` in `apps/web/components/onboarding/ProgressStepper.tsx`
- [X] T013 [P] [US3] Audit `apps/web/app/onboarding/profile/page.tsx` for fixed widths or non-wrapping flex rows; add `flex-wrap` or `flex-col sm:flex-row` responsive classes where overflow exists
- [X] T014 [P] [US3] Audit `apps/web/app/onboarding/company/page.tsx` and `apps/web/components/onboarding/CompanyForm.tsx` for fixed widths or non-wrapping flex rows; add responsive classes as needed
- [X] T015 [P] [US3] Audit `apps/web/components/onboarding/CompanySuggestions.tsx` for overflow on narrow viewports; ensure suggestion list items wrap or truncate gracefully
- [X] T016 [P] [US3] Audit `apps/web/app/onboarding/invite/page.tsx` and `apps/web/components/onboarding/InviteForm.tsx` for fixed widths; add responsive classes as needed
- [X] T017 [P] [US3] Audit `apps/web/app/onboarding/complete/page.tsx` and `apps/web/app/onboarding/pending/page.tsx` for fixed widths or horizontal overflow; add responsive layout classes as needed

**Checkpoint**: User Story 3 fully functional — full onboarding flow is completable on 390px; ProgressStepper fits within 320px viewport.

---

## Phase 6: User Story 4 — Log In and Register on Mobile (Priority: P2)

**Goal**: Login and register form containers use `min-h-dvh` and reduced top padding so the submit button remains reachable when the device keyboard is active.

**Independent Test**: At 390px with simulated keyboard (Chrome DevTools device emulation), tap the email field, confirm the Submit button is still visible or reachable by scrolling up within the viewport.

### Implementation for User Story 4

- [X] T018 [P] [US4] Replace `min-h-screen` with `min-h-dvh` and change outer container vertical padding from `py-12` to `py-8 sm:py-12` in `apps/web/app/login/page.tsx`
- [X] T019 [P] [US4] Replace `min-h-screen` with `min-h-dvh` and change outer container vertical padding from `py-12` to `py-8 sm:py-12` in `apps/web/app/register/page.tsx`

**Checkpoint**: User Story 4 fully functional — login and register forms are operable on 390px with the keyboard active.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Audit remaining pages, add viewport smoke tests, and confirm quality gates pass.

- [X] T020 [P] Audit `apps/web/app/proposals/page.tsx` for horizontal overflow on 390px; add `overflow-x-auto` wrapper, `flex-wrap`, or `flex-col sm:flex-row` classes as needed
- [X] T021 [P] Audit `apps/web/app/metrics/page.tsx` for horizontal overflow on 390px; add responsive layout classes as needed
- [X] T022 [P] Audit `apps/web/app/admin/page.tsx` for horizontal overflow on 390px; add responsive layout classes as needed
- [X] T023 Create `apps/web/tests/responsive.test.tsx` with Playwright viewport smoke tests (or vitest + jsdom fallback) asserting `document.documentElement.scrollWidth === window.innerWidth` at 390px and 320px on: documents list, document detail, login, register, and onboarding/profile pages
- [X] T024 [P] Run `cd apps/web && npm run lint` and confirm no new ESLint errors introduced by this feature (quality gate per constitution Principle V)
- [X] T025 Run `cd apps/web && npm test` and confirm the full test suite passes with no regressions (all previously passing tests must still pass)
- [X] T026 Validate all seven scenarios in `specs/019-responsive-ui/quickstart.md` using Chrome DevTools at 390px and 320px; confirm the overflow audit script in quickstart.md returns an empty array on all key pages

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — establishes baseline; SHOULD complete before user story phases to attribute any test failures correctly
- **User Stories (Phases 3–6)**: All depend only on Phase 2 completion; stories are fully independent of each other (no shared files)
- **Polish (Final Phase)**: Depends on all desired user story phases being complete

### User Story Dependencies

- **US1 (Phase 3, P1)**: Independent — files: `documents/page.tsx`, `documents/[id]/page.tsx`, `search/page.tsx`, `AddDocumentModal.tsx`
- **US2 (Phase 4, P1)**: Independent — files: `NavBar.tsx`, `SpaceSelector.tsx`, `tests/navbar.test.tsx`
- **US3 (Phase 5, P2)**: Independent — files: `onboarding/layout.tsx`, `ProgressStepper.tsx`, onboarding page files
- **US4 (Phase 6, P2)**: Independent — files: `login/page.tsx`, `register/page.tsx`

### Within Each User Story

- US2: T007 must complete before T008 (same file, sequential change)
- US1: T003, T004, T005 can run in parallel; T006 can also run in parallel
- US3: T011–T017 can all run in parallel (all different files)
- US4: T018 and T019 can run in parallel (different files)

---

## Parallel Execution Examples

### User Story 1 (Phase 3)

```bash
# Run in parallel — all different files:
Task T003: wrap table in overflow-x-auto, hide Confidentiality column — apps/web/app/documents/page.tsx
Task T004: flex-col sm:flex-row on document detail header — apps/web/app/documents/[id]/page.tsx
Task T005: audit search page — apps/web/app/search/page.tsx
# T006 follows after confirming T003 context (AddDocumentModal is independent but accessed from documents)
Task T006: grid-cols-1 sm:grid-cols-2 — apps/web/components/documents/AddDocumentModal.tsx
```

### User Story 3 (Phase 5)

```bash
# All parallel — all different files:
Task T011: p-4 sm:p-8 onboarding layout — apps/web/app/onboarding/layout.tsx
Task T012: compress ProgressStepper — apps/web/components/onboarding/ProgressStepper.tsx
Task T013: audit profile page — apps/web/app/onboarding/profile/page.tsx
Task T014: audit company page + CompanyForm — apps/web/app/onboarding/company/page.tsx
Task T015: audit CompanySuggestions — apps/web/components/onboarding/CompanySuggestions.tsx
Task T016: audit invite page + InviteForm — apps/web/app/onboarding/invite/page.tsx
Task T017: audit complete + pending pages — apps/web/app/onboarding/complete/page.tsx
```

---

## Implementation Strategy

### MVP First (US1 + US2 — both P1)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002)
3. Complete Phase 3: US1 — Documents readable on mobile (T003–T006)
4. Complete Phase 4: US2 — Navigation usable on mobile (T007–T010)
5. **STOP and VALIDATE**: Full critical path (log in → find document → read it) works at 390px
6. Demo / deploy MVP

### Incremental Delivery

1. Setup + Foundational → green baseline ✓
2. US1 → documents and search usable on mobile → validate → deploy
3. US2 → hamburger nav → validate → deploy
4. US3 → onboarding mobile-ready → validate → deploy
5. US4 → login/register keyboard-safe → validate → deploy
6. Polish → audit pages + tests + lint → final QA pass

---

## Notes

- `[P]` = different files, no incomplete task dependencies — safe to parallelize
- `[USN]` = maps to user story N from spec.md for traceability
- Constitution constraint: no new color classes (`blue-*`, `gray-*`), no new npm packages, no typography changes — layout/spacing classes only
- Desktop layout (≥ 768px) must be pixel-identical to baseline — use `md:` prefix to gate all mobile-only changes
- Commit after each phase checkpoint; use the quickstart.md overflow audit script to verify each story independently before moving on
