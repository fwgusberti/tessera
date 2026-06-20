# Quickstart: Validate Document Reindex UI

**Feature**: 017-document-reindex-ui | **Date**: 2026-06-20

## Prerequisites

- Tessera dev stack running: API on `:8000`, web on `:3000`, worker on Celery, Ollama on `:11434`
- At least one published document in a space (use admin bulk reindex or publish a document to get one)
- Two user accounts: one that owns the published document, one that does not
- Admin credentials (to test admin path)

## Start the stack

```bash
bash scripts/dev.sh
```

## Scenario T001 — Owner sees Reindex button on published document

1. Log in as the document owner.
2. Navigate to `/documents`, select a space, click a **published** document.
3. **Expected**: A blue "Reindex" button appears in the top-right header actions area.
4. **Expected**: No "Publish" button is visible (it only shows for ingested docs).

## Scenario T002 — Non-owner does not see Reindex button

1. Log in as a different user who does not own the published document and is not an admin.
2. Navigate to the same published document URL directly (e.g., `/documents/<uuid>`).
3. **Expected**: No "Reindex" button is visible.

## Scenario T003 — Admin sees Reindex button on any published document

1. Log in as an admin user.
2. Navigate to a published document owned by a different user.
3. **Expected**: The "Reindex" button is visible.

## Scenario T004 — Reindex not available on ingested documents

1. Log in as a document owner.
2. Navigate to a document in **ingested** state.
3. **Expected**: No "Reindex" button. The "Publish" button IS visible instead.

## Scenario T005 — Successful reindex shows queued confirmation and re-enables button

1. Log in as the document owner, navigate to a published document.
2. Click the "Reindex" button.
3. **Expected**: Button immediately shows "Reindexing…" and becomes disabled.
4. **Expected**: After API responds, "Reindex queued" appears in green text below the button.
5. **Expected**: After approximately 3 seconds, the message disappears and the button returns to "Reindex" in enabled state.
6. **Expected**: No page reload occurs; document metadata remains on screen.

## Scenario T006 — Re-trigger reindex in same session

1. After T005 completes, click "Reindex" again.
2. **Expected**: The same loading → success → reset cycle repeats.

## Scenario T007 — Test suite passes

```bash
cd apps/web
npx vitest run --reporter=verbose 2>&1 | tail -30
```

**Expected**: All tests pass, including the new "Reindex button" describe blocks in `documents.test.tsx` and `documents-reindex-admin.test.tsx`.
