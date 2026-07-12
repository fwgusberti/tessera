# Quickstart: Add Document Button in Space

**Feature**: 061-add-document-button

Validation guide proving the feature end-to-end. Contracts: [contracts/ui-and-api.md](./contracts/ui-and-api.md) · Data model: [data-model.md](./data-model.md)

## Prerequisites

- Repo dependencies installed (`npm install` in `apps/web`; API deps via the project's usual setup).
- Running stack for manual validation: API (`apps/api`) against PostgreSQL, and the web app:

```bash
# terminal 1 — API (project's standard invocation)
# terminal 2 — web
cd apps/web && npm run dev
```

- Two test users in the same company with different roles in one space: one **editor/admin**, one **viewer** (assignable via the space members page or seed data).

## Automated validation

```bash
cd apps/web
npx vitest run tests/space-add-document.test.tsx   # new suite for this feature
npx vitest run tests/documents.test.tsx            # regression: global entry point unchanged (FR-007)
npx vitest run                                     # full web suite
```

**Expected**: all pass. The new suite covers: button gating by role, dialog preselection, create-appends-to-grid (including from the empty state), cancel, title validation, server-error preservation, and creation into a different space not polluting the current grid.

## Manual validation scenarios

### US1 — create a document from a space page (P1)

1. Sign in as the **editor** user and navigate to a space page (`/spaces/<id>`).
2. **Expect**: an "Add Document" button next to "Add Space".
3. Click it. **Expect**: the Add Document dialog opens with the current space already selected in the Space dropdown (FR-002).
4. Enter a title, save. **Expect**: dialog closes; the document appears in the grid immediately, no page reload (FR-004, SC-003).
5. On an **empty** space, repeat: **Expect** the "no sub-folders or documents" message is replaced by the grid (US1-AC5).
6. Reopen the dialog and cancel/Escape. **Expect**: nothing created, page unchanged (US1-AC3).
7. Reopen and save with an empty title. **Expect**: "Title is required" validation, nothing created (US1-AC4).

### US2 — permission-aware visibility (P2)

1. Sign in as the **viewer** user, open the same space page.
2. **Expect**: no "Add Document" button (FR-005, SC-004).
3. Stale-page check: as the editor, open the dialog; in another session demote that user to viewer; save. **Expect**: a clear error in the dialog, entered content preserved, no document created (US2-AC3, FR-006).

### Edge cases

- Change the destination space inside the dialog before saving: **Expect** creation succeeds and the document does **not** appear in the current space's grid (spec assumption).
- Stop the API and save: **Expect** the dialog stays open with an error and the form content intact (FR-006).
- Global Documents page (`/documents`): **Expect** its Add Document flow works exactly as before, with no space preselected (FR-007).

## Success criteria mapping

| Criterion | Validated by |
|-----------|--------------|
| SC-001 (create without leaving the page) | US1 steps 1–4 |
| SC-002 (lands in preselected space) | US1 step 4 + destination-change edge case |
| SC-003 (visible ≤ 2s, no refresh) | US1 step 4 (local state insert) |
| SC-004 (viewer never sees the action) | US2 steps 1–2 + gating tests |
