# UI Contract: Reindex Button

**Feature**: 017-document-reindex-ui | **Component**: `DocumentDetailPage` (inline, not extracted)

## Rendering Contract

The Reindex button renders inside the existing header actions `<div>` in `apps/web/app/documents/[id]/page.tsx`, conditionally on:

```
document.state === "published" AND (user.id === document.owner_user_id OR user.isAdmin)
```

It does **not** render for:
- `state = "ingested"` or `state = "archived"` (regardless of role)
- Authenticated users who are neither owner nor admin

The Publish button renders for `state = "ingested"` only. These two buttons are **mutually exclusive** by state and never appear simultaneously.

## Rendered Structure

```html
<!-- Reindex button area (conditionally rendered) -->
<div class="flex flex-col items-end gap-1">
  <button
    disabled={reindexing}
    class="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
  >
    {reindexing ? "Reindexing…" : "Reindex"}
  </button>

  <!-- Success message (shown for ~3s after success) -->
  {reindexMessage && <p class="text-xs text-green-600">{reindexMessage}</p>}

  <!-- Error message (shown until next attempt) -->
  {reindexError && <p class="text-xs text-red-600">{reindexError}</p>}
</div>
```

## API Interaction

- **Endpoint**: `POST /v1/documents/{document_id}/reindex`
- **Request body**: `{}` (empty JSON object)
- **Success response**: `{ "queued": true, "document_id": "<uuid>" }` — HTTP 200
- **Error responses**: `403` (not owner/admin), `400` (not published), `404` (not found)

See `specs/016-fix-search-indexing/contracts/reindex-api.md` for the full backend contract.

## Behaviour Contract

| State | Button text | Button enabled | Message shown |
|-------|------------|----------------|---------------|
| IDLE | "Reindex" | Yes | None |
| LOADING (in-flight) | "Reindexing…" | No | None |
| SUCCESS (0–3s) | "Reindexing…" | No | "Reindex queued" (green) |
| IDLE (after 3s auto-dismiss) | "Reindex" | Yes | None |
| ERROR | "Reindex" | Yes | Server error message (red) |

## Accessibility Notes

- The `disabled` attribute on the button provides keyboard and screen-reader accessibility during in-flight / success window.
- No additional ARIA attributes required beyond the native `disabled` semantics (deferred to a future accessibility pass per spec).
