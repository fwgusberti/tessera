# Implementation Plan: UI Color Compliance

**Branch**: `018-ui-color-compliance` | **Date**: 2026-06-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/018-ui-color-compliance/spec.md`

## Summary

Migrate all 23 component and page files in `apps/web` from the non-compliant `blue-*` / `gray-*` Tailwind color scales to the constitution-mandated `indigo-*` (accent) and `slate-*` (neutral) scales. Also fix `globals.css` to use the `--font-sans` CSS variable instead of the hardcoded `Arial, Helvetica, sans-serif` fallback.

## Technical Context

**Language/Version**: TypeScript 5 / React 19 / Next.js 15.5

**Primary Dependencies**: Tailwind CSS v4 (via `@tailwindcss/postcss`)

**Storage**: N/A — purely visual change; no data model involved

**Testing**: Vitest 2 + Testing Library (React)

**Target Platform**: Browser — Next.js App Router web app

**Project Type**: Web application (frontend only; `apps/web`)

**Performance Goals**: N/A — visual migration, no performance dimension

**Constraints**: No behavior, routing, or accessibility semantics may change; semantic error colors (`red-*`) must be preserved untouched

**Scale/Scope**: 23 source files across `app/` and `components/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | ✅ Pass | No domain logic involved; change is purely presentation |
| II. Separation of Concerns | ✅ Pass | Migration is scoped to the frontend layer only |
| III. Data Locality & Consent | ✅ Pass | No new local storage introduced |
| IV. Test-Driven Development | ✅ Pass | Existing tests remain unchanged; no behavior change |
| V. Quality Gates | ✅ Pass | No Python code; TypeScript linting unaffected by CSS class renaming |
| UI Design System – Neutral | 🚨 Violation (in current code; this feature resolves it) | `gray-*` present in 23 files → migrated to `slate-*` |
| UI Design System – Accent | 🚨 Violation (in current code; this feature resolves it) | `blue-*` present in 23 files → migrated to `indigo-*` |
| UI Design System – Typography | 🚨 Minor violation in `globals.css` → resolved in this feature | `font-family: Arial, Helvetica, sans-serif` overrides `--font-sans` variable; fixed to `var(--font-sans)` |

**Post-design re-check**: All violations are the subject of this migration; no new violations are introduced by this plan.

## Project Structure

### Documentation (this feature)

```text
specs/018-ui-color-compliance/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (affected files)

```text
apps/web/
├── app/
│   ├── globals.css                        # typography font-family fix
│   ├── layout.tsx                         # bg-gray-50 → bg-slate-50
│   ├── page.tsx                           # gray-* → slate-*, blue-400 → indigo-400
│   ├── login/page.tsx                     # gray-*/blue-* → slate-*/indigo-*
│   ├── register/page.tsx                  # gray-*/blue-* → slate-*/indigo-*
│   ├── admin/page.tsx                     # gray-*/blue-* → slate-*/indigo-*
│   ├── documents/page.tsx                 # gray-*/blue-* → slate-*/indigo-*
│   ├── documents/[id]/page.tsx            # gray-*/blue-* → slate-*/indigo-*
│   ├── search/page.tsx                    # gray-*/blue-* → slate-*/indigo-*
│   ├── proposals/page.tsx                 # gray-*/blue-* → slate-*/indigo-*
│   ├── metrics/page.tsx                   # gray-* → slate-*
│   └── onboarding/
│       ├── layout.tsx                     # gray-* → slate-*
│       ├── invite/page.tsx                # gray-* → slate-*
│       ├── complete/page.tsx              # gray-*/blue-* → slate-*/indigo-*
│       ├── pending/page.tsx               # gray-*/blue-* → slate-*/indigo-*
│       ├── profile/page.tsx               # gray-*/blue-* → slate-*/indigo-*
│       └── company/page.tsx               # gray-*/blue-* → slate-*/indigo-*
└── components/
    ├── NavBar.tsx                         # gray-* → slate-*
    ├── SpaceSelector.tsx                  # blue-500 → indigo-500
    ├── documents/
    │   └── AddDocumentModal.tsx           # gray-*/blue-* → slate-*/indigo-*
    └── onboarding/
        ├── CompanyForm.tsx                # gray-*/blue-* → slate-*/indigo-*
        ├── CompanySuggestions.tsx         # gray-*/blue-* → slate-*/indigo-*
        ├── InviteForm.tsx                 # gray-*/blue-* → slate-*/indigo-*
        └── ProgressStepper.tsx            # gray-*/blue-* → slate-*/indigo-*
