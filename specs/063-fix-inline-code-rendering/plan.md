# Implementation Plan: Fix Inline Code Rendering

**Branch**: `063-fix-inline-code-rendering` | **Date**: 2026-07-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/063-fix-inline-code-rendering/spec.md`

## Summary

Inline code snippets (`` `main` ``) render with visible backtick characters in
chat answers and the document viewer. Root cause: the backticks are **not** in
the markup or the content — `react-markdown` correctly emits `<code>main</code>`
— they are injected by the `@tailwindcss/typography` plugin, whose `.prose`
styles add `content: "`"` via `code::before` / `code::after` pseudo-elements.
Both surfaces render through the shared `MarkdownContent` component
(`apps/web/components/markdown/MarkdownContent.tsx`, feature 062) inside a
`prose` wrapper, so both show the decoration.

Fix: a single CSS override in `apps/web/app/globals.css` — where the project's
typography customizations (`--tw-prose-code`, `--tw-prose-links`) already live —
setting `content: none` on `.prose code::before/::after`. This removes the
decorative backticks on every `prose` surface at once, leaves the `<code>`
element's monospace/color styling untouched (US2), and cannot affect literal
backticks that are part of the content, because those are real text nodes, not
pseudo-elements (US3). No component, API, storage, or content change.

This is a **frontend-only, CSS-only** fix.

## Technical Context

**Language/Version**: TypeScript 5 / CSS (frontend, the only layer changed); Python 3.11+ backend untouched

**Primary Dependencies**: Next.js 15 (App Router), React 19, Tailwind CSS 4 with `@tailwindcss/typography` ^0.5 (source of the pseudo-element backticks), `react-markdown` ^9 + `remark-gfm` ^4 — all already installed; no dependency changes

**Storage**: N/A — display-only; stored markdown and chat answers are already correct (spec assumption confirmed: backticks come from the display layer)

**Testing**: Vitest + @testing-library/react (jsdom) in `apps/web/tests/`. jsdom does not compute pseudo-element content, so verification is two-pronged: (1) DOM tests asserting inline code renders as a `<code>` element whose text contains no backtick characters (guards the markup layer, US1/US3 scenarios), and (2) a stylesheet regression test asserting `globals.css` contains the `content: none` override for `.prose code::before/::after` (guards the CSS layer). Visual confirmation via quickstart.

**Target Platform**: Web (desktop + responsive mobile), modern evergreen browsers

**Project Type**: Web application (monorepo: `apps/web` Next.js frontend, `apps/api` FastAPI backend, `packages/core` domain)

**Performance Goals**: None applicable — a static CSS rule; zero runtime cost

**Constraints**: All other markdown elements must render exactly as today (FR-005) — the override touches only the two pseudo-elements; code-block styling is unaffected because typography already sets `content: none` on `pre code::before/::after` (the rule is a no-op there). Chat and document viewer must stay identical (FR-003/SC-004) — guaranteed structurally: one shared component, one global rule.

**Scale/Scope**: 1 CSS file modified (`globals.css`), 1 test file added; no component, backend, or schema changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | ✅ PASS | No domain code touched; presentation-layer CSS only. |
| II. Separation of Concerns | ✅ PASS | Spec describes only visible behavior; all technical detail (typography plugin, pseudo-elements) lives here. |
| III. Data Locality & Consent | ✅ PASS | No client-side persistence introduced or modified. |
| IV. Test-Driven Development | ✅ PASS | New Vitest suite written first and confirmed failing (stylesheet assertion fails before the CSS change), then the override is added. DOM-level tests cover every acceptance scenario expressible in jsdom; existing `chat-markdown.test.tsx` and document suites are the FR-005 regression guard. No Python modules change, so the 85% Python coverage gate is unaffected. |
| V. Quality Gates | ✅ PASS | Ruff/Black not applicable (no Python changes); ESLint/TypeScript/Vitest apply to the web changes. |
| VI. Tenant Data Isolation | ✅ PASS | See Tenant Isolation section below. No data access of any kind is added or modified. |

### Tenant Isolation

- **Tables accessed**: None. This fix adds no queries, endpoints, or
  data-access paths; it changes one static CSS file.
- **Scoping confirmation**: Not applicable — no new or modified backend code.
  Content reaching the affected components is already delivered by the
  existing company-scoped chat and document endpoints, unchanged.
- **Isolation tests**: No new data-access path means no new isolation test is
  required.
- **Cross-tenant operations**: None introduced.

**Post-design re-check (after Phase 1)**: ✅ PASS — design artifacts confirm
the change surface is one CSS rule plus tests; no new endpoints, tables,
dependencies, or cross-tenant paths.

## Project Structure

### Documentation (this feature)

```text
specs/063-fix-inline-code-rendering/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── ui.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/web/
├── app/
│   └── globals.css                        # MODIFIED: add `.prose code::before/::after { content: none; }`
│                                          #   next to the existing --tw-prose-* typography customizations
├── components/
│   ├── markdown/
│   │   └── MarkdownContent.tsx            # UNCHANGED: shared renderer already emits correct <code> markup
│   ├── documents/
│   │   └── DocumentContent.tsx            # UNCHANGED: document-viewer surface (prose prose-slate)
│   └── chat/
│       └── MessageBubble.tsx              # UNCHANGED: chat surface (prose prose-sm prose-slate)
└── tests/
    ├── inline-code-rendering.test.tsx     # NEW: US1/US2/US3 scenarios (DOM assertions + stylesheet regression test)
    └── chat-markdown.test.tsx             # UNCHANGED: must keep passing (FR-005 regression guard)

apps/api/                                  # UNCHANGED — no backend work in this feature
packages/core/                             # UNCHANGED
```

**Structure Decision**: Web-application layout of the existing monorepo. The
production change is confined to a single file, `apps/web/app/globals.css`;
one new test file is added under `apps/web/tests/`.

## Complexity Tracking

No constitution violations — table intentionally left empty.
