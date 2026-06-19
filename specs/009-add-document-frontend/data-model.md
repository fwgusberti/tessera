# Data Model: Add Document — Frontend

**Feature**: 009-add-document-frontend | **Date**: 2026-06-18

## Existing Types (no changes)

All types are already declared in `apps/web/lib/types.ts`. This feature adds no new types.

### `Document` (existing)

| Field | Type | Notes |
|---|---|---|
| `id` | `string` (UUID) | Server-generated |
| `space_id` | `string` (UUID) | Required; links to a Space |
| `title` | `string` | Required |
| `language` | `string` | Defaults to `"pt-BR"` |
| `confidentiality` | `"public" \| "internal" \| "confidential" \| "restricted"` | Defaults to `"internal"` |
| `tags` | `string[]` | Defaults to `[]` (tags out of scope for this feature) |
| `state` | `"ingested" \| "published" \| "archived"` | Always `"ingested"` on creation |
| `current_version_id` | `string \| null` | Set server-side |
| `owner_user_id` | `string \| null` | Set server-side |
| `created_at` | `string` (ISO 8601) | Server-generated |
| `updated_at` | `string` (ISO 8601) | Server-generated |

### `Space` (existing, read-only for this feature)

| Field | Type | Notes |
|---|---|---|
| `id` | `string` (UUID) | Used as `space_id` in document creation |
| `name` | `string` | Displayed in the space selector |

## Form State (component-local, not persisted)

The `AddDocumentModal` component holds these fields in local React state:

| Field | Type | Default | Validation |
|---|---|---|---|
| `title` | `string` | `""` | Required (non-empty after trim) |
| `spaceId` | `string` | `""` | Required (non-empty) |
| `language` | `"pt-BR" \| "en"` | `"pt-BR"` | Always has a value; no validation needed |
| `confidentiality` | `"internal" \| "restricted" \| "public"` | `"internal"` | Always has a value; no validation needed |
| `contentMarkdown` | `string` | `""` | Optional at creation |
| `submitting` | `boolean` | `false` | UI state |
| `error` | `string \| null` | `null` | API error banner |

## API Contract (existing endpoint, no change)

**POST** `/v1/documents`

Request body:
```json
{
  "space_id": "<uuid>",
  "title": "<string>",
  "language": "pt-BR",
  "confidentiality": "internal",
  "tags": [],
  "content_markdown": "",
  "frontmatter": {}
}
```

Response (`201 Created`):
```json
{
  "document": { /* Document object */ },
  "version": { /* DocumentVersion object */ }
}
```
