# Data Model: Document Reindex UI

**Feature**: 017-document-reindex-ui | **Date**: 2026-06-20

## Existing Entities (unchanged)

### Document (read-only for this feature)

| Field | Type | Relevance |
|-------|------|-----------|
| `id` | `string` (UUID) | Used in the API call path `/v1/documents/{id}/reindex` |
| `state` | `"ingested" \| "published" \| "archived"` | Gates button visibility — only `"published"` shows the button |
| `owner_user_id` | `string \| null` | Compared against `AuthUser.id` to determine ownership |
| `current_version_id` | `string \| null` | Existing field; not read by this feature |

### AuthUser (read-only for this feature)

| Field | Type | Relevance |
|-------|------|-----------|
| `id` | `string` | Compared against `Document.owner_user_id` |
| `isAdmin` | `boolean` | Bypasses ownership check — admins can reindex any document |

## New UI State (component-local, not persisted)

These fields are added to the `DocumentDetailPage` component's local state:

| State Field | Type | Initial Value | Description |
|-------------|------|---------------|-------------|
| `reindexing` | `boolean` | `false` | `true` while the API call is in-flight or during the 3-second success window |
| `reindexMessage` | `string \| null` | `null` | Set to `"Reindex queued"` on success; cleared after 3 seconds |
| `reindexError` | `string \| null` | `null` | Set to the server error message on failure; cleared on next attempt |

## Visibility Rule

```
canReindex =
  document.state === "published"
  AND (user.id === document.owner_user_id OR user.isAdmin === true)
```

This is a pure derivation from existing entity fields — no new backend fields required.

## State Transitions (UI only)

```
IDLE
 │── user clicks "Reindex" ──► LOADING (reindexing=true, reindexMessage=null, reindexError=null)
 │
LOADING
 ├── API success ──► SUCCESS (reindexing=true, reindexMessage="Reindex queued")
 │                    │
 │                    └── after 3s ──► IDLE (reindexing=false, reindexMessage=null)
 │
 └── API error ──► ERROR (reindexing=false, reindexError="<server message>")
                    │
                    └── user clicks "Reindex" again ──► LOADING
```

Note: `reindexing=true` persists through the SUCCESS state to keep the button disabled during the 3-second message display, then resets to `false` so the user can reindex again.
