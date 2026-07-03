# Phase 0 Research: AI Assistance for Creating and Editing Documents

All spec-level ambiguities were already resolved during `/speckit-clarify`
(see spec.md `## Clarifications`). This phase covers the remaining
plan-level technical decisions needed before design.

## Decision: Suggestions are stateless and never persisted server-side

**Rationale**: The spec's Assumptions state only one suggestion is tracked
at a time and that accepted content must flow through the existing
autosave/versioning path unchanged (FR-012). Persisting an intermediate
"suggestion" entity would require a new table, a cleanup/expiry story, and
duplicate logic for something that already has a natural home: the
browser's in-memory component state for the duration of the create/edit
session. This also makes FR-015 (discard pending suggestion on session
finalize) free — a suggestion that was never written to the `document_draft`
row cannot leak into a finalized version.

**Alternatives considered**:
- A `document_ai_suggestion` table keyed by document/session — rejected:
  adds a migration, an expiry/cleanup mechanism, and a second source of
  truth for content that must never itself become the document, for no
  behavior the spec requires.
- Storing the pending suggestion inside the existing `document_draft` row
  (e.g. a second `pending_suggestion_markdown` column) — rejected: conflates
  "autosaved user content" with "unaccepted AI output," which is exactly the
  distinction FR-005/FR-009 require staying separate, and would need its own
  finalize-time discard logic instead of getting it for free.

## Decision: One revision endpoint handles both the initial request and follow-up refinements

**Rationale**: Story 3 (refine) is, from the server's point of view, just
another revision request where the caller supplies the prior suggestion as
additional context alongside a new instruction. This mirrors how the
existing `/v1/assistant/answer` endpoint already handles multi-turn chat —
the client resends `history`, the server stays stateless per call. Reusing
that exact shape (client resends `previous_suggestion` instead of a
`history` array) avoids a third endpoint and a session/conversation-id
concept the spec never asks for.

**Alternatives considered**:
- A dedicated `POST /assist/refine` endpoint — rejected: would duplicate
  the permission check, prompt-construction, and response shape of
  `/assist/revise` for no behavioral difference other than which fields are
  populated.
- Server-side conversation state keyed by a suggestion ID — rejected: adds
  the same persistence/cleanup cost rejected above, for a single-user,
  single-suggestion-at-a-time flow the spec explicitly scopes down
  (Assumptions: "Only one active AI suggestion is tracked at a time").

## Decision: Draft generation and revision reuse the existing `LLMProvider` port unchanged

**Rationale**: `tessera_core.ports.providers.LLMProvider.complete()` already
accepts an arbitrary `messages` list and an optional `system` prompt, which
is sufficient to express "generate a draft from this prompt" and "revise
this content per this instruction" as different system prompts against the
same port. No new port method is needed. This keeps Constitution Principle
II (Separation of Concerns) intact — the vendor (`AnthropicLLMProvider`)
does not need to change at all for this feature.

**Alternatives considered**:
- A new `LLMProvider.assist_document(...)` port method — rejected: would
  encode document-assist-specific concerns (draft vs. revise vs. refine)
  into the port interface, when the existing generic `complete()` +
  per-use-case system prompt (in the new `ai_assist/prompts.py`) already
  expresses that distinction at the right layer.

## Decision: Output language matches the user's prompt/instruction via system-prompt instruction, not application logic

**Rationale**: Per the spec clarification, generated content must match the
language of the user's prompt/instruction (falling back to the language of
the content being revised when no free-text instruction is given). This is
naturally expressed as a system-prompt rule passed to `LLMProvider.complete()`
(e.g. "Respond in the same language as the user's instruction below; if no
instruction is given, respond in the same language as the provided
content.") rather than a pre-detection step in Python — avoids adding a
language-detection dependency for a rule the model can already follow
directly.

**Alternatives considered**:
- A language-detection library (e.g. `langdetect`) gating which system
  prompt variant to send — rejected: adds a dependency and a failure mode
  (misdetection on short prompts) to solve a problem the LLM already
  handles reliably when instructed directly.

## Decision: Creation-form AI control visibility reuses the existing per-space role-check endpoint

**Rationale**: The edit page already calls `GET /v1/spaces/{id}/members/me`
to decide whether to show the edit view at all (`apps/web/app/documents/[id]/edit/page.tsx`).
`AddDocumentModal.tsx` does not currently gate any field by role — the
backend is the sole enforcement point for `POST /documents` today. To
satisfy FR-001 ("no control available" to users without write access) with
the least new surface area, the modal will call the same
`members/me` endpoint once a space is selected, exactly as the edit page
does, and use it only to toggle the AI control — no new backend endpoint.

**Alternatives considered**:
- A new bulk `GET /v1/spaces?role=editor` filter — rejected: broader change
  to an existing, unrelated endpoint's contract for a need only this one
  optional UI control has.
- Skipping client-side gating and relying solely on the existing 403 from
  `POST /documents/assist/draft` — rejected: FR-001 explicitly requires the
  control itself to be unavailable, not merely to fail on use.

## Decision: New endpoints write an audit record on every request, not just on acceptance

**Rationale**: Neither new endpoint mutates persisted state, but the
existing `/v1/assistant/answer` endpoint already audit-logs every LLM query
(`action="query"`) despite being read-only, establishing the repo's
precedent that "data sent to the LLM" is itself an auditable event in this
multi-tenant system. The new endpoints follow the same precedent with
`action="ai_draft_requested"` / `action="ai_revision_requested"`.

**Alternatives considered**:
- Only audit-logging on acceptance (i.e. rely on the existing
  `document_edited` / document-creation audit trail) — rejected: would lose
  visibility into what was *sent to* the third-party LLM provider, which is
  the more security-relevant event for a system with confidentiality tiers
  on document content.
