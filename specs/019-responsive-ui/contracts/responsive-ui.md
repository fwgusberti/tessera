# Responsive UI Contract

**Feature**: 019-responsive-ui | **Date**: 2026-06-20

This contract defines the observable behavior each component MUST satisfy after this feature is implemented. It is the validation target for QA and the test acceptance criteria.

---

## Global Rules

| Rule | Requirement |
|------|-------------|
| **No horizontal overflow** | At viewport widths 320px, 375px, 390px, and 430px, `document.documentElement.scrollWidth` MUST equal `window.innerWidth` on all app pages |
| **No design token change** | The `slate-*`, `indigo-*`, `red-*` color classes and Geist/Inter fonts MUST remain unmodified. No `blue-*` or `gray-*` classes may be introduced |
| **Desktop unchanged** | At viewport width 1024px and 1440px, the visual output of all pages MUST be identical to the pre-feature baseline |
| **Touch targets** | All `<button>`, `<a>`, and `<select>` elements visible on mobile MUST have an effective tap area of at least 44×44px |

---

## Component Contracts

### NavBar

| Scenario | Expected behavior |
|----------|------------------|
| Viewport < 768px | Hamburger button (`aria-label="Open menu"`) is visible; nav links are hidden |
| Viewport ≥ 768px | Hamburger button is hidden; nav links are visible in a horizontal row |
| Hamburger pressed | Mobile menu overlay opens below the top bar; all nav links are visible vertically |
| Nav link pressed in mobile menu | Menu closes; target page loads |
| Escape key pressed while menu open | Menu closes |
| Menu overlay dismissible | Clicking/tapping outside the menu panel closes it |
| Hamburger button touch target | ≥ 44×44px effective tap area |

### SpaceSelector

| Scenario | Expected behavior |
|----------|------------------|
| Viewport < 768px | Select element fills available container width (`w-full`) |
| Long space names | Truncated within the select; no horizontal overflow |

### ProgressStepper

| Scenario | Expected behavior |
|----------|------------------|
| Viewport 320px | All 4 step circles and 3 connectors fit within the viewport width without horizontal scroll |
| Step labels | Visible and readable at all viewport widths ≥ 320px |
| Current step | Visually distinct (`indigo-100` background, `indigo-600` border) on all viewports |

### AddDocumentModal

| Scenario | Expected behavior |
|----------|------------------|
| Viewport < 640px | Language and Confidentiality selects stack vertically (single column) |
| Viewport ≥ 640px | Language and Confidentiality selects side-by-side (two columns) |
| Viewport 390px | Modal is fully visible; no content clipped by screen edges |
| Viewport 320px | Modal scrollable if content exceeds screen height; no horizontal overflow |

### Documents List Page

| Scenario | Expected behavior |
|----------|------------------|
| Viewport < 768px | "Confidentiality" column is hidden; Title and State columns are visible |
| Viewport < 768px | Table fits within viewport; horizontal scroll wrapper present but not triggered |
| Viewport ≥ 768px | All 3 columns (Title, State, Confidentiality) visible — unchanged |

### Document Detail Page

| Scenario | Expected behavior |
|----------|------------------|
| Viewport < 768px | Document title and action buttons (Publish / Reindex) stack vertically |
| Viewport ≥ 768px | Title on the left, action buttons on the right (unchanged) |
| Long document titles | Wrap within the column; no overflow |

### Login and Register Pages

| Scenario | Expected behavior |
|----------|------------------|
| Viewport 390px, keyboard visible | Submit button remains reachable by scrolling; not hidden behind keyboard |
| Viewport 390px | Form card fills available width below `max-w-sm` cap |
| Error messages | Visible within the viewport without scrolling on 390px |

### Onboarding Layout

| Scenario | Expected behavior |
|----------|------------------|
| Viewport < 640px | White card inner padding is 16px (p-4); form fields have comfortable input width |
| Viewport ≥ 640px | White card inner padding is 32px (p-8) — unchanged from today |
| ProgressStepper visible on all onboarding pages | Fits within 320px viewport |

---

## Out-of-Scope Behaviors (explicitly not contracted)

- Landscape smartphone orientation
- Tablet viewport (768px–1023px) — desktop mode applies by default
- Proposals, Metrics, Admin pages — these are audited but have no explicit contract beyond the global no-horizontal-overflow rule
