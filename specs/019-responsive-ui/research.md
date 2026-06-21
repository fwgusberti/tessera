# Research: Responsive UI for Smartphones

**Feature**: 019-responsive-ui | **Date**: 2026-06-20

## Decision 1: Mobile Navigation Pattern

**Decision**: Hamburger menu overlay (collapsible panel anchored below the top bar)

**Rationale**: Tessera has 6 navigation targets (Search, Documents, Proposals, Metrics, Admin, Sign out). Bottom tab bars suit 3–5 primary tab flows (native-app paradigm), not SaaS dashboards with variable-length nav. Hamburger + vertical panel is the standard web SaaS pattern (Notion, Linear, GitHub mobile web), requires no new packages, integrates naturally with the existing horizontal NavBar structure, and keeps the desktop layout zero-diff.

**Alternatives considered**:
- **Bottom tab bar**: Better ergonomics for one-handed use, but requires restructuring the root layout (fixed bottom element, content padding), doesn't map cleanly to 6 items, and diverges from the existing nav paradigm. Rejected for scope reasons.
- **Slide-in drawer**: More polished, but requires backdrop overlay, `z-index` management, swipe gesture support, and more complex state. Rejected as over-engineered for this feature's scope.
- **Responsive horizontal wrap**: Allow nav links to wrap to a second row on mobile. Rejected — wrapping is unpredictable and breaks the minimal aesthetic.

## Decision 2: Document Table Responsiveness

**Decision**: Wrap existing `<table>` in `<div className="overflow-x-auto">` AND add `hidden md:table-cell` to the "Confidentiality" column header and cells to reduce column count on mobile.

**Rationale**: The overflow-x-auto wrapper is the lowest-risk change (zero structural change to markup). Hiding the lowest-priority column ("Confidentiality") reduces the table width enough that it fits comfortably at 390px without horizontal scroll while retaining the table semantics. Title and State are the two columns users need most on mobile.

**Alternatives considered**:
- **Card layout per document**: Best UX, but duplicates markup (card + table elements or conditional rendering). Higher complexity and test surface. Can be done as a follow-up enhancement.
- **Stack all columns vertically in cells**: CSS-only `display: block` on `td` — hacky, breaks table semantics.
- **`min-width` on the table + always scroll**: Simplest but always shows a scrollbar, even when not needed. Rejected.

## Decision 3: Keyboard Avoidance on Form Pages

**Decision**: Use `min-h-dvh` on centered form containers (login, register, onboarding layout) combined with `py-8 sm:py-12` to reduce top padding on mobile. Ensure containers are naturally scrollable (no overflow hidden on ancestors).

**Rationale**: `min-h-dvh` uses the dynamic viewport unit that shrinks when the browser UI (address bar + keyboard) appears, preventing the form from being taller than the visible area. Reducing `py-12` to `py-8` on mobile gives back ~32px of vertical space so the submit button stays on-screen for the keyboard. No `position: fixed` sticky footer is needed because all forms have ≤ 5 fields and the button is naturally close to the last field.

**Alternatives considered**:
- **Fixed-position sticky submit button**: Best for long forms. Over-engineered for current 3–5 field forms.
- **`resize-observer` + JS keyboard detection**: Non-standard, fragile, not needed.
- **`vh` units**: Legacy; `100vh` on iOS Safari = full height including browser chrome, causing the classic "100vh taller than viewport" bug. `dvh` resolves this.

## Decision 4: ProgressStepper on Narrow Viewports

**Decision**: Reduce connector `w-12` → `w-6 sm:w-12` and `mx-2` → `mx-1 sm:mx-2`. Keep step labels visible at all sizes but use `text-[10px] sm:text-xs` to allow them to fit.

**Rationale**: At 390px with the existing sizing, the stepper is ~320px wide which fits. At 320px, it overflows by ~16px. Reducing connectors from 48px to 24px and margins from 16px to 8px total reduces the stepper to ~272px — fits at 320px with room to spare.

**Alternatives considered**:
- **Hide labels on mobile**: Loses context for users. Labels are short (Profile, Company, Invite, Done) and meaningful. Rejected.
- **`overflow-x-auto` on stepper**: Allows the stepper to scroll horizontally. Bad UX — users will not know to scroll. Rejected.
- **Vertical stepper on mobile**: Cleanest UX but completely different markup/layout. Out of scope for this feature.

## Decision 5: SpaceSelector Width

**Decision**: Add `w-full` to the `<select>` element's className.

**Rationale**: Native `<select>` elements default to `min-content` width. Without `w-full`, the selector is too narrow to tap on mobile and truncates long space names. This is a one-class fix.

## Decision 6: Testing Strategy

**Decision**: Use Vitest + Testing Library for new component tests (hamburger menu state); add a Playwright test file for viewport smoke tests if Playwright is already configured; otherwise add a vitest test that renders the page at narrow width and asserts no explicit `overflow-x` on the root.

**Rationale**: Checking for actual pixel overflow programmatically via jsdom is not straightforward (jsdom doesn't compute layout). Playwright is the right tool for true viewport testing. If Playwright is not in the project, document the manual validation steps in quickstart.md and leave a placeholder test file.

**Alternatives considered**:
- **Visual regression (Chromatic/Percy)**: Not in the constitution and requires setup. Out of scope.
- **Jest snapshots**: Cannot assert layout/overflow behavior.
