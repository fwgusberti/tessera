# Feature Specification: AI Assistance for Creating and Editing Documents

**Feature Branch**: `050-ai-document-assistance`

**Created**: 2026-07-02

**Status**: Draft

**Input**: User description: "add ai assistance for create and edit documents"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate a Starting Draft When Creating a Document (Priority: P1)

A user opening the "Add Document" form has a topic in mind but not yet any
written content. Instead of starting from a blank markdown field, they type a
short prompt describing what the document should cover and ask the AI to
generate a first draft. The generated markdown appears in the content field,
where the user can read it, edit it freely, or discard it and write the
content themselves before saving.

**Why this priority**: This is the highest-value, most requested capability —
it removes the blank-page problem at the exact moment a document is created
and requires no changes to the existing edit flow to deliver value on its
own.

**Independent Test**: On the document creation form, enter a short topic
prompt, trigger AI draft generation, and confirm markdown content appears in
the content field. Confirm the user can still edit that content and save the
document normally, and that the "Add Document" flow works unchanged if AI
generation is never used.

**Acceptance Scenarios**:

1. **Given** the document creation form is open, **When** the user enters a
   topic prompt and requests an AI-generated draft, **Then** generated
   markdown content appears in the content field within the form.
2. **Given** an AI-generated draft is showing in the content field, **When**
   the user edits, replaces, or clears the text, **Then** their changes are
   kept exactly as with manually typed content — the AI draft is not
   restored or reapplied.
3. **Given** a user does not have write access to create documents in a
   given space, **When** they view the creation form for that space, **Then**
   no AI draft-generation control is available to them.
4. **Given** a user never uses the AI draft-generation control, **When** they
   fill in the form manually and save, **Then** document creation succeeds
   exactly as it does today.

---

### User Story 2 - Request an AI Revision While Editing (Priority: P2)

A space member with write access is in the document edit view (raw
Markdown pane and live preview) working on existing content. They select a
passage — or the whole document — and ask the AI to revise it (e.g.
improve wording, fix grammar, expand, or summarize). The AI's suggested
replacement is shown separately from their current content so they can
compare it before deciding whether to use it.

**Why this priority**: This extends AI assistance into the editing flow
(046), where most of a document's lifetime is spent, but depends on nothing
from Story 1 and can be built and tested independently.

**Independent Test**: In the edit view of an existing document, select a
portion of text (or the whole content), request an AI revision, and confirm
a suggested replacement appears without the current content being
overwritten automatically. Separately, confirm a user without write access
to the document's space cannot see or use this control.

**Acceptance Scenarios**:

1. **Given** a user with write access is in the edit view, **When** they
   select text (or the entire content) and request an AI revision, **Then**
   the system shows a suggested replacement alongside or in place of the
   existing content, clearly marked as an AI suggestion pending review.
2. **Given** an AI suggestion is being shown, **When** the user accepts it,
   **Then** the accepted text replaces the corresponding content in the
   editable pane and behaves like any other manual edit for autosave and
   versioning purposes.
3. **Given** an AI suggestion is being shown, **When** the user rejects or
   dismisses it, **Then** the editable pane reverts to exactly the content
   that was present before the suggestion was requested, with nothing lost.
4. **Given** a user without write access to the document's space, **When**
   they view the document, **Then** no AI revision control is available to
   them (consistent with the existing edit entry point restriction).

---

### User Story 3 - Refine an AI Suggestion Before Accepting (Priority: P3)

After receiving an AI-generated draft or revision, the user is not fully
satisfied and gives a short follow-up instruction (e.g. "make it shorter" or
"more formal tone") instead of accepting, rejecting, or manually rewriting
it. The AI updates its suggestion based on the follow-up, and the user can
keep refining, accept, or discard at any point.

**Why this priority**: This meaningfully improves the usefulness of Stories 1
and 2 by avoiding all-or-nothing outcomes, but the core value already exists
without it, so it is the right piece to defer if scope must be trimmed.

**Independent Test**: Generate an AI draft or revision (per Story 1 or 2),
then submit a follow-up instruction instead of accepting or discarding.
Confirm the suggestion updates to reflect the follow-up while the user can
still accept or discard the latest version at any time.

**Acceptance Scenarios**:

1. **Given** an AI draft or revision suggestion is showing, **When** the
   user submits a follow-up instruction, **Then** the suggestion is updated
   to reflect that instruction without requiring the user to restate their
   original prompt.
2. **Given** a refined suggestion is showing, **When** the user accepts it,
   **Then** the latest refined version (not an earlier one) is what gets
   applied.
