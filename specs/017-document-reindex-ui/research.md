# Research: Document Reindex UI

**Date**: 2026-06-20 | **Feature**: 017-document-reindex-ui

## Findings

### Decision: No new API endpoint or data layer needed

The `POST /v1/documents/{document_id}/reindex` endpoint was implemented in spec-016 and is already in production. The UI change is purely additive: one existing component modified, one test file extended, one new test file added.

**Rationale**: The endpoint already enforces all auth and state checks server-side. The UI only needs to call it and relay the result.

**Alternatives considered**: Adding a polling mechanism to show when indexing completes. Rejected — the spec explicitly states the "queued" confirmation is sufficient and the operation is async.

---

### Decision: Modify `apps/web/app/documents/[id]/page.tsx` directly (no new component)

The Reindex button pattern is identical to the existing Publish button in the same file (single API call, loading state, inline error display). Extracting to a shared component would add abstraction without benefit.

**Rationale**: Three similar JSX patterns does not justify a premature abstraction. The button logic is co-located with the document detail state it reads (`document.state`, `document.owner_user_id`).

**Alternatives considered**: Extracting a `DocumentActions` component. Rejected — only two actions exist and they are mutually exclusive by document state; there is no shared state or reuse across pages.

---

### Decision: Auth user read via `useAuth()` hook

The document detail page currently does not read the current user. The `useAuth()` hook from `@/lib/auth` is the standard mechanism used across the app (admin page, auth guard). It exposes `user.id` and `user.isAdmin` — exactly what FR-001 and FR-003 require.

**Rationale**: No additional API call needed; the JWT payload is already decoded client-side by the auth context.

**Alternatives considered**: Fetching user profile from API on mount. Rejected — the auth context already has this data.

---

### Decision: 3-second `setTimeout` for success auto-dismiss, managed via `useEffect` cleanup

After success, `reindexMessage` is set and a `setTimeout` clears it and re-enables the button after 3000ms. To prevent state updates on unmounted components (React warning), the timeout is tracked with a ref or via a cleanup function.

**Rationale**: Simple timeout is the lowest-complexity mechanism. `useEffect` cleanup cancels the timer if the user navigates away before it fires.

**Alternatives considered**: A library like `react-hot-toast`. Rejected — adds a dependency for a single use case; the existing pattern in the codebase is inline state-based messages.

---

### Decision: Admin tests in a separate test file

`vi.mock` is hoisted and module-scoped in Vitest. The existing `documents.test.tsx` mocks `useAuth` to return `isAdmin: false`. Overriding this per-describe block requires either `vi.resetModules` + `vi.doMock` (fragile) or a separate file that simply mocks the admin scenario. The project already follows this pattern: `admin.test.tsx` mocks `isAdmin: true` at the file level.

**Rationale**: Separation is idiomatic for this codebase. A new `documents-reindex-admin.test.tsx` is self-contained and readable.

**Alternatives considered**: Using `vi.mocked(useAuth).mockReturnValueOnce(...)` per-test. Rejected — requires the mock factory to return a `vi.fn()` not a plain function, which would require changing the existing mock in `documents.test.tsx`.
