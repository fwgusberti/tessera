# Tasks: Fix Field Text Contrast

**Input**: Design documents from `specs/021-fix-field-text-contrast/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, contracts/css-rules.md ✅, quickstart.md ✅

**Tests**: No automated tests — CSS-only change; validation is visual inspection per quickstart.md.
Constitution IV (TDD) applies only to Python business-domain modules (≥85% coverage).

**Organization**: Phase 2 is the sole implementation phase (one CSS file, two rule blocks).
Phases 3–4 map to US1/US2 visual-validation scenarios from quickstart.md.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different browser tabs / no shared file edits)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Exact file paths included in all descriptions

## Path Conventions

Web app frontend: `apps/web/app/` (Next.js App Router)

---

## Phase 1: Setup

**Purpose**: Confirm insertion point in globals.css before making the change

- [x] T001 Inspect apps/web/app/globals.css to locate the end of the existing base-layer rules and identify where to insert the new form-element color block

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: The entire implementation — two CSS rule blocks in one file. Enables both user stories.

**⚠️ CRITICAL**: All US1 and US2 validation depends on this phase completing first.

- [x] T002 Add form-field text-color rule block to apps/web/app/globals.css — `input:not([type="checkbox"]):not([type="radio"]):not([type="range"]):not([type="color"]):not([type="file"]), textarea, select { color: var(--color-slate-900); }` per contracts/css-rules.md
- [x] T003 Add placeholder text-color rule block to apps/web/app/globals.css immediately after T002 — `::placeholder { color: var(--color-slate-400); opacity: 1; }` per contracts/css-rules.md (opacity: 1 overrides Firefox default)

**Checkpoint**: globals.css contains both new rule blocks matching contracts/css-rules.md exactly; dev server reloads automatically.

---

## Phase 3: User Story 1 — Read Text in Form Fields (Priority: P1) 🎯 MVP

**Goal**: User-entered and pre-filled text is clearly readable in all standard form fields across all pages in all normal states (default, filled).

**Independent Test**: Open any page with a form field, type text, and confirm characters are clearly dark (slate-900) against the white field background — quickstart SC-001 through SC-007.

### Implementation for User Story 1

- [ ] T004 [P] [US1] Visually verify login and registration pages in apps/web/app/login/page.tsx and apps/web/app/register/page.tsx — type into all fields and confirm text is clearly readable (quickstart SC-001, SC-002)
- [ ] T005 [P] [US1] Visually verify placeholder text contrast on apps/web/app/login/page.tsx and apps/web/app/admin/page.tsx — confirm placeholder is medium gray (slate-400), lighter than filled text but not invisible (quickstart SC-003)
- [ ] T006 [P] [US1] Visually verify search, admin, documents, and onboarding pages in apps/web/app/search/page.tsx, apps/web/app/admin/page.tsx, apps/web/components/documents/AddDocumentModal.tsx, and apps/web/app/onboarding/profile/page.tsx — type into all inputs and selects (quickstart SC-004, SC-005, SC-006, SC-007)

**Checkpoint**: All basic form fields display clearly readable text across all pages — US1 fully validated.

---

## Phase 4: User Story 2 — Read Text in Focused and Error States (Priority: P2)

**Goal**: Field text remains clearly readable when the field is focused (active) or displaying a validation error. No additional CSS changes expected — same rules from Phase 2 cover these states.

**Independent Test**: Tab into a field to trigger the focus ring; submit an empty login form to trigger an error — confirm text is readable in both states (quickstart SC-008, SC-009).

### Implementation for User Story 2

- [ ] T007 [P] [US2] Validate focused-state text contrast in apps/web/app/globals.css — Tab into any field and confirm focus ring (indigo-500) appears while text color remains clearly readable, no color degradation (quickstart SC-008)
- [ ] T008 [P] [US2] Validate error-state text contrast in apps/web/app/globals.css — submit login form with empty Email, confirm text remains clearly readable despite red border/highlight (quickstart SC-009)

**Checkpoint**: Both focus and error states confirmed — text readable in all field states. If either fails, add a state-scoped override to apps/web/app/globals.css.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Regression check on surrounding UI elements and final CSS diff verification.

- [ ] T009 Scan labels, error messages, and surrounding text on each page visited in Phases 3–4 and confirm no surrounding text has become harder to read (quickstart SC-010)
- [ ] T010 [P] Verify apps/web/app/globals.css diff matches the exact rule blocks in contracts/css-rules.md — no extra selectors, no missing opacity line, no gray-* or blue-* introduced (constitution compliance)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on T001 — BLOCKS all validation phases
- **US1 (Phase 3)**: Depends on T002 + T003 (Phase 2 complete)
- **US2 (Phase 4)**: Depends on T002 + T003 (Phase 2 complete); independent of Phase 3
- **Polish (Phase 5)**: Depends on Phase 3 and Phase 4 checkpoints passing

### User Story Dependencies

- **US1 (P1)**: Can begin as soon as Phase 2 is complete — no dependency on US2
- **US2 (P2)**: Can begin as soon as Phase 2 is complete — independent of US1

### Within Each User Story

- T004, T005, T006 are all [P] — can run simultaneously in separate browser tabs
- T007 and T008 are both [P] — can run simultaneously in separate browser tabs
- No code edits in Phases 3–5 (implementation complete after Phase 2)

---

## Parallel Example: User Story 1

```bash
# All US1 validation tasks launch together after Phase 2:
Tab A: T004 — login and register pages
Tab B: T005 — placeholder contrast
Tab C: T006 — search, admin, documents, onboarding
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. T001: Inspect globals.css
2. T002 → T003: Add both CSS rule blocks (entire implementation, ~10 lines)
3. T004 + T005 + T006: Validate US1 across all pages
4. **STOP and VALIDATE**: US1 fully functional — can ship if acceptable
5. T007 + T008 + T009 + T010: Complete US2 and polish before merging

### Incremental Delivery

1. Phase 1 + Phase 2 → implementation complete (< 10 min)
2. Phase 3 → all standard fields readable → US1 MVP
3. Phase 4 → focused and error states validated → US2
4. Phase 5 → no regressions, diff verified → ready to merge

---

## Notes

- [P] tasks = independent browser-tab validations; no shared file conflicts
- The **entire code change** is T002 + T003 — one CSS file, ~10 lines
- All Phase 3–5 tasks are visual inspection only (no code edits unless a gap is found)
- Start dev server before Phase 3: `cd apps/web && npm run dev`
- Reference: quickstart.md has exact URLs and expected outcomes per scenario
- Reference: contracts/css-rules.md has the authoritative CSS diff to verify after implementation
