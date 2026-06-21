# Data Model: UI Color Compliance

**Feature**: 018-ui-color-compliance | **Date**: 2026-06-20

This feature has no persistent data model or schema changes. It is a purely visual migration of Tailwind CSS class names.

## Conceptual Entities (design token definitions)

These entities represent the canonical color scales mandated by the constitution. They are implemented as Tailwind utility class names, not as runtime data structures.

---

### Color Scale – Neutral (`slate-*`)

Replaces `gray-*` in all neutral surface, border, and text contexts.

| Shade | Tailwind class | Primary use |
|-------|---------------|-------------|
| 50 | `slate-50` | Table header background, page background, row hover tint |
| 100 | `slate-100` | Archived state badge background, subtle secondary backgrounds |
| 200 | `slate-200` | Progress stepper connector (incomplete), divider lines |
| 300 | `slate-300` | Form input border (default) |
| 400 | `slate-400` | Placeholder text, empty-state text, muted labels |
| 500 | `slate-500` | Secondary body text, loading text |
| 600 | `slate-600` | Table header text, nav link text, form label text |
| 700 | `slate-700` | Form label text (stronger), secondary button text |
| 800 | `slate-800` | Section headings |
| 900 | `slate-900` | Primary headings, bold/primary text |

**Scope**: All neutral text, surfaces, borders, and backgrounds in `apps/web`.

**Constraint**: `gray-*` MUST NOT be present after migration (SC-002).

---

### Color Scale – Primary Accent (`indigo-*`)

Replaces `blue-*` for all interactive element default, hover, and focus states.

| Shade | Tailwind class | Primary use |
|-------|---------------|-------------|
| 50 | `indigo-50` | Selected card/row tint, invitation card background |
| 100 | `indigo-100` | Email chip/tag background |
| 200 | `indigo-200` | Invitation card border tint |
| 400 | `indigo-400` | Card hover border (dashboard nav cards) |
| 500 | `indigo-500` | Focus ring on form inputs and interactive elements |
| 600 | `indigo-600` | Primary button background (default), active stepper, text links |
| 700 | `indigo-700` | Primary button hover, current stepper label |
| 800 | `indigo-800` | Email chip/tag text |

**State mapping** (per constitution):
- Default interactive: `indigo-600`
- Hover: `indigo-700`
- Focus ring: `indigo-500`

**Scope**: All primary interactive elements (buttons, links, focus rings, active indicators).

**Constraint**: `blue-*` MUST NOT be present after migration (SC-001).

---

### Color Scale – Error/Destructive (`red-*`)

No changes. Pre-existing and fully compliant with constitution.

| Scope | Notes |
|-------|-------|
| Validation errors | `red-*` retained as-is |
| Destructive actions | `red-*` retained as-is |

---

### Typography – Font Family

| Property | Before | After |
|----------|--------|-------|
| `body` font-family in `globals.css` | `Arial, Helvetica, sans-serif` | `var(--font-sans)` |

The `--font-sans` variable resolves to `var(--font-geist-sans)` (Geist Sans) via the `@theme inline` block already present in `globals.css`. No new font loading is required.

---

## Affected File Inventory

| # | File (relative to `apps/web/`) | Change type |
|---|-------------------------------|-------------|
| 1 | `app/globals.css` | `font-family` fix |
| 2 | `app/layout.tsx` | `gray-*` → `slate-*` |
| 3 | `app/page.tsx` | `gray-*` → `slate-*`, `blue-400` → `indigo-400` |
| 4 | `app/login/page.tsx` | `gray-*` → `slate-*`, `blue-*` → `indigo-*` |
| 5 | `app/register/page.tsx` | `gray-*` → `slate-*`, `blue-*` → `indigo-*` |
| 6 | `app/admin/page.tsx` | `gray-*` → `slate-*`, `blue-*` → `indigo-*` |
| 7 | `app/documents/page.tsx` | `gray-*` → `slate-*`, `blue-*` → `indigo-*` |
| 8 | `app/documents/[id]/page.tsx` | `gray-*` → `slate-*`, `blue-*` → `indigo-*` |
| 9 | `app/search/page.tsx` | `gray-*` → `slate-*`, `blue-*` → `indigo-*` |
| 10 | `app/proposals/page.tsx` | `gray-*` → `slate-*`, `blue-*` → `indigo-*` |
| 11 | `app/metrics/page.tsx` | `gray-*` → `slate-*` |
| 12 | `app/onboarding/layout.tsx` | `gray-*` → `slate-*` |
| 13 | `app/onboarding/invite/page.tsx` | `gray-*` → `slate-*` |
| 14 | `app/onboarding/complete/page.tsx` | `gray-*` → `slate-*`, `blue-*` → `indigo-*` |
| 15 | `app/onboarding/pending/page.tsx` | `gray-*` → `slate-*`, `blue-*` → `indigo-*` |
| 16 | `app/onboarding/profile/page.tsx` | `gray-*` → `slate-*`, `blue-*` → `indigo-*` |
| 17 | `app/onboarding/company/page.tsx` | `gray-*` → `slate-*`, `blue-*` → `indigo-*` |
| 18 | `components/NavBar.tsx` | `gray-*` → `slate-*` |
| 19 | `components/SpaceSelector.tsx` | `blue-500` → `indigo-500` |
| 20 | `components/documents/AddDocumentModal.tsx` | `gray-*` → `slate-*`, `blue-*` → `indigo-*` |
| 21 | `components/onboarding/CompanyForm.tsx` | `gray-*` → `slate-*`, `blue-*` → `indigo-*` |
| 22 | `components/onboarding/CompanySuggestions.tsx` | `gray-*` → `slate-*`, `blue-*` → `indigo-*` |
| 23 | `components/onboarding/InviteForm.tsx` | `gray-*` → `slate-*`, `blue-*` → `indigo-*` |
| 24 | `components/onboarding/ProgressStepper.tsx` | `gray-*` → `slate-*`, `blue-*` → `indigo-*` |

> Note: `globals.css` is an additional file (not one of the 23 component/page files) but is within scope per the spec assumption about CSS custom properties and raw values in `globals.css`.
