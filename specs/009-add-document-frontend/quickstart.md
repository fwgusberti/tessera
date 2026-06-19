# Quickstart Validation Guide: Add Document — Frontend

**Feature**: 009-add-document-frontend | **Date**: 2026-06-18

## Prerequisites

- Tessera dev stack running (`make dev` or `make api` + `make web` from repo root).
- At least one user registered and onboarded.
- At least one Space created (needed for the space selector to have options).
- Browser open at `http://localhost:3000/documents`.

## Validation Scenarios

### S-1: Happy path — create a document

1. Log in and navigate to **Documents**.
2. Confirm "Add Document" button is visible in the page header area.
3. Click "Add Document" → modal dialog appears over the document list.
4. Fill in:
   - Title: `Test Document`
   - Space: pick any available space
   - Language: `pt-BR` (default)
   - Confidentiality: `internal` (default)
   - Content: `# Hello\n\nThis is a test document.`
5. Click **Save**.
6. **Expected**: Modal closes. The document list now shows a new row for "Test Document" with an `ingested` badge at the top. No page reload occurred.

---

### S-2: Required-field validation

1. Click "Add Document" → modal opens.
2. Leave Title blank. Click **Save**.
3. **Expected**: Inline error under the Title field. Form not submitted (no network request fired).
4. Fill in Title. Leave Space unselected. Click **Save**.
5. **Expected**: Inline error under the Space field. Form not submitted.

---

### S-3: Cancel dismisses without saving

1. Click "Add Document" → modal opens.
2. Type something in the Title field.
3. Click **Cancel**.
4. **Expected**: Modal closes. Document list is unchanged (no new row).
5. Reopen the modal → form fields are reset to their defaults.

---

### S-4: Escape key dismisses

1. Click "Add Document" → modal opens.
2. Press **Escape**.
3. **Expected**: Modal closes. Document list unchanged.

---

### S-5: No spaces available

1. (If possible in the test environment, remove all spaces, or test with a user who has no spaces.)
2. Click "Add Document" → modal opens.
3. **Expected**: Space selector is empty or shows "No spaces available" message. Save button should be disabled or validation should prevent submission.

---

### S-6: API error handling

1. (Simulate a network error by stopping the API server mid-session, or use browser DevTools → Network → block `POST /v1/documents`.)
2. Fill form with valid data. Click **Save**.
3. **Expected**: Modal stays open. A red error banner appears at the top of the form describing the failure. The user can correct and retry.

---

## Running the Test Suite

```bash
cd apps/web
npm run test -- --run
```

All tests in `tests/documents.test.tsx` must pass, including the new describe blocks for the "Add Document" modal.
