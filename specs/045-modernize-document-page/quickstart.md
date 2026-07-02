# Quickstart: Validate Modernize Document Page

## Prerequisites

- API and web app running locally (see repo root / `apps/api` and `apps/web`
  README/dev instructions for the standard local stack).
- A logged-in test user who is a member of a company with:
  - At least one nested space (a space with a parent), containing a document,
    to exercise the breadcrumb trail (FR-008).
  - At least one document with `content_markdown` containing headings, a list,
    a code block, and (if testing GFM) a table, to exercise formatted
    rendering (FR-002).
  - At least one document with three or more approved versions, to exercise
    the version history list (FR-004).
  - At least one document with no approved version yet (`current_version_id`
    is null) and one with no version history, to exercise empty states
    (FR-006).

## Validation scenarios

1. **Modern layout + breadcrumb** — Navigate to a document in a nested space
   (`/documents/{id}`). Confirm the breadcrumb shows "Root › (ancestor
   spaces) › (document's own space) › (document title)" and that clicking any
   ancestor segment navigates to that space (reuses `SpaceBreadcrumb`, see
   `research.md` §3).

2. **Formatted content** — Open a document whose current version contains
   headings, a list, and a code block. Confirm each renders as distinct,
   styled elements (not raw markdown source with `#`/`-`/backticks visible).
   See `contracts/reused-endpoints.md` — content still comes from the same
   `GET /v1/documents/{id}` response, just rendered differently.

3. **Actions unchanged, restyled** — As the document owner (or an admin), on
   an `ingested` document, click Publish; confirm loading → published state
   transition still works and now uses the modernized button style. On a
   `published` document you own/administer, click Reindex; confirm the queued
   message still appears. As a non-owner/non-admin, confirm the Reindex
   control does not render.

4. **Version history** — Open a document with 3+ versions; confirm each
   version's number, approval date/time, and approver render as a scannable
   list (not a raw table) with no pagination control. Open a document with no
   versions; confirm the empty-state message appears instead of an empty list.

5. **Empty/loading/error states** — Open a document with no current content;
   confirm a clear empty-state message replaces the content area. Navigate to
   a non-existent document ID; confirm a "not found" message renders instead
   of a blank/broken page.

6. **Responsive check** — Resize the browser (or use device emulation) to
   360px width. Confirm the header, breadcrumb, actions, content, and version
   history all remain readable with no page-level horizontal scroll (SC-003).

7. **Breadcrumb degradation (defensive)** — If reachable in a test/staging
   environment, simulate a failure of the space/ancestors lookup (e.g., by
   temporarily revoking access or via a network-block test tool) and confirm
   the page still renders the document fully, falling back to a plain
   "← Documents" link instead of crashing (see `contracts/reused-endpoints.md`
   "Failure handling").

## Automated coverage

The scenarios above are covered by (see `plan.md` Project Structure):
- `apps/web/tests/documents-reindex-admin.test.tsx` (extended)
- `apps/web/tests/document-detail-modernized.test.tsx` (new)

Run with the existing frontend test command (`apps/web` `package.json` test
script) — no new test runner or configuration is introduced.
