# Research: Fix Field Text Contrast

## Root Cause

**Decision**: The contrast issue stems from missing explicit text-color declarations on
`<input>`, `<select>`, and `<textarea>` elements.

**Rationale**: Tailwind CSS v4 ships a preflight (`@import "tailwindcss"`) that resets
box-sizing, borders, margins, and padding globally but does **not** add `color: inherit`
to form elements. Modern browsers typically provide user-agent stylesheets that can render
form elements with a system color (e.g., `color: -internal-light-dark(black, white)`) that
doesn't reliably pick up the `color` set on `body`. When `globals.css` sets
`color: var(--foreground)` on `body`, this propagates to regular elements but not
consistently to form elements in all browsers and rendering contexts.

**Verification**: Every `<input>`, `<select>`, and `<textarea>` in the codebase carries
only `text-sm` (a `font-size` class) in its `className` — no `text-*` color class is
present anywhere in the ~9 affected components.

**Alternatives considered**:

| Alternative | Rejected because |
|-------------|------------------|
| Add `text-slate-900` to each of ~20 individual elements | Tedious, error-prone, and doesn't protect future fields added without the class |
| Use `color: inherit` from body (`#171717`) | `#171717` is not a `slate-*` color — constitution violation |
| Create a shared `<Field>` wrapper component | Over-engineering; the spec explicitly scopes the fix to CSS |

## Tailwind v4 CSS Custom Properties

After `@import "tailwindcss"`, the full Tailwind theme is available as CSS custom
properties. The relevant variables for this fix:

```
--color-slate-900   (#0f172a)  → field text
--color-slate-400   (#94a3b8)  → placeholder text
--color-slate-500   (#64748b)  → disabled text (via existing opacity-50, no extra rule needed)
```

## Selector Scope

The CSS rule must cover text-bearing form elements only:

- `input:not([type="checkbox"]):not([type="radio"]):not([type="range"]):not([type="color"]):not([type="file"])` — excludes non-text controls
- `textarea`
- `select`
- `::placeholder` pseudo-element — targets placeholder text in inputs and textareas

## Constitution Alignment

Using `var(--color-slate-900)` (Tailwind v4 variable for `slate-900`) is fully
constitution-compliant: it references the canonical `slate-*` neutral scale for text.

## No Data-Model Changes

This is a pure CSS presentation fix. No entities, no API contracts, no backend changes.
