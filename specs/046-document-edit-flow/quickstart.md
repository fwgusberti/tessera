# Quickstart: Document Edit Flow

Prerequisites: local stack running (API + Postgres + web), a company with at
least two users — one with EDITOR (or company admin) role on a space, one
without any membership in that space — and one existing document in that
space with a published or ingested version.

## 1. Migrate the database

```bash
cd apps/api && alembic upgrade head
```
Confirms migration `0014_document_drafts.py` applies cleanly and creates the
`document_drafts` table.

## 2. Split view + live preview (User Story 1)

1. Log in as the EDITOR user, open the document detail page
   (`/documents/{id}`).
2. Confirm an "Edit" entry point is visible.
3. Click it → the edit view opens at `/documents/{id}/edit` with the raw
   Markdown source on the left and a rendered preview on the right,
   pre-filled with the document's current content.
4. Type a Markdown change (e.g., add `## New Heading`) in the left pane.
   **Expected**: the right pane reflects the change within ~1 second, no
   manual refresh (SC-001).
5. Log in as the user with no membership in that space; confirm no Edit
   entry point is shown on the same document, and a direct
   `PUT /v1/documents/{id}/draft` call from that session returns `403`
   (SC-004).

## 3. Autosave protection (User Story 2)

1. As the EDITOR user, in the edit view, type a change and wait ~5s (past
   the autosave debounce).
2. Reload the browser tab without navigating away deliberately.
   **Expected**: reopening `/documents/{id}/edit` restores the autosaved
   content (not the original, unedited content) — confirms
   `GET /v1/documents/{id}/draft` resumption works.
3. Temporarily block the API (e.g., stop the API container) and make
   another edit. **Expected**: a visible save-failure warning appears, and
   the typed content remains present/editable in the pane (FR-008).

## 4. Session finalization creates a version (User Story 3)

1. As the EDITOR user, edit the document, then use the explicit "Done
   editing" action to leave the edit view.
   **Expected**: `GET /v1/documents/{id}/versions` now includes one new
   version containing the edited content, and `GET /v1/documents/{id}`
   shows it as `current_version`.
2. Open the edit view again, make no changes, and leave immediately.
   **Expected**: no new version is created (FR-011) — version count
   unchanged.
3. (Optional, slower) Open the edit view, make a change, then stay idle
   past the inactivity timeout without navigating away.
   **Expected**: the same finalization occurs as in step 1, confirming the
   inactivity-timeout path (FR-010).

## 5. Automated checks

```bash
# Backend
cd apps/api && pytest tests/unit/test_documents_draft_router.py --cov --cov-fail-under=85

# Frontend
cd apps/web && npx vitest run tests/documents-edit.test.tsx
```