3. **Given** a user has refined a suggestion multiple times, **When** they
   decide to discard it entirely, **Then** their original content (from
   before any AI involvement) is restored unchanged.

---

### Edge Cases

- What happens when the AI assistance service is unavailable or times out?
  The user sees a clear error message; their existing typed content (in the
  create form or edit pane) is left completely unchanged and they can keep
  working manually.
- What happens if the user submits an empty or whitespace-only prompt for
  draft generation or revision? The request is blocked client-side with an
  inline message asking for a prompt, consistent with other form validation
  in the product.
- What happens if the AI-generated content is incoherent, off-topic, or
  otherwise unusable? The user can discard it and either regenerate with a
  clearer prompt or write the content manually — nothing is auto-saved or
  auto-applied without explicit acceptance.
- What happens if the user triggers a new AI request while a previous one for
  the same field is still in progress? The system prevents a second
  concurrent request for that field (e.g. the control is disabled) until the
  first completes or fails.
- What happens if a user's write access to the space is revoked while an AI
  suggestion is pending? The pending suggestion cannot be accepted and any
  further AI assistance requests are blocked, consistent with revoked edit
  access during a normal editing session.
- What happens when the document (or selected passage) is very large? The
  system handles this gracefully — generating a best-effort suggestion or
  informing the user the input is too large — rather than failing silently
  or crashing the edit view.
- What happens to AI-generated content that is never accepted? It has no
  effect on the document's saved content, autosaved edit session, or version
  history — only accepted content becomes part of the document.
- What happens if an editing session finalizes (the user navigates away, or
  the feature 046 inactivity timeout fires) while an AI suggestion is still
  pending and unaccepted? The pending suggestion is discarded; finalization
  produces a version containing only previously accepted content, exactly as
  if the pending suggestion had never been requested.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The document creation form MUST provide an optional AI
  draft-generation control that accepts a short user-provided prompt
  describing the desired document.
- **FR-002**: When draft generation is requested, System MUST generate
  markdown content from the prompt and place it into the form's content
  field without automatically submitting or creating the document.
- **FR-003**: Using AI draft generation MUST remain entirely optional — a
  user MUST be able to create a document by filling in the form manually
  without ever invoking AI assistance.
- **FR-004**: The document edit view MUST provide an AI revision control that
  lets a space member with write access request an AI-suggested improvement
  to a selected portion of the current content, or to the entire current
  content by default when nothing is selected.
- **FR-005**: When an AI revision is requested, System MUST present the
  suggested replacement content distinctly from the user's current content,
  and MUST NOT overwrite the user's existing content until it is explicitly
  accepted.
- **FR-006**: For both draft generation and revision, the user MUST be able
  to explicitly accept a suggestion (applying it), reject or dismiss it
  (discarding it with no change to their existing content), or request a
  follow-up refinement before deciding.
- **FR-007**: AI assistance controls (draft generation and revision) MUST
  only be available to users who already have the permission required for
  the underlying action — space access for creating documents, and write
  access for editing them.
- **FR-008**: AI-generated content MUST be produced using only the current
  document/content the user is actively working on and their own prompts or
  instructions — not content from other documents, spaces, or companies the
  user cannot otherwise access.
- **FR-009**: Content that originated from an AI suggestion and has not yet
  been accepted MUST be visually distinguishable from the user's own typed
  content.
- **FR-010**: If an AI assistance request fails or times out, System MUST
  show a clear, user-readable error and MUST leave the user's existing draft
  or in-progress edit content unchanged.
- **FR-011**: System MUST prevent a user from submitting a second concurrent
  AI assistance request for the same field/selection while one is already in
  progress.
- **FR-012**: Content applied to the document from an accepted AI suggestion
  MUST participate in the existing autosave and version-finalization
  behavior the same way manually typed content does — no separate version
  type or bypass of existing document versioning is introduced.
- **FR-013**: A user MUST be able to submit a follow-up instruction against
  the current AI suggestion to refine it, without needing to restate their
  original prompt or instruction from scratch.
- **FR-014**: Discarding an AI suggestion at any point (including after one
  or more refinements) MUST restore the content exactly as it was
  immediately before that suggestion was first requested.
- **FR-015**: If an editing session finalizes (navigate-away or inactivity
  timeout, per feature 046) while an AI suggestion is pending and
  unaccepted, System MUST discard that pending suggestion and finalize using
  only previously accepted content — an unaccepted suggestion MUST NOT be
  auto-applied.
