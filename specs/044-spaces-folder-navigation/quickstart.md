# Quickstart: Spaces as Drive-Style Folders (UI)

Validation guide for confirming the feature works end-to-end once
implemented. No new backend/database setup is required — this is a frontend
change reusing existing endpoints (see `contracts/reused-endpoints.md`).

## Prerequisites

- API and Postgres running (`make infra`, `make migrate`, `make api`), with
  at least one company that has: two or more top-level spaces, at least one
  space with a sub-space, and at least one document assigned directly to a
  space that also has a sub-space (to exercise mixed contents).
- Frontend running: `make web`.
- A logged-in user who is `admin` on at least two spaces in the same company
  (to exercise reparenting), and a second user who is `viewer`-only on a
  space (to exercise the permission-denied drag path).

## Scenario 1 — Top-level grid (User Story 1, P1)

1. Navigate to `/spaces`.
2. Expect: only spaces with no accessible parent render as folder tiles in a
   grid; no sub-folders appear.
3. Open a folder tile that has sub-folders.
4. Expect: the URL changes to `/spaces/{id}`, the view now shows only that
   folder's direct sub-folders, and the breadcrumb reads `Root › {folder name}`.
5. Click the `Root` breadcrumb segment.
6. Expect: return to the top-level grid.
7. Copy the URL from step 4 and load it directly in a new tab.
8. Expect: it opens straight into that folder's view with the correct
   breadcrumb (FR-009 deep link).

## Scenario 2 — Mixed contents (User Story 2, P2)

1. Open the folder prepared with both a sub-folder and a directly-assigned
   document.
2. Expect: both the sub-folder tile and the document tile render together,
   visually distinguishable (folder vs. document icon).
3. Open a folder with sub-folders but no documents, then one with documents
   but no sub-folders.
4. Expect: only the items that exist render — no error, no placeholder for
   the missing category.
5. Open a folder with neither.
6. Expect: an empty-state message.
7. Click a document tile.
8. Expect: navigation to that document's existing detail view.

## Scenario 3 — Drag-and-drop reparenting (User Story 3, P3)

1. As the admin user, drag a folder tile and drop it onto a different folder
   tile you are also admin on.
2. Expect: the dragged folder disappears from its old location, the view
   updates immediately, and reloading confirms the new parent persisted
   (`PATCH /v1/spaces/{id}/parent` succeeded).
3. Drag a folder tile and drop it onto itself, then onto one of its own
   sub-folders.
4. Expect: both drops are rejected with a clear message; the hierarchy is
   unchanged.
5. Drag a folder tile and drop it onto the `Root` breadcrumb crumb.
6. Expect: the space becomes a top-level folder (`DELETE /v1/spaces/{id}/parent`).
7. As the viewer-only user, attempt to drag a folder tile you don't have
   admin access to.
8. Expect: either the drag does not start, or the drop is rejected with a
   permission message — no change to the hierarchy.
9. Using keyboard-only navigation (no mouse), open the same folder tile's
   existing "Set parent" action.
10. Expect: the non-drag fallback still works, moving the space without any
    drag gesture (FR-014).

## Expected outcome

All three user stories are independently demonstrable; no backend or
database changes were required to validate any of them.
