# Research: UI Color Compliance

**Feature**: 018-ui-color-compliance | **Date**: 2026-06-20

## Decision: Tailwind CSS class-name replacement strategy

**Decision**: Direct find-and-replace of Tailwind color class names across 23 source files — no abstraction layer, no CSS custom property indirection.

**Rationale**: Tailwind v4 compiles classes at build time from the source files; a direct textual substitution is sufficient and produces no runtime overhead. Introducing CSS custom properties or a design-token abstraction would exceed the scope of this migration (FR-009: purely visual change).

**Alternatives considered**:
- *CSS custom properties*: Would add indirection and a new abstraction layer; out of scope for this migration, which only migrates existing class names.
- *Component-level token constants*: Would require restructuring components; excessive for a class-name rename.

---

## Decision: Neutral scale mapping

**Decision**: Every `gray-N` class is replaced with `slate-N` (same numeric shade). No shade adjustments needed.

**Rationale**: Tailwind's `slate` scale and `gray` scale share the same visual weight distribution. The spec requires no shade-level redesign — only color-family compliance. The constitution mandates `slate-*` for all neutral surfaces.

**Alternatives considered**: Manually adjusting shades to optimize contrast — rejected; out of scope and would require designer sign-off.

---

## Decision: Primary accent mapping

**Decision**: Every `blue-N` class is replaced with `indigo-N` (same numeric shade), except where the constitution prescribes specific shades:
- Default interactive: `indigo-600`
- Hover state: `indigo-700`
- Focus ring: `indigo-500`

**Rationale**: The existing codebase already follows the 600/700/500 pattern for default/hover/focus — it just uses the wrong family (`blue-*`). A direct name substitution satisfies the constitution without any shade restructuring.

**Alternatives considered**: Using `indigo-500` as the default and `indigo-600` for hover — rejected because existing code uses `600`/`700`/`500` correctly, and the constitution explicitly lists those shades.

---

## Decision: globals.css font-family fix

**Decision**: Replace `font-family: Arial, Helvetica, sans-serif` with `font-family: var(--font-sans)` in the `body` rule.

**Rationale**: `apps/web/app/layout.tsx` already loads Geist Sans into the `--font-geist-sans` CSS variable and assigns it to `--font-sans` via the `@theme inline` block in `globals.css`. The `body` rule currently overrides this with a hardcoded fallback, making Geist Sans ineffective for body text. Fixing it completes the typography setup already in place per the constitution.

**Alternatives considered**: Removing the `body` font override entirely — equivalent outcome, but explicit `var(--font-sans)` is more readable as intent.

---

## Decision: Scope of error/destructive colors

**Decision**: `red-*` classes are fully out of scope; no changes made to them.

**Rationale**: The constitution and spec explicitly exclude the `red-*` error/destructive color family from this migration. No `red-*` classes appear in contexts that would be confused with accent colors. FR-005 mandates preservation.

---

## Findings: Dynamic class names

**Finding**: One instance of a conditional template literal in `proposals/page.tsx` line 66:
```tsx
selected?.id === p.id ? "border-blue-500 bg-blue-50" : "bg-white hover:bg-gray-50"
```
Both branches are static strings visible to the Tailwind compiler; this migrates cleanly to:
```tsx
selected?.id === p.id ? "border-indigo-500 bg-indigo-50" : "bg-white hover:bg-slate-50"
```

**Finding**: No string concatenation or dynamic class construction found beyond the above.

---

## Findings: globals.css custom properties

The `--background` (`#ffffff`) and `--foreground` (`#171717`) CSS variables are plain hex values not derived from a Tailwind color scale. They are not surface colors in the UI component sense; they are low-level primitives used only in the `:root` block and dark mode override. They are out of scope.
