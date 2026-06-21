---

description: "Task list for UI Color Compliance — migrate gray-*/blue-* to slate-*/indigo-* across 23 files and fix globals.css typography"
---

# Tasks: UI Color Compliance

**Input**: Design documents from `/specs/018-ui-color-compliance/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Tests**: Not requested — this is a purely visual migration; existing `npm test` suite verifies no behavioral regressions.

**Organization**: Tasks are grouped by user story to enable independent verification of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- All tasks include exact file paths

## Migration Reference

Apply these substitutions uniformly. See `plan.md` Color Migration Reference for full table.

| Old | New |
|-----|-----|
| `gray-N` | `slate-N` (all shades, all variants: bg-, text-, border-, hover:, etc.) |
| `blue-N` | `indigo-N` (all shades, all variants: bg-, text-, border-, hover:, focus:, etc.) |
| `font-family: Arial, Helvetica, sans-serif` | `font-family: var(--font-sans)` |

**Never touch**: `red-*` error/destructive classes — out of scope per FR-005.

---

## Phase 1: Setup

**Purpose**: Establish a baseline of current violations before any migration work begins.

- [X] T001 Run `grep -rn "\bblue-[0-9]\|bgray-[0-9]" apps/web/app apps/web/components --include="*.tsx" --include="*.ts" --include="*.css" | grep -v node_modules | grep -v .next` from repo root and record the violation count as the migration baseline

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: Fix `globals.css` typography so the Geist Sans font variable takes effect. This is a prerequisite for meaningful visual verification of all pages.

**⚠️ CRITICAL**: Complete this before beginning visual spot-checks across pages.

- [X] T002 In `apps/web/app/globals.css`, find the `body` rule containing `font-family: Arial, Helvetica, sans-serif` and replace it with `font-family: var(--font-sans)` — preserves the existing `@theme inline` Geist Sans setup

**Checkpoint**: Geist Sans now renders on all pages — user story implementation can begin.

---

## Phase 3: User Story 1 — Consistent Visual Identity Across All Pages (Priority: P1) 🎯 MVP

**Goal**: Every page and component uses `slate-*` for neutral surfaces/text and `indigo-*` for interactive elements. Zero `gray-*` or `blue-*` class names remain after migration.

**Independent Test**: Run the two grep commands from quickstart.md — both must return zero matches. Then open each page and confirm visual consistency per quickstart.md visual walkthrough.

### Core Layout & Shared Components

- [X] T003 [P] [US1] In `apps/web/app/layout.tsx`, replace all `gray-*` Tailwind classes with `slate-*` equivalents (e.g. `bg-gray-50` → `bg-slate-50`)
- [X] T004 [P] [US1] In `apps/web/app/page.tsx`, replace all `gray-*` → `slate-*` and `blue-400` → `indigo-400`
- [X] T005 [P] [US1] In `apps/web/components/NavBar.tsx`, replace all `gray-*` → `slate-*` (nav links, bottom border, logo text)
- [X] T006 [P] [US1] In `apps/web/components/SpaceSelector.tsx`, replace `blue-500` → `indigo-500` (focus ring on dropdown)

### Auth Pages

- [X] T007 [P] [US1] In `apps/web/app/login/page.tsx`, replace all `gray-*` → `slate-*` and `blue-*` → `indigo-*` (inputs, sign-in button, link text, focus rings)
- [X] T008 [P] [US1] In `apps/web/app/register/page.tsx`, replace all `gray-*` → `slate-*` and `blue-*` → `indigo-*` (same pattern as login)

### Document Pages & Components

- [X] T009 [P] [US1] In `apps/web/app/documents/page.tsx`, replace all `gray-*` → `slate-*` and `blue-*` → `indigo-*`; update `STATE_STYLES` object's `archived` entry: `bg-gray-100 text-gray-600` → `bg-slate-100 text-slate-600`
- [X] T010 [P] [US1] In `apps/web/app/documents/[id]/page.tsx`, replace all `gray-*` → `slate-*` and `blue-*` → `indigo-*`; update `STATE_STYLES` object's `archived` entry: `bg-gray-100 text-gray-600` → `bg-slate-100 text-slate-600`
- [X] T011 [P] [US1] In `apps/web/components/documents/AddDocumentModal.tsx`, replace all `gray-*` → `slate-*` and `blue-*` → `indigo-*` (form inputs, Add button, Cancel button hover)

### Search, Admin, Proposals, Metrics Pages

- [X] T012 [P] [US1] In `apps/web/app/search/page.tsx`, replace all `gray-*` → `slate-*` and `blue-*` → `indigo-*` (mode toggle active state, search input focus ring, submit button)
- [X] T013 [P] [US1] In `apps/web/app/admin/page.tsx`, replace all `gray-*` → `slate-*` and `blue-*` → `indigo-*` (table headers, form inputs, submit buttons)
- [X] T014 [P] [US1] In `apps/web/app/proposals/page.tsx`, replace all `gray-*` → `slate-*` and `blue-*` → `indigo-*`; update the dynamic template literal at line 66: `"border-blue-500 bg-blue-50"` → `"border-indigo-500 bg-indigo-50"` and `"hover:bg-gray-50"` → `"hover:bg-slate-50"`
- [X] T015 [P] [US1] In `apps/web/app/metrics/page.tsx`, replace all `gray-*` → `slate-*` (text labels and values — no accent classes in this file)

### Onboarding Pages

- [X] T016 [P] [US1] In `apps/web/app/onboarding/layout.tsx`, replace all `gray-*` → `slate-*`
- [X] T017 [P] [US1] In `apps/web/app/onboarding/invite/page.tsx`, replace all `gray-*` → `slate-*`
- [X] T018 [P] [US1] In `apps/web/app/onboarding/complete/page.tsx`, replace all `gray-*` → `slate-*` and `blue-*` → `indigo-*` (primary button default/hover states)
- [X] T019 [P] [US1] In `apps/web/app/onboarding/pending/page.tsx`, replace all `gray-*` → `slate-*` and `blue-*` → `indigo-*` (primary button default/hover states)
- [X] T020 [P] [US1] In `apps/web/app/onboarding/profile/page.tsx`, replace all `gray-*` → `slate-*` and `blue-*` → `indigo-*` (form inputs, Continue button, focus rings)
- [X] T021 [P] [US1] In `apps/web/app/onboarding/company/page.tsx`, replace all `gray-*` → `slate-*` and `blue-*` → `indigo-*` (search spinner border, form inputs)

### Onboarding Components

- [X] T022 [P] [US1] In `apps/web/components/onboarding/CompanyForm.tsx`, replace all `gray-*` → `slate-*` and `blue-*` → `indigo-*` (form inputs, labels, submit button)
- [X] T023 [P] [US1] In `apps/web/components/onboarding/CompanySuggestions.tsx`, replace all `gray-*` → `slate-*` and `blue-*` → `indigo-*` (invitation card border `indigo-200`, card bg `indigo-50`, Join button)
- [X] T024 [P] [US1] In `apps/web/components/onboarding/InviteForm.tsx`, replace all `gray-*` → `slate-*` and `blue-*` → `indigo-*` (email chips: `indigo-100` bg / `indigo-800` text; chip close: `indigo-500` / `indigo-700` hover; Send Invites button)
- [X] T025 [P] [US1] In `apps/web/components/onboarding/ProgressStepper.tsx`, replace all `gray-*` → `slate-*` and `blue-*` → `indigo-*` (completed step `indigo-600`, current step `indigo-100`/`indigo-700`/`indigo-600`, pending step `slate-100`/`slate-400`, connectors `indigo-600`/`slate-200`)

### User Story 1 Verification

- [X] T026 [US1] Run both grep commands from `specs/018-ui-color-compliance/quickstart.md` (Automated Verification section) — both must return zero matches; any match is an unresolved violation to fix before proceeding
- [X] T027 [US1] Run `cd apps/web && npm test` — all tests must pass; any failure indicates a behavioral regression that must be investigated and resolved

**Checkpoint**: User Story 1 complete — all 23 files migrated, grep clean, tests green. Visual walkthrough can now validate independently.

---

## Phase 4: User Story 2 — Accessible Focus States on All Interactive Elements (Priority: P2)

**Goal**: Every interactive element shows a visible indigo focus ring when receiving keyboard focus; no blue focus rings remain.

**Independent Test**: Tab through all interactive elements on `/login` and `/documents` and confirm all focus rings are indigo, not blue.

- [X] T028 [P] [US2] With dev server running (`cd apps/web && npm run dev`), open `/login` in a browser and tab through the email input, password input, and sign-in button — verify each shows a visible `focus:ring-indigo-500` / `focus:border-indigo-500` highlight (not blue)
- [X] T029 [P] [US2] In the same browser session, open `/documents` and tab to the Add Document button and space selector dropdown — verify both show an indigo focus ring; also verify the Add Document modal inputs show indigo focus rings when opened

**Checkpoint**: Keyboard navigation and screen-reader users receive correct indigo focus indicators on all tested pages.

---

## Phase 5: User Story 3 — No Regressions in Semantic Error States (Priority: P3)

**Goal**: All `red-*` error/destructive color classes are untouched; error states remain visually distinct.

**Independent Test**: Trigger a login failure and a register validation error — verify both show red error styling, not indigo.

- [X] T030 [P] [US3] With dev server running, visit `/login` and submit with wrong credentials — verify the error message displays in `red-*` colors (not indigo); then visit `/register` and submit with mismatched passwords — verify the validation error also displays in `red-*`
- [X] T031 [P] [US3] Run `grep -rn "\bred-[0-9]" apps/web/app apps/web/components --include="*.tsx" --include="*.ts" --include="*.css" | grep -v node_modules | grep -v .next` — confirm all `red-*` occurrences still exist and match the pre-migration baseline count; any removal is a regression

**Checkpoint**: Error states confirmed unchanged — all three user stories independently verified.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Full visual validation across all application routes per quickstart.md.

- [X] T032 Run the complete Visual Walkthrough in `specs/018-ui-color-compliance/quickstart.md` (sections 1–13) covering all routes: `/login`, `/register`, `/`, `/documents`, `/documents/<id>`, Add Document Modal, `/search`, `/admin`, `/proposals`, `/metrics`, `/onboarding/*` (all steps), NavBar, and Space Selector — confirm consistent indigo accent and slate neutral palette with no visible remnants of old color scheme

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — run immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — run T002 before any visual checking
- **User Story 1 (Phase 3)**: Can begin after Foundational — all T003–T025 are parallelizable; T026–T027 must follow completion of T003–T025
- **User Story 2 (Phase 4)**: Depends on Phase 3 completion — requires T003–T027 done
- **User Story 3 (Phase 5)**: Depends on Phase 3 completion — can run in parallel with Phase 4
- **Polish (Final Phase)**: Depends on all three user story phases completing

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational (Phase 2) — no inter-story dependencies
- **US2 (P2)**: Depends on US1 completion — focus ring classes are migrated in US1 file tasks
- **US3 (P3)**: Depends on US1 completion — confirms red-* classes untouched after migration

### Within Phase 3 (US1)

- T003–T025: All parallelizable — different files, no shared state
- T026, T027: Must follow T003–T025 completion

---

## Parallel Example: User Story 1

```bash
# Launch all core layout migrations in parallel:
Task: T003 — apps/web/app/layout.tsx
Task: T004 — apps/web/app/page.tsx
Task: T005 — apps/web/components/NavBar.tsx
Task: T006 — apps/web/components/SpaceSelector.tsx

# Then launch all remaining file groups simultaneously:
Task: T007 — apps/web/app/login/page.tsx
Task: T008 — apps/web/app/register/page.tsx
Task: T009 — apps/web/app/documents/page.tsx
Task: T010 — apps/web/app/documents/[id]/page.tsx
Task: T011 — apps/web/components/documents/AddDocumentModal.tsx
Task: T012 — apps/web/app/search/page.tsx
Task: T013 — apps/web/app/admin/page.tsx
Task: T014 — apps/web/app/proposals/page.tsx
Task: T015 — apps/web/app/metrics/page.tsx
Task: T016 — apps/web/app/onboarding/layout.tsx
Task: T017 — apps/web/app/onboarding/invite/page.tsx
Task: T018 — apps/web/app/onboarding/complete/page.tsx
Task: T019 — apps/web/app/onboarding/pending/page.tsx
Task: T020 — apps/web/app/onboarding/profile/page.tsx
Task: T021 — apps/web/app/onboarding/company/page.tsx
Task: T022 — apps/web/components/onboarding/CompanyForm.tsx
Task: T023 — apps/web/components/onboarding/CompanySuggestions.tsx
Task: T024 — apps/web/components/onboarding/InviteForm.tsx
Task: T025 — apps/web/components/onboarding/ProgressStepper.tsx
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (baseline grep)
2. Complete Phase 2: Foundational (globals.css typography fix)
3. Complete Phase 3: User Story 1 (all 23 file migrations + grep + test)
4. **STOP and VALIDATE**: Grep clean, tests pass, visual walkthrough clean
5. Ship — US2 and US3 are verification stories that confirm US1 is correct

### Incremental Delivery

1. Complete Setup + Foundational → ready to migrate
2. Complete US1 file migrations → grep verification → npm test → MVP checkpoint
3. Add US2 verification → confirm focus states in browser
4. Add US3 verification → confirm error states unchanged
5. Full quickstart.md walkthrough → done

### Parallel Team Strategy

With multiple developers:

1. Complete T001–T002 together
2. Once T002 is done, split T003–T025 across developers (all independent files)
3. Run T026–T027 together once all migrations complete
4. T028–T029 (US2) and T030–T031 (US3) in parallel by different developers
5. T032 walkthrough together as final sign-off

---

## Notes

- **[P]** tasks operate on different files — no merge conflicts, full parallelism safe
- The `STATE_STYLES` object in T009 and T010 is a JavaScript object, not JSX — grep-based migration must check object values, not just JSX className strings
- The dynamic template literal in T014 (`proposals/page.tsx` line 66) is flagged in research.md — both string branches are static and Tailwind-visible; migrate both strings in the conditional expression
- `red-*` classes are never touched — any tool doing batch substitution must exclude this family
- `--background` / `--foreground` CSS custom properties in `globals.css` are hex values, not color-scale tokens — leave untouched per research.md findings
- Commit after each logical group or user story phase to keep diffs reviewable