```

**Structure Decision**: Single `apps/web` Next.js project. All changes are inside `app/` pages and `components/`; no new files created.

## Color Migration Reference

The following class-name substitutions are applied uniformly across all 23 files:

### Neutral scale: `gray-*` → `slate-*`

All numeric shades are preserved; only the color name changes.

| Old class | New class | Usage context |
|-----------|-----------|---------------|
| `bg-gray-50` | `bg-slate-50` | Table header backgrounds, hover row tint, page background |
| `bg-gray-100` | `bg-slate-100` | State badge background (archived), search snippet bg, button secondary bg |
| `bg-gray-200` | `bg-slate-200` | Progress step connector (incomplete) |
| `hover:bg-gray-50` | `hover:bg-slate-50` | Table row hover, secondary button hover |
| `hover:bg-gray-100` | `hover:bg-slate-100` | Search snippet hover, small secondary button hover |
| `border-gray-200` | `border-slate-200` | Card borders, divider lines |
| `border-gray-300` | `border-slate-300` | Form input borders |
| `text-gray-400` | `text-slate-400` | Placeholder / muted / empty-state text |
| `text-gray-500` | `text-slate-500` | Secondary body text |
| `text-gray-600` | `text-slate-600` | Table header text, form label text, nav links |
| `text-gray-700` | `text-slate-700` | Form label text, secondary button text |
| `text-gray-800` | `text-slate-800` | Section headings |
| `text-gray-900` | `text-slate-900` | Primary headings, bold text |
| `hover:text-gray-700` | `hover:text-slate-700` | Nav link hover, muted link hover |
| `hover:text-gray-900` | `hover:text-slate-900` | Nav link hover (stronger) |

### Primary accent: `blue-*` → `indigo-*`

All numeric shades preserved; color name changes. Aligns with constitution's `indigo-600` default / `indigo-700` hover / `indigo-500` focus.

| Old class | New class | Usage context |
|-----------|-----------|---------------|
| `bg-blue-600` | `bg-indigo-600` | Primary button background (default) |
| `bg-blue-50` | `bg-indigo-50` | Selected card/row tint, suggestion card tint |
| `bg-blue-100` | `bg-indigo-100` | Email chip/tag background |
| `hover:bg-blue-700` | `hover:bg-indigo-700` | Primary button hover |
| `border-blue-200` | `border-indigo-200` | Invitation card border tint |
| `border-blue-500` | `border-indigo-500` | Selected state border |
| `border-blue-600` | `border-indigo-600` | Progress stepper current-step indicator |
| `hover:border-blue-400` | `hover:border-indigo-400` | Dashboard quick-nav card hover |
| `text-blue-600` | `text-indigo-600` | Text links, metric highlight, progress connector text |
| `text-blue-700` | `text-indigo-700` | Progress stepper current-step label |
| `text-blue-800` | `text-indigo-800` | Email chip/tag text |
| `text-blue-500` | `text-indigo-500` | Email chip close button |
| `hover:text-blue-700` | `hover:text-indigo-700` | Email chip close button hover |
| `focus:ring-blue-500` | `focus:ring-indigo-500` | Form input focus ring |
| `focus:border-blue-500` | `focus:border-indigo-500` | Form input focus border |

### globals.css typography fix

```css
/* Before */
font-family: Arial, Helvetica, sans-serif;

/* After */
font-family: var(--font-sans);
```

## Complexity Tracking

No constitution violations are introduced by this plan. All violations noted above are pre-existing in the current codebase and are the explicit subject of this feature.

## Risks & Edge Cases

| Risk | Mitigation |
|------|-----------|
| `STATE_STYLES` object in `documents/page.tsx` and `documents/[id]/page.tsx` contains `bg-gray-100 text-gray-600` for `archived` state | Migrate to `bg-slate-100 text-slate-600`; error states (`red-*`) untouched |
| Dynamically constructed class names via string interpolation | Audit found one: `proposals/page.tsx` line 66 — conditional template literal; migrated statically since both branches are visible |
| `globals.css` font-family override | Fix to `var(--font-sans)` so Geist Sans loads per constitution |
| `--foreground`/`--background` CSS custom properties | Already use plain hex; not color-scale tokens; left unchanged |
| Modal overlay (`AddDocumentModal`) | Standard Tailwind bg-white overlay; no layered color issues |
