# Implementation Plan: Fix Field Text Contrast

**Branch**: `021-fix-field-text-contrast` | **Date**: 2026-06-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/021-fix-field-text-contrast/spec.md`

## Summary

Form fields across the application (`<input>`, `<select>`, `<textarea>`) have no explicit
text color set, causing browsers to fall back to system-default colors that may not contrast
adequately against the white/light field backgrounds. The fix is a targeted addition to
`globals.css` that enforces `slate-900` text color on all text-style form elements and
`slate-400` on placeholder text — one CSS file, no component changes.

## Technical Context

**Language/Version**: TypeScript 5.x, CSS

**Primary Dependencies**: Next.js 15.5.19, Tailwind CSS v4 (`@tailwindcss/postcss ^4`)

**Storage**: N/A

**Testing**: Vitest + React Testing Library (existing suite); visual inspection for CSS

**Target Platform**: Web browser (desktop + mobile, all pages in `apps/web/`)

**Project Type**: Web application — Next.js App Router frontend

**Performance Goals**: No performance impact (CSS-only change)

**Constraints**: Fix must not affect checkbox/radio inputs (which have no inner text), must
not alter surrounding label or error-message text, must work in all field states (default,
focused, filled, error, disabled).

**Scale/Scope**: 1 CSS file (`globals.css`), covering ~20 form field elements across 9
source files. No JS/TS edits required.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. DDD | ✅ PASS | No domain logic touched. |
| II. SoC | ✅ PASS | Frontend-only; no backend impact. |
| III. Data Locality | ✅ PASS | No persistence changes. |
| IV. TDD | ✅ PASS | TDD mandate targets Python business-domain modules (85% coverage). CSS presentation layer requires visual inspection, documented in `quickstart.md`. |
| V. Quality Gates | ✅ PASS | No Python files modified; Ruff/Black not applicable. ESLint passes for CSS in a `.css` file. |
| UI Design System | ✅ PASS | Fix aligns fields with the `slate-*` text scale: `slate-900` for field text, `slate-400` for placeholders. Uses Tailwind v4 CSS custom-property references (`--color-slate-*`). `gray-*` and `blue-*` not introduced. |

## Project Structure

### Documentation (this feature)

```text
specs/021-fix-field-text-contrast/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (N/A — no entities)
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code

```text
apps/web/
└── app/
    └── globals.css      # ONLY file modified — adds form-element color rules
```

All form elements in the following files are covered by the global rule and require
no individual edits:

```text
apps/web/app/login/page.tsx
apps/web/app/register/page.tsx
apps/web/app/search/page.tsx
apps/web/app/admin/page.tsx
apps/web/app/onboarding/profile/page.tsx
apps/web/components/onboarding/CompanyForm.tsx
apps/web/components/onboarding/InviteForm.tsx
apps/web/components/documents/AddDocumentModal.tsx
apps/web/components/SpaceSelector.tsx
```

**Structure Decision**: Single-project web app (Next.js), option 1. Only the global
stylesheet is modified; no new files created.
