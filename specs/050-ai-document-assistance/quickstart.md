# Quickstart: AI Assistance for Creating and Editing Documents

Prerequisites: local stack running (API + Postgres + web), `ANTHROPIC_API_KEY`
set for the API service (same variable the existing `/v1/assistant/answer`
chat feature already requires), a company with a user holding EDITOR (or
company admin) role on a space, a second user with no membership in that
space, and one existing document in that space for the edit-flow checks.
See `contracts/document-assist-api.md` for full request/response shapes and
`data-model.md` for the transient state involved — no new migration is
required by this feature.

## 1. AI-generated draft on creation (User Story 1)

1. Log in as the EDITOR user, open the Documents page, click "Add Document".
2. Confirm a "Generate with AI" prompt field and button are visible (space
   already selected/default, or select the EDITOR's space first).
3. Enter a short topic (e.g. "Onboarding checklist for new hires") and
   trigger generation. **Expected**: markdown appears in the content field
   within a few seconds (SC-001), the modal has not submitted/closed.
4. Edit the generated text, then click Save. **Expected**: document is
   created normally with the edited content — confirms AI output is not
   auto-submitted (FR-002) and remains editable (Acceptance Scenario 1.2).
5. Reopen "Add Document", select a space the current user does NOT have
   write access to (or log in as the non-member user). **Expected**: no
   "Generate with AI" control is shown for that space (FR-001, SC-006).
6. Reopen "Add Document" and save without ever touching the AI control.
   **Expected**: document creation succeeds exactly as before this feature
   (SC-003).

## 2. AI revision suggestion in the edit view (User Story 2)

1. As the EDITOR user, open the document's edit view
   (`/documents/{id}/edit`).
2. Without selecting any text, trigger "Ask AI to revise" with an
   instruction (e.g. "make this more concise"). **Expected**: the request
   acts on the entire current content (Clarification: default to whole
   document when nothing is selected) and a suggestion appears in a
   distinctly styled panel — the editable pane's content is unchanged
   (FR-005).
3. Click "Accept". **Expected**: the suggestion replaces the corresponding
   content in the editable pane, the autosave indicator behaves exactly as
   for a manual edit, and the panel closes.
4. Repeat step 2, then click "Discard" instead. **Expected**: the editable
   pane still shows exactly what it did before the suggestion was requested
   — nothing lost, nothing applied (FR-014, SC-005).
5. Log in as the user with no membership in that space; confirm no "Ask AI
   to revise" control is shown (FR-007), and a direct
   `POST /v1/documents/{id}/assist/revise` call from that session returns
   `403`/`404` per `contracts/document-assist-api.md`.

## 3. Iterative refinement (User Story 3)

1. As the EDITOR user, trigger an AI revision (step 2 above), then instead
   of Accept/Discard, enter a follow-up instruction (e.g. "even shorter")
   and submit it. **Expected**: the suggestion panel updates to a new
   suggestion reflecting the follow-up, without needing to retype the
   original instruction.
2. Click Accept. **Expected**: the *latest refined* suggestion is what gets
   applied to the editable pane, not the first one.
3. Repeat once more, refining twice, then Discard. **Expected**: the
   editable pane is restored to the content from *before the first*
   suggestion in the chain — not an intermediate refinement (FR-014).

## 4. Pending suggestion discarded on session finalize

1. Trigger an AI revision, leave the suggestion panel open (do not Accept
   or Discard), and click "Done editing" (or let the inactivity timeout
   fire, per `specs/046-document-edit-flow/quickstart.md` §4.3).
   **Expected**: `GET /v1/documents/{id}/versions` shows a new version (if
   there were other accepted edits) or no new version (if the only pending
   change was the un-accepted suggestion) — the pending suggestion's text
   never appears in the finalized version (FR-015).

## 5. Failure handling

1. Temporarily make the API unable to reach the LLM provider (e.g. unset
   `ANTHROPIC_API_KEY` or stop network egress) and trigger a draft
   generation or revision request. **Expected**: a clear, user-readable
   error appears; existing typed content in the form/pane is unchanged
   (FR-010).
2. Trigger a request, then immediately trigger another for the same
   field/selection before the first resolves. **Expected**: the control is
   disabled/the second request is blocked until the first completes
   (FR-011).

## 6. Automated checks

```bash
# Backend
cd apps/api && pytest tests/contract/test_document_assist.py tests/unit/test_document_assist_router.py tests/integration/test_document_assist_tenant_isolation.py --cov --cov-fail-under=85

# Frontend
cd apps/web && npx vitest run tests/document-create-ai-assist.test.tsx tests/document-edit-ai-assist.test.tsx
```
