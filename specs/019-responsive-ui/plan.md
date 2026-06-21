# Implementation Plan: Responsive UI for Smartphones

**Branch**: `019-responsive-ui` | **Date**: 2026-06-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/019-responsive-ui/spec.md`

## Summary

Make the Tessera Next.js web app fully usable on smartphone viewports (320px–767px) by adding Tailwind responsive classes to existing components, replacing the desktop-only nav with a hamburger overlay on mobile, converting the document list table to a card layout below `md`, and ensuring all interactive controls meet the 44×44pt touch target minimum. No new packages, no design-token changes; layout and spacing classes only.

## Technical Context

**Language/Version**: TypeScript 5.x / Next.js 14 (App Router)

**Primary Dependencies**: React 18, Tailwind CSS 3.x (breakpoints: `sm`=640px, `md`=768px, `lg`=1024px)

**Storage**: N/A (UI-only change)

**Testing**: Playwright (E2E) for viewport smoke tests; Vitest + Testing Library for component-level tests

**Target Platform**: Web browser on smartphones (portrait, 320px–767px) and desktop (≥ 768px unchanged)

**Project Type**: Web application (Next.js frontend)

**Performance Goals**: No bundle-size regression beyond a negligible state variable for the mobile menu toggle

**Constraints**: Must not change any color, font, or spacing token defined in the constitution's UI Design System. No new npm packages. Desktop layout (≥ 768px) must be pixel-identical to today.

**Scale/Scope**: 11 pages + 4 shared components modified. No backend changes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Justification |
|-----------|--------|---------------|
| I. Domain-Driven Architecture | ✅ PASS | Pure frontend layout change; no domain logic touched |
| II. Separation of Concerns | ✅ PASS | No product/domain definitions altered |
| III. Data Locality & Consent | ✅ PASS | No new client-side persistence introduced |
| IV. Test-Driven Development | ✅ PASS | Responsive viewport tests will be written alongside code changes. Coverage applies to Python modules; frontend component tests added to maintain the spirit |
| V. Quality Gates | ✅ PASS | Only TypeScript/TSX changes; Ruff/Black checks apply to Python only — ESLint must stay clean |
| UI Design System | ✅ PASS | FR-009 is explicit: only layout/spacing classes change, not color or typography tokens. `slate-*`, `indigo-*`, Geist font — all preserved |

**No violations. Phase 0 may proceed.**

## Project Structure

### Documentation (this feature)

```text
specs/019-responsive-ui/
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── responsive-ui.md # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository)

```text
apps/web/
├── app/
│   ├── layout.tsx                          # Root layout — no change needed (px-4 already fine)
│   ├── login/page.tsx                      # Keyboard-avoidance tweak
│   ├── register/page.tsx                   # Keyboard-avoidance tweak
│   ├── documents/page.tsx                  # Table → card layout on mobile
│   ├── documents/[id]/page.tsx             # Header flex → flex-col on mobile
│   ├── search/page.tsx                     # Search bar row verified OK; no changes
│   ├── proposals/page.tsx                  # Audit and fix if needed
│   ├── metrics/page.tsx                    # Audit and fix if needed
│   ├── admin/page.tsx                      # Audit and fix if needed
│   └── onboarding/
│       ├── layout.tsx                      # Card padding responsive (p-8 → p-4 sm:p-8)
│       ├── profile/page.tsx                # Audit — forms already use w-full; verify
│       ├── company/page.tsx                # Audit
│       ├── invite/page.tsx                 # Audit
│       ├── complete/page.tsx               # Audit
│       └── pending/page.tsx                # Audit
├── components/
│   ├── NavBar.tsx                          # PRIMARY CHANGE — hamburger mobile menu
│   ├── SpaceSelector.tsx                   # Add w-full for mobile
│   ├── documents/
│   │   └── AddDocumentModal.tsx            # 2-col grid → 1-col on mobile
│   └── onboarding/
│       └── ProgressStepper.tsx             # Tighten spacing on mobile
└── tests/
    ├── navbar.test.tsx                     # Add mobile nav tests
    └── responsive.test.tsx                 # New: Playwright viewport smoke tests (OR vitest jsdom)
```

**Structure Decision**: Single-project web app. All changes live under `apps/web/`. No new directories needed beyond `specs/019-responsive-ui/contracts/` for planning artifacts.

## Complexity Tracking

No constitution violations. No complexity justification required.

---

## Phase 0 Research

See [research.md](research.md) for all decisions with rationale.

## Phase 1 Design

### Data Model

See [data-model.md](data-model.md). No new database entities. Documents responsive UI concepts (breakpoints, touch targets, layout modes).

### Contracts

