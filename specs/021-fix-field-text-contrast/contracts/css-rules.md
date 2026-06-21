# CSS Contract: Form Field Text Color

## Scope

Applies to `apps/web/app/globals.css`.

## Rules Added

```css
/* Form element text color — slate-900 for high contrast on light backgrounds */
input:not([type="checkbox"]):not([type="radio"]):not([type="range"]):not([type="color"]):not([type="file"]),
textarea,
select {
  color: var(--color-slate-900);
}

/* Placeholder — slate-400: visible but clearly lighter than entered text */
::placeholder {
  color: var(--color-slate-400);
  opacity: 1; /* Override Firefox default reduced opacity */
}
```

## Invariants

| Rule | Invariant |
|------|-----------|
| Field text | `color: var(--color-slate-900)` = `#0f172a` on all text-bearing inputs, textareas, and selects |
| Placeholder text | `color: var(--color-slate-400)` = `#94a3b8`, distinctly lighter than field text |
| Checkbox / radio | Unaffected — excluded from the selector |
| Disabled fields | Existing `disabled:opacity-50` provides visual de-emphasis; no additional color rule needed |
| Focused fields | Focus ring uses `indigo-500` (existing classes unchanged); text color unchanged |
| Error state | Border and ring color changes (red-*) are unaffected; text color unchanged |

## Non-Goals

- Does not change the `body` foreground variable (`--foreground: #171717`)
- Does not affect table cell text, badge text, or any non-field elements
- Does not introduce `gray-*` or `blue-*` (constitution compliance)
