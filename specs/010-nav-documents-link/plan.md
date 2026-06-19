# Implementation Plan: Documents Navigation Link

**Branch**: `010-nav-documents-link` | **Date**: 2026-06-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/010-nav-documents-link/spec.md`

## Summary

Add a "Documents" link to the NavBar so users can reach `/documents` in one click. The existing `/documents` page and its auth guard are already functional; only `NavBar.tsx` and its test file require changes.

## Technical Context

**Language/Version**: TypeScript 5 (frontend only)

**Primary Dependencies**: Next.js 15.5 (App Router), React 19, Tailwind CSS 4, Vitest 2 + React Testing Library (no new dependencies)

**Storage**: N/A — no data storage changes

**Testing**: Vitest 2 + React Testing Library; extend existing `apps/web/tests/navbar.test.tsx`

**Target Platform**: Browser (desktop-first)

**Project Type**: Full-stack web application — this change is frontend-only

**Performance Goals**: Synchronous link render; no fetch on render

**Constraints**: No new npm dependencies; follow existing Tailwind CSS utility-class styling

**Scale/Scope**: One line added to one component, one assertion added to one test

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | ✅ PASS | No domain model touched. Link is pure view-layer. |
| II. Separation of Concerns | ✅ PASS | NavBar is a presentational component; no business logic involved. |
| III. Data Locality & Consent | ✅ PASS | No local persistence introduced. |
| IV. Test-Driven Development | ✅ PASS | Failing test assertion added first; then component updated. |
| V. Quality Gates | ✅ PASS | ESLint + TypeScript strict checks apply; no new lint surface. |
| Stack — Persistent storage | ✅ N/A | No storage changes. |
| Stack — Caching/transport | ✅ N/A | No Redis or broker usage. |
| Stack — IaC | ✅ N/A | No infrastructure change. |
| Security — Auth | ✅ PASS | `/documents` page uses existing AuthGuard; nav link rendered unconditionally (consistent with Admin, Search, etc.). |
| Security — Secrets | ✅ PASS | No secrets involved. |
| Security — Audit log | ✅ PASS | No state-changing action; read-only navigation. |
| Docs separation | ✅ PASS | HOW is in this plan; WHAT/WHY is in spec.md. |

**Post-design re-check**: All principles maintained. The change is purely additive: one `<a>` element in an existing component.

## Project Structure

### Documentation (this feature)

```text
specs/010-nav-documents-link/
├── plan.md              # This file
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (files touched)

```text
apps/web/
├── components/
│   └── NavBar.tsx           # Add <a href="/documents">Documents</a>
└── tests/
    └── navbar.test.tsx      # Add assertion for Documents link
```

## Phase 0: Research

No unknowns. All decisions follow directly from the existing codebase:

| Decision | Rationale |
|----------|-----------|
| Insert Documents link after Search (position 2nd) | Documents is the primary content feature; Search is the discovery tool that naturally precedes it. Preserves Admin last. Final order: Search → Documents → Proposals → Metrics → Admin. |
| Link always visible (not auth-gated in nav) | Consistent with Admin, Search, Proposals, Metrics — all rendered unconditionally. Auth enforcement lives in the page's existing AuthGuard. |
| `<a href="/documents">` (plain anchor, not Next.js `<Link>`) | Consistent with all other NavBar links which use plain `<a>` tags. |
| No active-state styling | Not present anywhere in NavBar; no precedent to follow. |

## Phase 1: Design

### No Data Model Changes

No entities, schemas, or API contracts are affected.

### NavBar Change

Add the following element inside the `<div className="flex items-center gap-4">` block in `apps/web/components/NavBar.tsx`, after the Search link and before the Proposals link:

```tsx
<a href="/documents" className="text-sm text-gray-600 hover:text-gray-900">
  Documents
</a>
```

### Test Change

In `apps/web/tests/navbar.test.tsx`, add this assertion to the "renders navigation links" test:

```tsx
expect(screen.getByRole("link", { name: /documents/i })).toBeInTheDocument();
```
