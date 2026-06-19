# Implementation Plan: Add Document — Frontend

**Branch**: `009-add-document-frontend` | **Date**: 2026-06-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/009-add-document-frontend/spec.md`

## Summary

Add an "Add Document" button and modal creation form to the existing Documents list page (`apps/web/app/documents/page.tsx`). When the user submits the form, `POST /v1/documents` is called (already implemented in the API) and the new document row is prepended to the list without a page reload. No backend changes required.

## Technical Context

**Language/Version**: TypeScript 5 (frontend only)

**Primary Dependencies**: Next.js 15.5 (App Router), React 19, Tailwind CSS 4, Vitest 2 + React Testing Library (no new dependencies)

**Storage**: No storage changes — purely frontend state (`useState`)

**Testing**: Vitest 2 + React Testing Library; extend existing `apps/web/tests/documents.test.tsx`

**Target Platform**: Browser (desktop-first)

**Project Type**: Full-stack web application — this change is frontend-only

**Performance Goals**: Modal opens synchronously (no fetch on open); form submission completes within normal API round-trip time

**Constraints**: No new npm dependencies; must not duplicate the `/v1/spaces` fetch; must follow existing Tailwind CSS utility-class styling conventions

**Scale/Scope**: One new component (`AddDocumentModal`), one updated page (`documents/page.tsx`), new test cases in existing test file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | ✅ PASS | No domain entities changed. UI state is purely view-layer; the Document domain entity lives in the backend unchanged. |
| II. Separation of Concerns | ✅ PASS | `AddDocumentModal` is a self-contained UI component; it delegates persistence to `api.post()`; no business logic bleeds into the component. |
| III. Data Locality & Consent | ✅ PASS | No local persistence introduced. Form state is in-memory only; discarded on close. |
| IV. Test-Driven Development | ✅ PASS | New test cases added first (failing), then component implemented. Tests cover happy path, required-field validation, cancel, and API error. |
| V. Quality Gates | ✅ PASS | ESLint + TypeScript strict checks enforced; no new lint surface. |
| Stack — Persistent storage | ✅ N/A | No storage changes. |
| Stack — Caching/transport | ✅ N/A | No Redis or broker usage. |
| Stack — IaC | ✅ N/A | No infrastructure change. |
| Security — Auth | ✅ PASS | Documents page is behind `AuthGuard`; `api.post()` automatically injects the JWT Bearer token. No auth changes required. |
| Security — Secrets | ✅ PASS | No secrets involved. |
| Security — Audit log | ✅ PASS | Audit logging for `document.created` is emitted by the existing backend endpoint handler; no frontend change needed. |
| Docs separation | ✅ PASS | This plan holds all technical decisions. Spec holds WHAT/WHY only. |

**Post-design re-check**: All principles maintained. The implementation is additive (new component + UI wiring) and introduces no architectural novelty.

## Project Structure

### Documentation (this feature)

```text
specs/009-add-document-frontend/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── AddDocumentModal.ts   # Component prop contract
└── tasks.md             # Phase 2 output (/speckit-tasks — not yet created)
```

### Source Code

```text
apps/web/
├── components/
│   └── documents/
│       └── AddDocumentModal.tsx   # NEW: modal form component
├── app/
│   └── documents/
│       └── page.tsx               # MODIFIED: add button + modal wiring
└── tests/
    └── documents.test.tsx         # MODIFIED: add modal test cases
```

**Structure Decision**: Single new component in `components/documents/` following the existing `components/onboarding/` pattern. The page file is the only consumer, so no lib abstraction needed.

## Key Design Decisions

### Modal Pattern

Plain `div`-based overlay (not `<dialog>`) styled with Tailwind CSS. Backdrop click and Escape key both dismiss. `autoFocus` on the Title input when the modal opens. `role="dialog"` + `aria-modal="true"` for accessibility.

### Space List Reuse

`DocumentsPage` already fetches spaces. It passes the `spaces` array to `<AddDocumentModal spaces={spaces} />` as a prop. The modal makes no additional API calls.

### Prepend on Success

After a successful `POST /v1/documents`, the response `document` object is prepended to the `documents` state array in `DocumentsPage`:
```ts
setDocuments(prev => [newDoc, ...prev]);
```
This is conditional on whether a space is currently selected: if the new document's `space_id` matches `selectedSpaceId`, it is prepended; otherwise it is not added (it would not appear in the filtered list anyway).

### Validation

Client-side only before submission. Two required fields: `title` (non-empty after trim) and `spaceId` (non-empty string). Inline error `<p>` elements rendered below each field when invalid. Server errors shown in a banner at the top of the form.

### No New Dependencies

All styling via Tailwind CSS utility classes (already installed). No modal library, no form library, no markdown renderer.

## Complexity Tracking

> No constitution violations requiring justification.
