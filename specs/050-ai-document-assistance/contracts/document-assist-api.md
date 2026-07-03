# API Contract: Document AI Assistance

Two new endpoints, mounted under the existing `/v1` prefix alongside
`routers/documents.py`, in a new `routers/document_assist.py`. Both require
the same authentication as every other `/v1/documents*` route
(`CompanyMemberContext` — OAuth2/JWT session, resolves to `(user_info,
company_id, caller_membership)`) and go through the `_onboarding_guard`
dependency already applied to `documents.router` in `main.py`.

---

## `POST /v1/documents/assist/draft`

Generates an AI draft for the document-creation form (Story 1). Stateless —
nothing is persisted by this call.

**Auth**: `CompanyMemberContext`. Caller MUST have `can_write_document` for
`space_id` (same check `POST /documents` performs) — 403 otherwise.

**Request body**

```json
{
  "space_id": "uuid",
  "prompt": "string, required, non-blank",
  "previous_suggestion": "string, optional — present only for a Story 3 follow-up refinement"
}
```

**Response `200`**

```json
{
  "content_markdown": "string"
}
```

**Error responses**

| Status | Condition |
|---|---|
| `400` | `prompt` is blank/whitespace-only |
| `403` | Caller lacks `can_write_document` for `space_id` |
| `404` | `space_id` does not resolve within the caller's company (cross-tenant — indistinguishable from absent, matching `_not_found()` elsewhere in `documents.py`) |
| `502`/`503` | Upstream LLM provider failure or timeout — surfaced as a generic user-readable error (FR-010); the client MUST leave existing form content untouched |

**Side effects**: writes an audit record
(`action="ai_draft_requested"`, `entity_type="space"`, `entity_id=space_id`)
on every successful or denied attempt where a company context was
established, mirroring `/v1/assistant/answer`'s `action="query"` audit.

---

## `POST /v1/documents/{document_id}/assist/revise`

Generates an AI revision suggestion for the edit view (Stories 2 & 3).
Stateless — nothing is persisted by this call; the returned `suggestion` is
not applied to the document/draft unless the client separately calls the
existing `PUT /v1/documents/{document_id}/draft` after the user accepts it.

**Auth**: `CompanyMemberContext`. Resolves `document_id` and enforces write
access via the existing `_resolve_document_for_draft_write` helper (same
403/404 semantics as `GET/PUT /documents/{id}/draft`).

**Request body**

```json
{
  "content": "string, required, non-blank — selected text, or the whole current editable content when nothing is selected",
  "instruction": "string, optional — e.g. 'fix grammar'; empty means a canned/quick action",
  "previous_suggestion": "string, optional — present only for a Story 3 follow-up refinement"
}
```

**Response `200`**

```json
{
  "suggestion": "string"
}
```

**Error responses**

| Status | Condition |
|---|---|
| `400` | `content` is blank/whitespace-only |
| `403` | Caller lacks `can_write_document` for the document's space |
| `404` | `document_id` does not resolve within the caller's company |
| `502`/`503` | Upstream LLM provider failure or timeout — same handling as above |

**Side effects**: writes an audit record
(`action="ai_revision_requested"`, `entity_type="document"`,
`entity_id=document_id`) on every successful or denied attempt where a
company context was established.

---

## Explicitly out of contract

- Neither endpoint accepts or returns a suggestion/session identifier —
  refinement (Story 3) is expressed by resending `previous_suggestion` plus
  a new `prompt`/`instruction`, not by referencing server-held state
  (see `research.md`, "One revision endpoint handles both...").
- Neither endpoint performs retrieval across other documents/spaces (no
  `space_ids` fan-out like `/v1/assistant/answer`); the only content in
  scope is what the request body supplies (FR-008).
- Accepting a suggestion is NOT a call to either of these endpoints — it is
  the client applying `suggestion`/`content_markdown` to its own local
  state and, for the edit flow, letting the existing autosave
  (`PUT /documents/{id}/draft`) and finalize (`POST
  /documents/{id}/draft/finish`) endpoints pick it up unchanged (FR-012).
