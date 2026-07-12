# Research: Fix Inline Code Rendering

**Feature**: 063-fix-inline-code-rendering | **Date**: 2026-07-11

All Technical Context unknowns were resolved by direct codebase inspection —
no external research agents were required. Findings and decisions below.

## R1. Root cause of the visible backticks

**Decision**: The defect is a CSS decoration, not a parsing or content bug.
`@tailwindcss/typography` ^0.5 (loaded in `apps/web/app/globals.css` via
`@plugin "@tailwindcss/typography"`) styles `.prose` content with:

```css
.prose :where(code):not(...)::before { content: "`"; }
.prose :where(code):not(...)::after  { content: "`"; }
```

Both display surfaces named in the spec render through the shared
`MarkdownContent` component inside a `prose` wrapper — chat
(`MessageBubble.tsx`, `prose prose-sm prose-slate`) and the document viewer
(`DocumentContent.tsx`, `prose prose-slate`) — so both show backticks around
every inline `<code>` element.

**Rationale for the diagnosis**:
- `react-markdown` emits `<code>main</code>` with no backtick characters in
  any text node; the existing `chat-markdown.test.tsx` suite confirms the
  markup layer is clean.
- The typography plugin explicitly sets `content: none` on
  `pre code::before/::after`, which is why fenced code blocks do **not** show
  the decoration — matching the reported symptom exactly (only *inline* code
  is affected).
- The spec's assumption ("backticks are added by the display layer; stored
  content is correct") is confirmed.

**Alternatives considered**: A parser/renderer bug in `react-markdown` or
`remark-gfm` — ruled out by inspecting rendered markup and existing tests; a
content-layer bug (backticks stored in documents / emitted by the assistant)
— ruled out by the same evidence and out of scope per the spec.

## R2. Fix approach

**Decision**: Add one override rule in `apps/web/app/globals.css`, next to the
existing typography customizations (`--tw-prose-code`, `--tw-prose-links`,
`--tw-prose-bold` already live there):

```css
.prose code::before,
.prose code::after {
  content: none;
}
```

**Rationale**:
- **Single point of truth**: every markdown surface uses a `prose` wrapper, so
  one global rule fixes chat and the document viewer identically (FR-003,
  SC-004) and automatically covers any future `prose` surface.
- **Specificity is safe**: the plugin's selector
  (`.prose :where(code):not(:where(...))::before`) has specificity (0,1,1)
  because `:where()` contributes zero; the override `.prose code::before` is
  (0,1,2) and wins unconditionally, regardless of rule order.
- **No collateral damage**: `pre code::before/::after` already have
  `content: none` in the plugin, so the rule is a no-op for code blocks
  (FR-005); the `<code>` element's font, color (`--tw-prose-code`), and
  weight are separate declarations and remain untouched (FR-002).
- **Precedent**: `globals.css` is already the project's home for typography
  overrides, keeping all `prose` customization in one file.

**Alternatives considered**:
1. **Tailwind utility variants on the wrapper**
   (`prose-code:before:content-none prose-code:after:content-none` added to
   the `className` in `MessageBubble` and `DocumentContent`, or appended
   inside `MarkdownContent`): works and is assertable in jsdom, but
   duplicates the fix per call site (or adds class-merging logic to the
   shared component) and silently misses any future `prose` surface that
   bypasses `MarkdownContent`. Rejected in favor of the global rule.
2. **Custom `code` component in `react-markdown`** rendering with a
   `not-prose` class or bespoke styling: heaviest option; re-implements
   styling the typography plugin already provides and risks diverging from
   the surrounding `prose` theme (violates the spec assumption that inline
   code keeps its current styling minus the backticks). Rejected.
3. **Forking/configuring the typography theme** in Tailwind config: Tailwind 4
   CSS-first setup in this repo has no JS config for the plugin; introducing
   one for a two-line override is disproportionate. Rejected.

## R3. Test strategy for pseudo-element content

**Decision**: Two-pronged verification in a new
`apps/web/tests/inline-code-rendering.test.tsx`:

1. **DOM assertions (jsdom)** for every acceptance scenario expressible in
   markup: inline code renders as a `<code>` element (not inside `<pre>`)
   whose surface text contains no backtick characters; multiple snippets in
   one sentence; snippets nested in list items, table cells, headings, and
   bold; empty inline spans produce no stray text; code-block content keeps
   literal backticks; a lone unpaired backtick in prose stays visible as
   typed. Covered for both surfaces (`MessageBubble` and `DocumentContent`).
2. **Stylesheet regression test**: read `apps/web/app/globals.css` from the
   test and assert it contains the `content: none` override targeting
   `.prose code::before` and `.prose code::after`. This is the failing-first
   TDD test for the actual fix, and it guards against the rule being removed.

**Rationale**: jsdom does not compute styles for pseudo-elements, so
`getComputedStyle(el, "::before")` cannot observe the plugin's `content`
value — a pure DOM test can neither fail before the fix nor detect a
regression of it. Reading the stylesheet is the narrowest deterministic check
available in the existing Vitest setup. Human visual confirmation of SC-001–
SC-004 is scripted in `quickstart.md`.

**Alternatives considered**: Browser-based E2E (Playwright/Cypress) asserting
computed pseudo-element content — the only way to assert the rendered pixels,
but the repo has no browser-test infrastructure and introducing it for one
CSS rule is disproportionate; visual snapshot testing — same infrastructure
objection. Both rejected in favor of stylesheet assertion + quickstart visual
check.

## R4. Scope of affected surfaces

**Decision**: Chat answers and the document viewer are the two in-scope
surfaces (per spec FR-003); both are fixed by the single rule. The search
page (`apps/web/app/search/page.tsx`) also uses a `prose` wrapper but renders
the answer as plain text without markdown parsing, so it can never produce an
inline `<code>` element today; the global rule covers it automatically if it
ever adopts markdown rendering. No other `prose` usages exist in `apps/web`.

**Rationale**: Verified by repository-wide search for `prose` and
`MarkdownContent` usages.
