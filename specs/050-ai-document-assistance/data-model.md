# Phase 1 Data Model: AI Assistance for Creating and Editing Documents

## Persisted entities

**None.** This feature introduces no new database table and no migration.
Per `research.md` ("Suggestions are stateless and never persisted
server-side"), the entities named in `spec.md` (AI Draft Suggestion, AI
Revision Suggestion, Assistance Request) exist only as request/response
payloads and transient frontend component state — never written to
PostgreSQL. Existing entities (`Document`, `DocumentVersion`, `DocumentDraft`
— i.e. the `document`, `document_version`, `document_draft` tables) are
unchanged in shape; this feature only adds a new way their content can
originate (an accepted AI suggestion flows through the same
`POST /documents`, `PUT /documents/{id}/draft`, and
`POST /documents/{id}/draft/finish` calls as manually typed content).

## Request/response shapes (transient, not persisted)

### `DraftAssistRequest` (client → server)

| Field | Type | Required | Notes |
|---|---|---|---|
| `space_id` | UUID | yes | Space the document will be created in; scoped via `get_by_id_for_company` before any LLM call (Tenant Isolation). |
| `prompt` | string | yes, non-blank | The user's topic/instruction. Rejected client-side and server-side if blank (edge case). |
| `previous_suggestion` | string | no | Present only on a follow-up refinement (Story 3); the prior draft being refined. |

### `DraftAssistResponse` (server → client)

| Field | Type | Notes |
|---|---|---|
| `content_markdown` | string | The generated (or refined) draft. Placed into the create form's content field by the client — never auto-submitted (FR-002). |

### `RevisionAssistRequest` (client → server, `POST /documents/{document_id}/assist/revise`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `content` | string | yes, non-blank | The text to revise — either the user's current text selection, or the entire current editable-pane content when nothing is selected (Clarification: default to whole document). |
| `instruction` | string | no | The user's revision instruction (e.g. "fix grammar", "make it shorter"). May be empty for a canned/quick action; language-matching then falls back to the language of `content` (FR-016). |
| `previous_suggestion` | string | no | Present only on a follow-up refinement (Story 3); the prior suggestion being refined. |

### `RevisionAssistResponse` (server → client)

| Field | Type | Notes |
|---|---|---|
| `suggestion` | string | The proposed replacement text. Never written to the document/draft until the client sends it back through the existing `PUT /documents/{id}/draft` call on explicit accept (FR-005, FR-012). |

## Frontend transient state (not persisted, not sent to any storage API)

Both `AddDocumentModal.tsx` and the edit page hold the same shape of
transient state while an AI interaction is in progress, encapsulated by the
new shared `AiSuggestionPanel` component:

| State | Type | Lifecycle |
|---|---|---|
| `pendingSuggestion` | `string \| null` | Set on a successful draft/revision response; cleared on accept or discard; never written to `localStorage`/`sessionStorage` (Constitution III). |
| `preAiContent` | `string \| null` | Snapshot of the field's content immediately before the *first* suggestion in the current chain was requested; restored verbatim on discard, satisfying FR-014 even after multiple refinements. |
| `assistStatus` | `"idle" \| "loading" \| "error"` | Drives the disabled state of the trigger control (FR-011: no second concurrent request for the same field) and the error banner (FR-010). |

## Validation rules

- `prompt` (draft) / `content` (revision) MUST be non-blank after trimming —
  enforced both client-side (inline message, edge case) and server-side
  (`field_validator`, mirroring `ChatHistoryMessage.content_must_not_be_empty`
  in `routers/assistant.py`).
- `space_id` (draft) / `document_id` (revision) MUST resolve within the
  caller's own company via `get_by_id_for_company`, else 404 (Tenant
  Isolation section of plan.md).
- The caller MUST hold `can_write_document` for the resolved space, else
  403 — identical rule and identical helper function used by
  `POST /documents` and the draft PUT/finish endpoints.
