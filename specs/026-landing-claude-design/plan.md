# Implementation Plan: Landing Page Claude-Chat Design

**Branch**: `026-landing-claude-design` | **Date**: 2026-06-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/026-landing-claude-design/spec.md`

## Summary

Redesign the landing page from a dashboard-with-embedded-chat into a full-page Claude.ai–style chat experience. When no conversation exists the user sees a centered welcome screen with a heading, tagline, starter-prompt chips, and a centered input. Once a conversation starts the layout transitions to a scrollable message history with a sticky-pinned input bar at the bottom. All existing chat logic (`askAssistant`, `MessageBubble`, multi-turn history, loading/error states) is preserved.

## Technical Context

**Language/Version**: TypeScript / Next.js 14 (App Router)

**Primary Dependencies**: React 18, Tailwind CSS v3, Vitest + Testing Library (existing); no new packages required.

**Storage**: None (UI-only feature; in-memory React state already in `ChatInterface`)

**Testing**: Vitest + React Testing Library (`apps/web/tests/chat.test.tsx` + new tests for starter prompts)

**Target Platform**: Web browser, SSR-via-Next.js; minimum supported width 375 px

**Project Type**: Web application (Next.js App Router monorepo, `apps/web`)

**Performance Goals**: Starter-prompt chip click populates input in < 200 ms (pure synchronous React state update).

**Constraints**: No new npm packages; no backend changes; no root layout file restructure.

**Scale/Scope**: Two files changed (`ChatInterface.tsx`, `page.tsx`), one layout file lightly adjusted, two test files updated (existing + new tests for starter prompts). NavBar height treated as a CSS constant (`3.25rem`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | ✅ Pass | Frontend-only change; no domain model touched. |
| II. Separation of Concerns | ✅ Pass | Layout is presentation; chat logic unchanged. |
| III. Data Locality & Consent | ✅ Pass | No local persistence introduced. |
| IV. Test-Driven Development | ✅ Pass | Existing tests updated + new starter-prompt tests written before implementation. |
| V. Quality Gates | ✅ Pass | Ruff/Black are Python-only; ESLint + TS compiler are the JS equivalent and pass when run. |
| UI Design System | ✅ Pass | `slate-*` neutrals, `indigo-600/700/500` accents, Geist font (already loaded via root layout). |
| Security | ✅ Pass | No auth changes; AuthGuard continues to guard the page. |

**No violations; no Complexity Tracking entry required.**

## Project Structure

### Documentation (this feature)

```text
specs/026-landing-claude-design/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── ui-components.md # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (files touched by this feature)

```text
apps/web/
├── app/
│   ├── layout.tsx                    # Minimal change: h-screen flex-col for height propagation
│   └── page.tsx                      # Landing page — remove stats/nav cards, wrap ChatInterface
├── components/chat/
│   └── ChatInterface.tsx             # Core redesign: welcome + conversation layout + starter prompts
└── tests/
    └── chat.test.tsx                 # Update empty-state test; add starter-prompt tests
```

**Structure Decision**: Single web application in `apps/web`. All changes are frontend-only. No new directories or files needed outside `specs/026-landing-claude-design/`.

## Complexity Tracking

> No constitution violations. Section intentionally left blank.
