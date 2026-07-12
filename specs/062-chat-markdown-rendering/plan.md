# Implementation Plan: Chat Markdown Rendering

**Branch**: `062-chat-markdown-rendering` | **Date**: 2026-07-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/062-chat-markdown-rendering/spec.md`

## Summary

Render assistant chat answers as formatted markdown instead of raw text, with
the same visual treatment as the document viewer. The document viewer
(`apps/web/components/documents/DocumentContent.tsx`) already renders markdown
with `react-markdown` + `remark-gfm` inside a Tailwind `prose prose-slate`
wrapper. This feature extracts that rendering into a shared
`MarkdownContent` component and uses it in `MessageBubble` for the assistant's
answer, guaranteeing formatting parity (FR-002/SC-002) structurally rather
than by convention. Links in chat answers open in a new tab so the
conversation is never discarded (FR-005). All other chat states (pending,
error, don't-know, citations) are untouched.

This is a **frontend-only, display-only** feature: no API, storage, or answer
generation changes.

## Technical Context

**Language/Version**: TypeScript 5 (frontend, the only layer changed); Python 3.11+ backend untouched

**Primary Dependencies**: Next.js 15 (App Router, client components), React 19, Tailwind CSS 4 with `@tailwindcss/typography` ^0.5; `react-markdown` ^9 and `remark-gfm` ^4 — all already installed and used by `DocumentContent`

**Storage**: N/A — no schema or persistence changes; answers arrive via the existing `POST /v1/chat/ask` response and are rendered client-side only

**Testing**: Vitest + @testing-library/react (jsdom) in `apps/web/tests/`; existing `chat.test.tsx` is the regression guard for all non-answer chat states (US3); new `chat-markdown.test.tsx` covers formatted rendering

**Target Platform**: Web (desktop + responsive mobile), modern evergreen browsers

**Project Type**: Web application (monorepo: `apps/web` Next.js frontend, `apps/api` FastAPI backend, `packages/core` domain)

**Performance Goals**: No perceptible rendering slowdown for chat answers; markdown parsing of typical answers (< a few KB) is sub-millisecond-class client work — no measurable target beyond "no regression"

**Constraints**: Answer generation and the chat API contract are unchanged (spec assumption); formatted content must stay contained inside the `max-w-[85%]` chat bubble (FR-007/SC-004); embedded HTML must never execute (FR-004); the document viewer's visual output must not change

**Scale/Scope**: 1 new shared component, 2 components modified (`MessageBubble`, `DocumentContent` refactored to delegate), 1 new test file; no backend changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | ✅ PASS | No domain code touched; UI-only rendering change. |
| II. Separation of Concerns | ✅ PASS | Spec stays technology-agnostic; all technical decisions live in this plan. |
| III. Data Locality & Consent | ✅ PASS | No client-side persistence introduced; rendering is in-memory only. |
| IV. Test-Driven Development | ✅ PASS | New Vitest suite (`chat-markdown.test.tsx`) written first, covering rendered headings/bold/lists/tables/code, link behavior, HTML neutralization, and containment; existing `chat.test.tsx` and document-viewer suites are regression guards. No Python modules change, so the 85% Python coverage gate is unaffected. |
| V. Quality Gates | ✅ PASS | Ruff/Black not applicable (no Python changes); ESLint/TypeScript apply to the web changes. |
| VI. Tenant Data Isolation | ✅ PASS | See Tenant Isolation section below. No data access of any kind is added or modified. |

### Tenant Isolation

- **Tables accessed**: None. This feature adds no queries, endpoints, or
  data-access paths. The answer text it formats is already delivered to the
  client by the existing, company-scoped `POST /v1/chat/ask` endpoint.
- **Scoping confirmation**: Not applicable — no new or modified backend code.
  The existing chat endpoint's company scoping and its isolation tests remain
  the enforcement proof, unchanged.
- **Isolation tests**: No new data-access path means no new isolation test is
  required.
- **Cross-tenant operations**: None introduced.

**Post-design re-check (after Phase 1)**: ✅ PASS — design artifacts introduce
no new endpoints, tables, or cross-tenant paths; the only security-relevant
surface is client-side HTML neutralization (FR-004), handled by
`react-markdown`'s default behavior of never emitting raw HTML (no
`rehype-raw`), with a test asserting script content is inert.

## Project Structure

### Documentation (this feature)

```text
specs/062-chat-markdown-rendering/
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
├── components/
│   ├── markdown/
│   │   └── MarkdownContent.tsx        # NEW: shared markdown renderer (react-markdown + remark-gfm + prose)
│   ├── documents/
│   │   └── DocumentContent.tsx        # MODIFIED: delegates rendering to MarkdownContent (visual output unchanged)
│   └── chat/
│       ├── MessageBubble.tsx          # MODIFIED: answer text rendered via MarkdownContent; all other states untouched
│       └── ChatInterface.tsx          # UNCHANGED: regression guard only
├── lib/
│   └── types.ts                       # UNCHANGED: ChatTurn/AssistantAnswer already carry the answer string
└── tests/
    ├── chat-markdown.test.tsx         # NEW: US1 + US2 acceptance scenarios and edge cases
    └── chat.test.tsx                  # UNCHANGED: must keep passing (FR-006, US3)

apps/api/                              # UNCHANGED — no backend work in this feature
packages/core/                         # UNCHANGED
```

**Structure Decision**: Web-application layout of the existing monorepo. All
changes are confined to `apps/web`: one new shared component
(`components/markdown/MarkdownContent.tsx`), two modified components
(`MessageBubble`, `DocumentContent`), and one new test file.

## Complexity Tracking

No constitution violations — table intentionally left empty.
