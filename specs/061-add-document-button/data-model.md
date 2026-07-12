# Data Model: Add Document Button in Space

**Feature**: 061-add-document-button | **Date**: 2026-07-11

No new entities, fields, tables, or migrations. The feature reuses existing entities exactly as they are; this document records how each one participates.

## Entities (existing, unchanged)

### Document

Created through the existing `POST /v1/documents` flow. Frontend type: `Document` in `apps/web/lib/types.ts`.

| Field | Type | Role in this feature |
|-------|------|----------------------|
| `id` | UUID | React list key in the grid |
| `space_id` | UUID | Compared to the current folder id to decide whether the new document joins the grid |
| `title` | string | Required; validated non-empty in the dialog (US1-AC4) |
| `language` | string | Set in dialog (default `pt-BR`) |
| `confidentiality` | enum | Set in dialog (default `internal`) |
| `state` | enum | Returned by the API; rendered by the grid tile |

**Validation rules**: unchanged — title required (client + server), destination space required, all other rules enforced server-side as today (spec edge case: "no new rules").

### Space

The folder page's current space is the preselected destination. Frontend type: `Space` in `apps/web/lib/types.ts`. Only `id` (preselection, grid membership check) and `name` (dialog `<select>` label) are used.

### SpaceAccess (view model)

`{ space, effective_role, is_direct }`, produced by `mapSpaceAccesses` from `GET /v1/spaces`. Drives the two derived values this feature adds:

- `currentRole = accesses.find(a => a.space.id === folderId)?.effective_role`
- `canAddDocument = currentRole === "editor" || currentRole === "admin"` (FR-001, FR-005)

### Space role

Existing 3-tier enum `viewer | editor | admin` (`SpaceRole` in `apps/web/lib/types.ts`). No new roles or permissions (spec assumption). Server-side, `can_write_document` remains the authority.

## State transitions

None at the domain level. UI state added to the space folder page:

```
addingDocument: boolean  (closed → open → closed)
documents: Document[]    (append created doc when doc.space_id === folderId)
```

The existing derived `isEmpty` flag transitions the page from empty-state message to grid automatically when `documents` gains its first entry (FR-004, US1-AC5).

## Relationships (unchanged)

- Document —belongs to→ exactly one Space (`space_id`).
- User —has effective role in→ Space (direct membership or inherited; resolved server-side into `effective_role`).
