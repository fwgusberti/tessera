# Contracts: Add Document Button in Space

**Feature**: 061-add-document-button | **Date**: 2026-07-11

No new or modified API endpoints. This feature consumes existing endpoints and changes one UI component contract additively.

## UI component contract (modified, additive)

### `AddDocumentModal` — `apps/web/components/documents/AddDocumentModal.tsx`

```ts
interface AddDocumentModalProps {
  open: boolean;
  spaces: Space[];
  initialSpaceId?: string;   // NEW, optional: destination preselected when the dialog opens
  onClose: () => void;
  onCreated: (document: Document) => void;
}
```

**Behavior contract**:

- When `open` transitions to true, the destination select's value is `initialSpaceId ?? ""`. All other fields reset exactly as today.
- Callers that omit `initialSpaceId` (the Documents page) observe no behavior change (FR-007).
- If `initialSpaceId` is set, the AI-assist role probe (`GET /v1/spaces/{id}/members/me`) fires for that space on open, enabling the AI panel for editors/admins (FR-003).
- The user may still change the destination via the select; `onCreated` receives the API's created `Document`, whose `space_id` reflects the final choice.
- Submit remains disabled while a request is in flight (double-click edge case); API errors render in the dialog without clearing entered content (FR-006).

## UI page contract (modified)

### Space folder page — `apps/web/app/spaces/[id]/page.tsx`

- Renders an "Add Document" button next to "Add Space" **iff** the current folder's `effective_role` is `editor` or `admin` (FR-001, FR-005). Styling follows the constitution's design system (`bg-indigo-600`, hover `indigo-700`).
- Button click opens `AddDocumentModal` with `initialSpaceId={folderId}` and `spaces` = all accessible spaces (FR-002).
- `onCreated(doc)`: if `doc.space_id === folderId`, the document is added to the grid state; otherwise the grid is unchanged (edge case: destination changed in dialog). Empty state is replaced by the grid when the first item arrives (FR-004).

## Consumed API endpoints (existing, unchanged)

### `GET /v1/spaces`

Already called by the page. Response items include `effective_role: "viewer" | "editor" | "admin"` used for button gating. Company-scoped server-side.

### `GET /v1/documents?space_id={folderId}`

Already called by the page to populate the grid. Returns 404 (with `cross_tenant_denied` audit) for spaces outside the caller's company.

### `POST /v1/documents`

Called by the modal on save. Request:

```json
{
  "space_id": "<uuid>",
  "title": "<non-empty string>",
  "language": "pt-BR",
  "confidentiality": "internal",
  "content_markdown": "",
  "tags": [],
  "frontmatter": {}
}
```

Responses relevant to this feature:

- `201` → `{ "document": Document, "version": DocumentVersion }` — dialog closes, `onCreated` fires.
- `403` — caller is not editor/admin in the target space (stale-page case, US2-AC3): message shown in dialog, content preserved.
- `404` — space missing or belongs to another company (tenant isolation; also the "space deleted while dialog open" edge case): message shown in dialog.
- `422` — server-side validation failure: message shown in dialog.

### `GET /v1/spaces/{space_id}/members/me`

Called by the modal (existing behavior) to decide AI-panel visibility. Errors degrade to hiding the panel.
