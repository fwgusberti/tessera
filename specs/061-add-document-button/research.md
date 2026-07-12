# Research: Add Document Button in Space

**Feature**: 061-add-document-button | **Date**: 2026-07-11

No `NEEDS CLARIFICATION` items remained in the Technical Context — the codebase already contains every building block. Research consisted of auditing the existing implementation to pick the integration approach.

## Decision 1: Reuse `AddDocumentModal` with a new optional `initialSpaceId` prop

- **Decision**: Extend `apps/web/components/documents/AddDocumentModal.tsx` with an optional `initialSpaceId?: string` prop. The existing reset effect (which clears all fields when `open` becomes false) initializes `spaceId` to `initialSpaceId ?? ""` instead of `""`, so every open from the space page starts with the current space preselected while the Documents page (which passes no prop) keeps its current behavior byte-for-byte.
- **Rationale**: FR-003 requires the exact same capabilities (title, language, confidentiality, content, AI assist) as the existing flow; the modal already implements all of them, including the role-gated AI panel driven by `GET /v1/spaces/{id}/members/me` when `spaceId` is set. Preselecting via prop means the AI-assist effect fires immediately for the current space, matching "AI draft assistance where the user's role permits it" with zero extra code. The user can still change the destination in the dialog (spec assumption), because the `<select>` stays fully functional.
- **Alternatives considered**:
  - *New dedicated modal for the space page* — rejected: duplicates ~300 lines of validated form + AI logic and would drift from the Documents-page flow, violating FR-003.
  - *Controlled `spaceId` from the parent* — rejected: over-generalizes; no caller needs to observe destination changes, and it would force the Documents page to adopt new state.
  - *Prefill via URL query param on the Documents page* — rejected: navigates away from the space, defeating the core value (SC-001) and losing the "appears in grid without reload" requirement (FR-004).

## Decision 2: Role gating from data the space page already loads

- **Decision**: Show the "Add Document" button only when the current folder's `SpaceAccess.effective_role` is `"editor"` or `"admin"`. The page already fetches `GET /v1/spaces` and maps it with `mapSpaceAccesses`, so the role is available as `accesses.find(a => a.space.id === folderId)?.effective_role` — no new request.
- **Rationale**: FR-005/US2 require viewer-role users never see the button. `effective_role` is the platform's inherited-role resolution (direct or via ancestor), computed server-side, so the UI stays consistent with what the API will actually allow. Zero added latency.
- **Alternatives considered**:
  - *Call `GET /v1/spaces/{id}/members/me`* — rejected: an extra request per page view for data already present in the `/v1/spaces` response; also returns only direct membership semantics, while `effective_role` handles inheritance.
  - *Show the button always and rely on the server 403* — rejected: violates FR-005 and SC-004 (viewer must never be offered the action). Server enforcement remains as defense in depth for the stale-page case (US2-AC3), surfaced by the modal's existing `apiError` display.

## Decision 3: Grid update via local state, matching the Documents-page pattern

- **Decision**: In `onCreated`, append the new document to the page's `documents` state only if `document.space_id === folderId` (the user may have changed the destination in the dialog). The existing `isEmpty` derivation (`subfolders.length === 0 && documents.length === 0`) then automatically swaps the empty-state message for the grid.
- **Rationale**: Satisfies FR-004 and SC-003 (visible < 2s, no reload) with no refetch. Mirrors `handleDocumentCreated` on `app/documents/page.tsx`, keeping both entry points behaviorally aligned. The conditional insert covers the "changed destination" edge case exactly as the spec's assumptions describe.
- **Alternatives considered**:
  - *Refetch `GET /v1/documents?space_id=`* — rejected: extra round-trip and a loading flash for information the client already has; the create response returns the full document.
  - *Router refresh / full reload* — rejected: explicitly prohibited by FR-004.

## Decision 4: Spaces offered in the dialog = all accessible spaces

- **Decision**: Pass `accesses.map(a => a.space)` (every space the user can see) as the modal's `spaces` prop, identical to the Documents-page behavior.
- **Rationale**: The spec assumes the dialog behaves exactly as it does today, including free destination choice; server-side role checks reject invalid targets with a clear message shown in the dialog (FR-006). Filtering client-side to editor/admin spaces would change the shared dialog's semantics between entry points — out of scope.
- **Alternatives considered**: *Filter to writable spaces* — rejected as a behavior change to the existing flow (FR-007 says the existing entry point continues unchanged; keeping one semantics for the shared component is the safest reading).

## Decision 5: Testing approach

- **Decision**: New Vitest + Testing Library suite `apps/web/tests/space-add-document.test.tsx`, written before implementation (constitution IV), mocking `@/lib/api` like the existing `space-add.test.tsx` / `documents.test.tsx`. Coverage: button visible for editor/admin, absent for viewer, dialog opens preselected, successful create adds to grid (including from empty state), cancel creates nothing, missing title validates, server error keeps dialog open with content preserved, create-in-other-space does not appear in grid. The existing `documents.test.tsx` continues to pass untouched, proving FR-007.
- **Rationale**: Follows the repo's established frontend test patterns (jsdom, mocked `api`), and each spec acceptance scenario maps to a concrete test case.
- **Alternatives considered**: *E2E browser tests* — none exist in the repo today; introducing a new harness is out of scope for a single-button feature.