- **FR-016**: AI-generated draft and revision content MUST be produced in
  the same language as the user's prompt or instruction, independent of the
  document's selected language field. When a request has no free-text
  prompt (e.g. a quick action with no typed instruction), the AI MUST match
  the language of the content being revised instead.

### Key Entities

- **AI Draft Suggestion**: Markdown content generated in response to a
  creation-time prompt; held only until the user accepts it into the content
  field or discards it. Never persisted as a document on its own.
- **AI Revision Suggestion**: Proposed replacement content generated in
  response to a revision request during editing; distinct from the
  document's current content until explicitly accepted, at which point it
  behaves like a normal edit.
- **Assistance Request**: A user's prompt or instruction (including
  follow-up refinements) that produced a given AI Draft Suggestion or AI
  Revision Suggestion.
- **Document / Document Version / Edit Session**: Existing entities from the
  document creation (009) and edit (046) features; unchanged in structure —
  this feature adds a new way that their content can originate (AI-assisted)
  alongside manual typing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can go from entering a topic prompt to seeing a
  reviewable AI-generated draft in the creation form in under 15 seconds for
  a typical request.
- **SC-002**: A user can go from requesting a revision in the edit view to
  seeing a reviewable AI suggestion in under 15 seconds for a typical
  request.
- **SC-003**: 100% of documents can still be created and 100% of edits can
  still be finalized without the user ever invoking AI assistance.
- **SC-004**: 100% of AI-generated draft or revision content requires an
  explicit user acceptance action before it becomes part of a saved document
  or a finalized document version.
- **SC-005**: A user who rejects or discards an AI suggestion recovers their
  prior content, unchanged, in a single action, every time.
- **SC-006**: 100% of attempts to use AI draft generation or AI revision by
  users who lack the underlying creation or write-access permission are
  blocked.

## Clarifications

### Session 2026-07-02

- Q: In the edit view, when the user requests an AI revision without first
  selecting any text, what should the AI act on? → A: Default to the whole
  document — if nothing is selected, the AI revises the entire current
  content; selecting text narrows the scope to just that passage.
- Q: If a user has a pending, not-yet-accepted AI suggestion open and their
  edit session finalizes (navigate-away or the inactivity timeout from
  feature 046), what happens to that pending suggestion? → A: Discard the
  pending suggestion — finalization proceeds using only already-accepted
  content; an unaccepted suggestion is never auto-applied.
- Q: Should AI-generated drafts and revisions be produced in the document's
  selected language field (e.g. pt-BR by default, per feature 009), or the
  language of the user's prompt? → A: Match the language of the user's
  prompt/instruction, independent of the document's language field.
- Q: Should the spec define a concrete size threshold for "very large"
  documents/passages sent for AI assistance, or leave it unspecified? → A:
  Leave the threshold unspecified — graceful handling and a clear message
  are required, but the exact limit is a planning-phase technical decision,
  consistent with how feature 046 leaves its inactivity-timeout duration
  unspecified.

## Assumptions

- AI assistance reuses the existing AI/LLM assistant infrastructure already
  powering the product's chat feature (022, 026, 027) rather than
  introducing a separate provider integration.
- "Write access" and document-creation permission follow the existing space
  membership/role model (024, 046); this feature introduces no new
  permission tier.
- AI assistance operates on markdown content only, matching the existing
  plain-textarea creation flow (009) and split-pane Markdown/preview edit
  flow (046). No rich-text/WYSIWYG AI assistance is in scope.
- The AI's context for a revision request is limited to the document/content
  currently being worked on plus the user's own prompt and follow-ups —
  broader retrieval across other documents (as used by the separate AI chat
  feature) is out of scope for this feature.
- Only one active AI suggestion is tracked at a time per field/selection; the
  user refines or replaces it rather than comparing multiple simultaneous
  alternatives.
- Real-time collaborative AI assistance (multiple users interacting with AI
  on the same document at the same time) is out of scope, consistent with
  the single-session editing assumption already made for feature 046.
- Rate limiting or cost controls on AI assistance requests are an
  implementation concern for the planning phase, not a user-facing
  requirement specified here.
- Whether generated content streams progressively or appears all at once is
  an implementation detail; the user-facing requirement is that the full
  suggestion is reviewable before acceptance.
- The exact size threshold beyond which document/passage content is "too
  large" for an AI assistance request is a planning-phase technical
  decision, not specified here — matching how feature 046 leaves its
  inactivity-timeout duration unspecified as an implementation detail.
