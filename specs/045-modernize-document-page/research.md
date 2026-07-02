# Phase 0 Research: Modernize Document Page

## 1. Markdown rendering approach

**Decision**: Use `react-markdown` (v9) with the `remark-gfm` plugin to render
`DocumentVersion.content_markdown` as React elements.

**Rationale**: `react-markdown` parses markdown through the remark/rehype
pipeline and renders directly to React elements — it never uses
`dangerouslySetInnerHTML` and does not enable raw HTML passthrough unless the
`rehype-raw` plugin is explicitly added (which this feature does not add). This
makes it safe by default against script injection from user-authored document
content, satisfying the "no new XSS surface" constraint. `remark-gfm` adds
GitHub-flavored markdown support (tables, strikethrough, task lists), which
matters here because the edge cases call out documents containing tables and
code blocks. No markdown renderer currently exists anywhere in this monorepo
(checked `apps/web` and other apps), so this is a net-new, self-contained
addition.

**Alternatives considered**:
- *Keep raw `<pre>` text, restyle only the container* — rejected per
  clarification: the spec explicitly calls for rendering formatted rich text
  (FR-002).
- *`markdown-it` / `marked` with `dangerouslySetInnerHTML`* — rejected: both
  require manual HTML sanitization (e.g. DOMPurify) to be safe, adding a second
  new dependency and a manual security responsibility that `react-markdown`
  avoids by construction.
- *Server-side rendering to HTML in the API* — rejected: this feature is scoped
  as frontend-only (Assumptions in spec.md); the API already returns raw
  markdown and changing that would be a backend contract change, out of scope.

## 2. Content styling approach

**Decision**: Add `@tailwindcss/typography` as a dev dependency and register it
in `app/globals.css` via Tailwind v4's CSS-first `@plugin "@tailwindcss/typography";`
directive (this project has no `tailwind.config.js` — all Tailwind config is
CSS-based). Apply the `prose prose-slate max-w-none` utility classes to the
`DocumentContent` wrapper, and override the plugin's `--tw-prose-links`,
`--tw-prose-code`, and `--tw-prose-bold` CSS variables in `globals.css` so
rendered links/code use the constitution's `indigo-600`/`indigo-700` accent
instead of the plugin's default blue.

**Rationale**: Hand-mapping ~15 markdown element types (`h1`-`h6`, `p`, `ul`,
`ol`, `li`, `code`, `pre`, `blockquote`, `table`, `a`, `strong`, `em`, `hr`) to
individual Tailwind utility classes via `react-markdown`'s `components` prop
would be significantly more code to write and maintain than one plugin
registration plus a handful of CSS variable overrides, for the same visual
result. The plugin is the standard, low-maintenance solution for this exact
problem in Tailwind projects.

**Note on existing dead code found during research**: `app/search/page.tsx`
already applies a `prose prose-sm max-w-none` class to render LLM chat answers,
but the typography plugin was never installed, so those classes currently have
no effect there. This plan does not touch `search/page.tsx` (out of scope), but
installing the plugin as part of this feature will incidentally make those
existing classes start working — a side effect, not a goal of this feature.

**Alternatives considered**:
- *Hand-styled `components` overrides, no new dependency* — rejected: more code
  for equivalent output; see rationale above.
- *Leave `prose` unset and only restyle the container `<div>`* — rejected: this
  would not give headings/lists/code the distinct visual treatment FR-002 and
  SC-002 require.

## 3. Breadcrumb composition

**Decision**: Reuse the existing `SpaceBreadcrumb` component (`components/spaces/SpaceBreadcrumb.tsx`)
unmodified. Fetch `GET /v1/spaces/{document.space_id}/ancestors` (returns the
ancestor chain, excluding the space itself — same shape `{id, name, slug}` as
the component's `Ancestor` type) and `GET /v1/spaces/{document.space_id}`
(returns the space's own `name`/`id`/`slug`). Pass `[...ancestors, ownSpaceAsAncestor]`
as the component's `ancestors` prop and `document.title` as `currentName`.
`allAccesses` and `onReparented` are omitted (both optional) since the document
page has no reparenting UI.

**Rationale**: Both endpoints already exist, are already tenant-scoped, and are
already used by the Spaces folder browser (feature 044) for the identical
purpose. `SpaceBreadcrumb`'s `ancestors` prop only needs objects shaped like
`{id, name, slug}` — the document's own space fits that shape exactly, so no
prop or component change is needed to render "Root › Ancestor › Ancestor ›
OwnSpace › Document Title" (the last segment via `currentName` is rendered as
plain, non-clickable text, matching FR-008's request for the document title to
be the trail's leaf). This avoids introducing a second breadcrumb component or
coupling the document page to `SpaceBreadcrumb`'s drag-and-drop reparenting
internals (which stay inert here since no drag source sets the component's
expected MIME data on this page).

**Alternatives considered**:
- *New read-only breadcrumb component for documents* — rejected: unnecessary
  duplication when the existing component already renders the exact needed
  shape with zero modification.
- *Extend `SpaceBreadcrumb` with a new "extra crumb" prop* — rejected: not
  needed: concatenating the own-space entry into the existing `ancestors` array
  achieves the same result without changing the component's public API.

## 4. Version history layout

**Decision**: Replace the current `<table>` markup with a vertically stacked
list of version rows, each rendered as a bordered card (visually consistent
with `DocumentTile`'s `bg-white rounded border border-slate-200` treatment),
showing version number, approval date/time, and approver per row. No
pagination or "show more" control, per the resolved clarification (documents
are expected to have few versions).

**Rationale**: A card-per-row list reflows naturally at narrow (360px)
viewports without the column-squeezing/horizontal-scroll problems an HTML
`<table>` has on small screens, directly addressing the mobile edge case
(FR-005) without extra responsive-table logic (e.g. `overflow-x-auto` plus a
min-width table, which still requires horizontal scrolling on small screens).

**Alternatives considered**:
- *Keep `<table>`, only restyle borders/spacing* — rejected: does not resolve
  the mobile-width edge case without introducing horizontal scroll or a
  separate mobile-only layout.
- *Paginate version history* — rejected per clarification (Q3 in spec.md).

## 5. Tag display

**Decision**: Render each document tag as an individual pill/chip
(`inline-flex items-center px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-600`),
replacing the current comma-joined plain-text string.

**Rationale**: Matches the chip/pill treatment already used for document state
(`STATE_STYLES`) on this same page and for state badges on `DocumentTile`,
giving the header consistent visual language per FR-001. Handles the "large
number of tags" edge case by wrapping (`flex flex-wrap gap-1`) instead of
producing one long unbroken string.

**Alternatives considered**:
- *Keep comma-joined string, just recolor it* — rejected: does not address the
  edge case of a header breaking gracefully with many tags, and is visually
  inconsistent with the pill treatment already used one line above it (state
  badge).