See [contracts/responsive-ui.md](contracts/responsive-ui.md). Defines the responsive contract each component must satisfy.

### Validation Guide

See [quickstart.md](quickstart.md) for runnable validation scenarios.

---

## File-by-File Change Summary

### `components/NavBar.tsx` — HIGHEST PRIORITY

**Current state**: Flat horizontal row of `<a>` links. No responsive handling. On 390px screens, all links wrap or overflow.

**Change**: Add hamburger button (`md:hidden`) that toggles a `useState` boolean. When open, render an overlay `<div>` with vertical nav links below the top bar. Hide the horizontal link list on mobile (`hidden md:flex`).

```
Before: <div className="flex items-center gap-4"> — always visible
After:
  - Desktop (md+): flex row of links (unchanged)
  - Mobile (<md): hamburger icon button + collapsible vertical menu
```

**Touch target**: Hamburger button must be `min-h-[44px] min-w-[44px]`.

---

### `components/SpaceSelector.tsx`

**Current state**: `<select>` without width class — collapses to content width on mobile.

**Change**: Add `w-full` to the select element.

---

### `components/onboarding/ProgressStepper.tsx`

**Current state**: 4 circles (32px each) + 3 connectors (`w-12`=48px each) + spacing (`mx-2`=8px × 6) = 128 + 144 + 48 = 320px total. This barely fits on 320px viewport; connector labels add more height below.

**Change**: Reduce connector width on mobile (`w-8 sm:w-12`) and reduce `mx-2` to `mx-1 sm:mx-2`. Optionally hide step labels on screens ≤ 360px (`hidden xs:block` — but Tailwind has no `xs` by default; use `sr-only sm:not-sr-only` pattern to keep labels accessible).

---

### `components/documents/AddDocumentModal.tsx`

**Current state**: Language + Confidentiality selects in a `grid grid-cols-2 gap-3`. On 390px with `mx-4` margin, inner dialog is 358px, minus `px-6`×2=48px = 310px. Two columns at 310px = 155px each, which is fine. But on 320px: 312px - 48px = 264px / 2 = 132px per column — very tight.

**Change**: `grid-cols-1 sm:grid-cols-2` to stack on very small screens.

The `max-w-lg mx-4` dialog itself is fine (capped to viewport - 32px).

---

### `app/documents/page.tsx`

**Current state**: Documents render as a `<table>` with 3 columns. On mobile, tables overflow horizontally.

**Change**: Wrap the table in `<div className="overflow-x-auto">` (minimal, preserves all columns). Alternatively, add a card view for `md:hidden` and keep the table for `hidden md:block`. The card approach is better UX; the overflow-x-auto approach is simpler and lower risk.

**Decision from research**: Use overflow-x-auto wrapper for the table (safe, no markup duplication). Additionally show fewer columns using responsive `hidden md:table-cell` on the less critical "Confidentiality" column.

---

### `app/documents/[id]/page.tsx`

**Current state**: `<div className="flex items-start justify-between gap-4">` with title on the left and action buttons on the right. On mobile, if both title and button are on the same row, the title gets squeezed.

**Change**: `flex-col sm:flex-row items-start justify-between gap-4` — stack vertically on mobile, horizontal on sm+.

---

### `app/onboarding/layout.tsx`

**Current state**: White card has `p-8` (32px padding all sides). On 390px this leaves 374px - 64px = 310px inner width. Acceptable, but on 320px: 304px - 64px = 240px which is very narrow for form labels + inputs.

**Change**: `p-4 sm:p-8` for the white card.

---

### `app/login/page.tsx` and `app/register/page.tsx`

**Current state**: `<div className="flex items-center justify-center py-12">` with a `max-w-sm` card. The `py-12` adds 96px top+bottom padding; when the device keyboard appears (which can be ~40% of viewport height), the fixed viewport shrinks and the card may not be visible.

**Change**: Wrap the outer `div` with `min-h-svh` (supported in modern browsers, falls back to `min-h-screen`) and ensure it's scrollable. Use `py-8 sm:py-12` to reduce top padding on mobile, allowing the form to remain in view when keyboard appears.

---

### Audit-only pages (proposals, metrics, admin, onboarding step pages)

These pages need to be read and audited during implementation. If they contain fixed-width containers or horizontal flex rows without wrap, add appropriate `flex-wrap` or `flex-col sm:flex-row` responsive classes.

---

## Test Plan

1. **Unit**: Update `tests/navbar.test.tsx` to cover mobile menu open/close state and ARIA attributes.
2. **Viewport smoke**: New `tests/responsive.test.tsx` (vitest + jsdom or Playwright) asserting no horizontal scroll at 390px and 320px on key pages.
3. **Regression**: Run existing test suite — all tests must pass without change.
