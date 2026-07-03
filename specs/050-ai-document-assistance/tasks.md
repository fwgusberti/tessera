---

description: "Task list for AI Assistance for Creating and Editing Documents"

---

# Tasks: AI Assistance for Creating and Editing Documents

**Input**: Design documents from `/specs/050-ai-document-assistance/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/document-assist-api.md, quickstart.md

**Tests**: Included and REQUIRED — `plan.md`'s Constitution Check commits this feature to Test-Driven Development (Constitution Principle IV, NON-NEGOTIABLE): pytest tests for the two new endpoints and Vitest tests for both modified UI flows are written first and must fail before the corresponding implementation exists.

**Organization**: Tasks are grouped by user story (from `spec.md`) to enable independent implementation and testing of each story. This feature touches `apps/api` (2 new stateless endpoints, zero new tables — research.md) and `apps/web` (`AddDocumentModal.tsx`, the document edit page, and one new shared component).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task includes an exact file path

## Path Conventions

Backend: `apps/api/` (FastAPI). Frontend: `apps/web/` (Next.js App Router). No `packages/core/` or `db/migrations/` changes — this feature adds no persisted entity (research.md, data-model.md).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the shared request/response shapes at the frontend-type level before anything is built on top of them. No new package dependencies are needed (`anthropic` SDK and `AnthropicLLMProvider` already exist).

- [X] T001 [P] Add `DraftAssistRequest`, `DraftAssistResponse`, `RevisionAssistRequest`, `RevisionAssistResponse` TypeScript interfaces to `apps/web/lib/types.ts` per the shapes in `data-model.md` (`space_id`/`prompt`/`previous_suggestion` → `content_markdown`; `content`/`instruction`/`previous_suggestion` → `suggestion`), mirroring the existing interface style in that file

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared backend module skeleton and shared test-file scaffolding needed by both User Story 1 and User Story 2 (User Story 3 only extends US1/US2 code, so it depends on them directly rather than on this phase)

**⚠️ CRITICAL**: No User Story 1 or 2 backend implementation can begin until T002-T004 are complete. Test-file skeletons (T005-T008) have no implementation dependency and can start immediately.

- [X] T002 [P] Create `apps/api/tessera_api/ai_assist/__init__.py` (empty) and `apps/api/tessera_api/ai_assist/prompts.py` containing only the shared `LANGUAGE_MATCH_RULE` system-prompt fragment constant: `"Respond in the same language as the user's instruction. If no instruction is given, respond in the same language as the provided content."` (research.md "Output language matches..."; FR-016) — no `generate_draft`/`generate_revision` functions yet, those are added in US1/US2
- [X] T003 [P] Create `apps/api/tessera_api/routers/document_assist.py` skeleton: `APIRouter(tags=["document-assist"])` instance and the imports both endpoints will need (`CompanyMemberContext`, `SessionDep`, `write_audit`, `AnthropicLLMProvider`, `SqlSpaceRepository`, `SqlSpaceMembershipRepository`, `SqlUserRepository`, `is_company_admin`, `can_write_document`), plus imports of `_not_found` and `_resolve_document_for_draft_write` from `tessera_api.routers.documents` for reuse (plan.md Tenant Isolation section — same helper the draft PUT/finish endpoints already use) — no endpoint functions yet
- [X] T004 Register `document_assist.router` in `apps/api/tessera_api/main.py`: add `app.include_router(document_assist.router, prefix="/v1", dependencies=_onboarding_guard)` immediately after the existing `app.include_router(documents.router, ...)` line (depends on T003)
- [X] T005 [P] Create `apps/api/tests/contract/test_document_assist.py` skeleton (imports only, mirroring `apps/api/tests/contract/test_assistant.py`'s style of testing Pydantic request/response models directly) — no test cases yet
- [X] T006 [P] Create `apps/api/tests/unit/test_document_assist_router.py` skeleton: import and reuse the `_bypass_onboarding`, `_with_company_context`/`_with_company_member_context`, `_with_db` helpers from `apps/api/tests/unit/test_documents_router.py` (same pattern that file already establishes for `documents.py`'s own router tests), plus `AsyncMock`/`MagicMock`/`patch` imports for mocking `AnthropicLLMProvider.complete` — no test cases yet
- [X] T007 [P] Create `apps/api/tests/integration/test_document_assist_tenant_isolation.py` skeleton: two-company TestClient + real-JWT fixture setup mirroring `apps/api/tests/integration/test_document_permissions.py`'s pattern (`_make_jwt_header`, `_make_user`, `_company_membership`, `_bypass_onboarding_guard`) — no test cases yet
- [X] T008 [P] Create `apps/web/tests/document-edit-ai-assist.test.tsx` skeleton: mock `@/lib/api`, `@/lib/auth`, `next/navigation`, following `apps/web/tests/documents-edit.test.tsx`'s pattern; shared fixtures for a document + current version, an EDITOR-role `{ membership: { role: "editor" } }` response and a VIEWER-role equivalent for `/v1/spaces/{id}/members/me` — no test cases yet (shared by US2 and US3)

**Checkpoint**: Foundation ready — User Story 1 and User Story 2 backend/frontend work can both begin

---

## Phase 3: User Story 1 - Generate a Starting Draft When Creating a Document (Priority: P1) 🎯 MVP

**Goal**: An optional "Generate with AI" control on the document creation form that turns a short topic prompt into markdown placed directly into the content field — fully editable/discardable, never auto-submitted.

**Independent Test**: On the creation form, enter a topic prompt, trigger generation, confirm markdown appears in the content field, edit and save normally. Separately, confirm the control is absent for a space the user cannot write to, and that manual-only creation still works unchanged.

### Tests for User Story 1 ⚠️

> Write these tests FIRST, run them, and confirm they FAIL before implementing anything below

- [X] T009 [P] [US1] In `apps/api/tests/contract/test_document_assist.py`, add tests asserting `DraftAssistRequest` rejects a blank/whitespace-only `prompt` (mirrors `ChatHistoryMessage.content_must_not_be_empty` in `routers/assistant.py`) and that `DraftAssistResponse` requires `content_markdown`
- [X] T010 [P] [US1] In `apps/api/tests/unit/test_document_assist_router.py`, add tests asserting `POST /v1/documents/assist/draft`: (a) as an EDITOR-role caller with a mocked `AnthropicLLMProvider.complete` returns 200 with `{"content_markdown": ...}`, and the `system` prompt passed to `complete()` includes `LANGUAGE_MATCH_RULE` and the caller's `prompt`; (b) as a caller without write access to `space_id` (VIEWER/non-member) returns 403; (c) a blank `prompt` returns 400 without calling the LLM provider; (d) writes an audit record with `action="ai_draft_requested"`, `entity_type="space"`, `entity_id=space_id` (contracts/document-assist-api.md)
- [X] T011 [P] [US1] In `apps/api/tests/integration/test_document_assist_tenant_isolation.py`, add a test asserting Company A's session calling `POST /v1/documents/assist/draft` with Company B's `space_id` returns the generic 404 body, writes a `cross_tenant_denied` audit record, and never invokes the mocked/spied LLM provider (plan.md Tenant Isolation section)
- [X] T012 [P] [US1] Create `apps/web/tests/document-create-ai-assist.test.tsx` with tests asserting: (a) a "Generate with AI" prompt input + button is visible when the modal's selected space returns an EDITOR-role `members/me` response, and hidden when it returns a VIEWER-role response (FR-001); (b) submitting a prompt calls `generateDraft` and the response's `content_markdown` appears in the content textarea without the form auto-submitting (FR-002, FR-003); (c) after a draft appears, manually editing/clearing the textarea keeps exactly what the user typed (Acceptance Scenario 1.2); (d) a blank prompt is blocked client-side with an inline message before any API call; (e) an API error shows a banner and leaves existing textarea content untouched (FR-010); (f) the "Generate with AI" button is disabled while a request is in flight (FR-011)

### Implementation for User Story 1

- [X] T013 [US1] Add `async def generate_draft(prompt: str, llm_provider: LLMProvider, previous_suggestion: str | None = None) -> str` to `apps/api/tessera_api/ai_assist/prompts.py`: builds a system prompt combining `LANGUAGE_MATCH_RULE` with draft-generation instructions (and, when `previous_suggestion` is set, instructs the model to revise that prior draft per the new `prompt` as a follow-up rather than starting over — research.md "One revision endpoint handles both..."), calls `llm_provider.complete(messages=[{"role": "user", "content": prompt}], system=system_prompt)`, returns the resulting markdown (depends on T002)
- [X] T014 [US1] Add `POST /documents/assist/draft` to `apps/api/tessera_api/routers/document_assist.py`: `DraftAssistRequest`/`DraftAssistResponse` Pydantic models (blank-`prompt` `field_validator`, mirroring `ChatHistoryMessage`); resolve `space_id` via `SqlSpaceRepository.get_by_id_for_company(space_id, company_id)` (404 + `cross_tenant_denied` audit on miss, matching `create_document`'s existing check in `routers/documents.py`); enforce `can_write_document` via `SqlSpaceMembershipRepository.list_by_space` (403 on failure); call `generate_draft()`; `write_audit(action="ai_draft_requested", entity_type="space", entity_id=space_id)`; return `{"content_markdown": ...}` (contracts/document-assist-api.md; depends on T003, T004, T013)
- [X] T015 [US1] Create `apps/web/lib/documentAssist.ts` with `generateDraft(spaceId: string, prompt: string, previousSuggestion?: string): Promise<DraftAssistResponse>` calling `api.post("/v1/documents/assist/draft", { space_id: spaceId, prompt, previous_suggestion: previousSuggestion })` (depends on T001)
- [X] T016 [US1] Modify `apps/web/components/documents/AddDocumentModal.tsx`: on space selection, fetch `GET /v1/spaces/{spaceId}/members/me` (same call/shape the edit page already makes) and show a "Generate with AI" prompt input + button only when the resolved role is `"editor"`/`"admin"` (FR-001); on submit, call `generateDraft()`, disable the button while in flight (FR-011), on success set `contentMarkdown` to the response directly (FR-002) while snapshotting the pre-generation value as `preAiContent` (only on the *first* generation in a chain) and the response as `lastAiSuggestion`; on failure show an inline error banner and leave `contentMarkdown` untouched (FR-010); reset all AI-related state alongside the existing reset-on-close effect (depends on T012, T015)

**Checkpoint**: User Story 1 is fully functional and independently testable — AI draft generation, permission gating, and manual-only creation all work without touching the edit flow.

---

## Phase 4: User Story 2 - Request an AI Revision While Editing (Priority: P2)

**Goal**: An "Ask AI to revise" control in the edit view that proposes a replacement for the current selection (or the whole document by default) in a distinct panel, never overwriting the editable pane until the user explicitly accepts.

**Independent Test**: In the edit view, request a revision, confirm the suggestion appears separately from the editable pane, then confirm Accept applies it and Discard leaves the pane exactly as it was. Separately, confirm the control is absent for a user without write access, and that a pending suggestion never survives session finalization.

### Tests for User Story 2 ⚠️

> Write these tests FIRST, run them, and confirm they FAIL before implementing anything below

- [X] T017 [P] [US2] In `apps/api/tests/contract/test_document_assist.py`, add tests asserting `RevisionAssistRequest` rejects a blank/whitespace-only `content` and that `RevisionAssistResponse` requires `suggestion`
- [X] T018 [P] [US2] In `apps/api/tests/unit/test_document_assist_router.py`, add tests asserting `POST /v1/documents/{document_id}/assist/revise`: (a) as an EDITOR-role caller with a mocked `AnthropicLLMProvider.complete` returns 200 with `{"suggestion": ...}`, and the `system` prompt includes `LANGUAGE_MATCH_RULE`; (b) with an empty `instruction`, the constructed prompt falls back to matching the language of `content` rather than an instruction (FR-016 second sentence — assert on the `messages`/`system` the mocked `complete()` was called with); (c) as a caller without write access returns 403; (d) against a nonexistent/cross-tenant `document_id` returns 404; (e) blank `content` returns 400 without calling the LLM; (f) writes an audit record with `action="ai_revision_requested"`, `entity_type="document"`, `entity_id=document_id`
- [X] T019 [P] [US2] In `apps/api/tests/integration/test_document_assist_tenant_isolation.py`, add a test asserting Company A's session calling `POST /v1/documents/{document_id}/assist/revise` with Company B's `document_id` returns the generic 404 body, writes a `cross_tenant_denied` audit record, and never invokes the mocked/spied LLM provider
- [X] T020 [P] [US2] In `apps/web/tests/document-edit-ai-assist.test.tsx`, add tests asserting: (a) an "Ask AI to revise" control is visible in the EDITOR-role edit view; (b) triggering it with no text selection sends the entire current editable content as `content` (Clarification: default to whole document); (c) triggering it with a text selection sends only the selected substring as `content`; (d) a successful response renders the suggestion in a visually distinct panel (FR-009) while the editable pane's content is unchanged (FR-005); (e) clicking Accept applies the suggestion into the editable pane at the corresponding location and marks the session as edited (so the existing autosave effect picks it up, per FR-012); (f) clicking Discard leaves the editable pane exactly as it was before the request, with the panel closed (FR-014); (g) an API error shows a message and leaves the editable pane untouched; (h) the trigger is disabled while a request is in flight (FR-011)
- [X] T021 [P] [US2] In `apps/web/tests/document-edit-ai-assist.test.tsx`, add a test asserting that if the user triggers "Done editing" (or the existing `pagehide`/inactivity-timeout finalize paths from feature 046) while a suggestion panel is still open and unaccepted, the finalize call's request body reflects only the editable pane's actual content — the pending suggestion text is never included (FR-015)

### Implementation for User Story 2

- [X] T022 [US2] Add `async def generate_revision(content: str, instruction: str, llm_provider: LLMProvider, previous_suggestion: str | None = None) -> str` to `apps/api/tessera_api/ai_assist/prompts.py`: builds a system prompt combining `LANGUAGE_MATCH_RULE` with revision instructions, including `content` (and `previous_suggestion` when refining); when `instruction` is empty, the system prompt directs the model to infer intent as a general improvement pass and to match `content`'s language per `LANGUAGE_MATCH_RULE`'s second sentence; calls `llm_provider.complete(...)`, returns the suggestion text (depends on T002)
- [X] T023 [US2] Add `POST /documents/{document_id}/assist/revise` to `apps/api/tessera_api/routers/document_assist.py`: `RevisionAssistRequest`/`RevisionAssistResponse` Pydantic models (blank-`content` `field_validator`); reuse `_resolve_document_for_draft_write(document_id, ctx, session)` imported from `routers/documents.py` for the identical 404/403 resolution the draft PUT/finish endpoints already use; call `generate_revision()`; `write_audit(action="ai_revision_requested", entity_type="document", entity_id=document_id)`; return `{"suggestion": ...}` (contracts/document-assist-api.md; depends on T003, T004, T022)
- [X] T024 [US2] Add `reviseContent(documentId: string, content: string, instruction: string, previousSuggestion?: string): Promise<RevisionAssistResponse>` to `apps/web/lib/documentAssist.ts`, calling `api.post(`/v1/documents/${documentId}/assist/revise`, { content, instruction, previous_suggestion: previousSuggestion })` (depends on T015)
- [X] T025 [US2] Create `apps/web/components/documents/AiSuggestionPanel.tsx`: a self-contained panel accepting `{ suggestion: string | null, status: "idle" | "loading" | "error", errorMessage?: string, onAccept: () => void, onDiscard: () => void }`, styled per the constitution's UI Design System (indigo-50/indigo-200 card, indigo-600 "Accept" button, slate-* "Discard" button — no new color families) — no refine input yet (added in US3)
- [X] T026 [US2] Modify `apps/web/app/documents/[id]/edit/page.tsx`: add an "Ask AI to revise" trigger + short instruction input above the Markdown textarea; on trigger, read `textareaRef.current.selectionStart`/`selectionEnd` — if equal (no selection), use the full `content` as the revision target, otherwise use the selected substring; call `reviseContent()`, disabling the trigger while in flight (FR-011); render `AiSuggestionPanel` with the response; on Accept, splice the suggestion into `content` at the same range that was sent (full replace when no selection was made), set `hasEditedRef.current = true` so the existing autosave/finalize logic in this file treats it like any other edit (FR-012); on Discard, simply clear the pending-suggestion state — `content` is never touched, so FR-015 (discard on finalize) is satisfied by construction since the suggestion was never written into `content` (depends on T020, T021, T024, T025)

**Checkpoint**: User Stories 1 AND 2 both work independently — AI-assisted creation and AI-assisted revision, each fully gated by existing write-access checks, neither touching version history until content is actually accepted.

---

## Phase 5: User Story 3 - Refine an AI Suggestion Before Accepting (Priority: P3)

**Goal**: Both the creation-flow draft and the edit-flow revision support a follow-up refinement instruction before the user accepts or discards, and discarding after any number of refinements always restores the content from before the *first* suggestion in the chain.

**Independent Test**: Generate a draft or revision, submit a follow-up instruction instead of accepting/discarding, confirm the suggestion updates; accept and confirm the latest refined version is what's applied; separately, refine twice then discard and confirm the pre-AI content (not an intermediate refinement) is restored.

### Tests for User Story 3 ⚠️

> Write these tests FIRST, run them, and confirm they FAIL before implementing anything below

- [X] T027 [P] [US3] In `apps/web/tests/document-edit-ai-assist.test.tsx`, add tests asserting: (a) submitting a follow-up instruction from the open suggestion panel calls `reviseContent()` with `previous_suggestion` set to the currently shown suggestion, and the panel updates to the new response without requiring the original instruction to be retyped (FR-013); (b) after two refinements, clicking Accept applies the *latest* suggestion, not the first or second (Acceptance Scenario 3.2); (c) after two refinements, clicking Discard restores the editable pane to its content from *before the first* suggestion was requested, not an intermediate refinement (FR-014, Acceptance Scenario 3.3)
- [X] T028 [P] [US3] In `apps/web/tests/document-create-ai-assist.test.tsx`, add the equivalent tests for the creation flow: (a) a follow-up instruction after an initial draft calls `generateDraft()` with `previous_suggestion` set to the last generated draft and overwrites the content field with the refined result; (b) after two refinements, clicking Discard restores the content field to its value from *before the first* generation in the session (`preAiContent`), not an intermediate refinement

### Implementation for User Story 3

- [X] T029 [P] [US3] Extend `apps/web/components/documents/AiSuggestionPanel.tsx` with a follow-up instruction input and "Refine" action; `onRefine` is a caller-supplied callback (parallel to `onAccept`/`onDiscard`) so the panel stays presentation-only and the edit page owns the actual `reviseContent()` call (depends on T025)
- [X] T030 [US3] In `apps/web/app/documents/[id]/edit/page.tsx`, wire `AiSuggestionPanel`'s `onRefine` to call `reviseContent()` again with `previous_suggestion` set to the currently displayed suggestion, replacing it on success; keep the original pre-request `content` snapshot fixed across any number of refinements so Discard (T026) always reverts to it regardless of how many refinements occurred (depends on T026, T029)
- [X] T031 [P] [US3] In `apps/web/components/documents/AddDocumentModal.tsx`, add a "Refine" input alongside the existing "Generate with AI" control and a "Discard AI draft" button: Refine calls `generateDraft()` with `previous_suggestion` set to `lastAiSuggestion` and overwrites both `contentMarkdown` and `lastAiSuggestion` with the new response; Discard restores `contentMarkdown` to the `preAiContent` snapshot captured on the *first* generation and clears `preAiContent`/`lastAiSuggestion` (depends on T016)

**Checkpoint**: All three user stories independently functional — this is the full feature.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T032 [P] Run `quickstart.md` scenarios 1-5 manually against local `apps/api` + `apps/web` dev servers (draft generation + gating, revision + accept/discard, refinement chains, pending-suggestion-discarded-on-finalize, LLM-failure handling) — NOT DONE in this session: sandbox has no `ANTHROPIC_API_KEY` and no app-level `.env`/auth config, so a real browser click-through isn't possible here; every scenario is instead exercised by an equivalent automated test (see T033/T034 files) — a human should still run this manually against a fully configured environment before shipping.
- [X] T033 [P] Run `cd apps/api && pytest tests/contract/test_document_assist.py tests/unit/test_document_assist_router.py tests/integration/test_document_assist_tenant_isolation.py --cov --cov-fail-under=85` and confirm zero regressions in `tests/unit/test_documents_router.py` and `tests/contract/test_assistant.py`
- [X] T034 [P] Run `cd apps/web && npx vitest run tests/document-create-ai-assist.test.tsx tests/document-edit-ai-assist.test.tsx` then the full suite (`npx vitest run`) and confirm zero regressions (`documents-edit.test.tsx`, `documents.test.tsx`, etc.)
- [X] T035 Run `ruff check .` and `black --check .` in `apps/api` on all new/modified Python files (Constitution V)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: T002-T004 have no dependency on Setup and can start immediately; BLOCKS User Story 1 and User Story 2's backend endpoint tasks (T014, T023). T005-T008 (test skeletons) can start immediately in parallel with T002-T004.
- **User Story 1 (Phase 3)**: Depends on Foundational T002-T004 (backend) and T001 (frontend types) — otherwise independent
- **User Story 2 (Phase 4)**: Depends on Foundational T002-T004, T008, and on User Story 1's `apps/web/lib/documentAssist.ts` (T015) existing as a file to extend — functionally independent of US1's UI otherwise
- **User Story 3 (Phase 5)**: Depends on User Story 1 (T016, for the create-flow refine/discard controls) and User Story 2 (T025/T026, for the edit-flow panel to extend) — spec.md states this dependency explicitly ("builds on Stories 1 and 2")
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories — delivers AI-assisted draft generation on creation
- **User Story 2 (P2)**: Shares `apps/web/lib/documentAssist.ts` (T015) with US1 but is otherwise independently testable — delivers AI-assisted revision in the edit view
- **User Story 3 (P3)**: Builds on both US1 (T016) and US2 (T025/T026) — adds iterative refinement to each

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Backend prompt-construction helpers (T013, T022) are added to the same shared `ai_assist/prompts.py` file created in Foundational (T002) but do not depend on each other
- Story complete and checkpointed before moving to the next priority

### Parallel Opportunities

- T001 (Setup) and T002-T008 (Foundational) can all run in parallel — different files
- T009-T012 (US1 tests) can run in parallel — four different files
- T013 (prompts.py) can be built in parallel with the US1 tests — different file; T014 depends on T013
- T017-T020 (US2 tests) can run in parallel — three different files (T020/T021 share one file, sequential within it)
- T022 (prompts.py) can be built in parallel with the US2 tests; T023 depends on T022 and on T014 having already registered the router pattern (same file, sequential edit)
- T027/T028 (US3 tests) can run in parallel — two different files
- T029 and T031 (US3 implementation) can run in parallel — different files; T030 depends on T029

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together (four different files):
Task: "Add DraftAssistRequest/Response contract tests to test_document_assist.py"
Task: "Add POST /documents/assist/draft unit tests to test_document_assist_router.py"
Task: "Add cross-tenant assist/draft test to test_document_assist_tenant_isolation.py"
Task: "Create document-create-ai-assist.test.tsx with the full US1 test suite"

# The prompt-construction helper can be built alongside the tests:
Task: "Add generate_draft() to ai_assist/prompts.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002-T008)
3. Complete Phase 3: User Story 1 (T009-T016)
4. **STOP and VALIDATE**: Run `quickstart.md` Scenario 1 (AI-generated draft on creation)
5. Demo if ready — this alone already delivers the highest-value capability named in the feature request ("create")

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. User Story 1 → validate via `quickstart.md` Scenario 1 → demo (MVP)
3. User Story 2 → validate via `quickstart.md` Scenarios 2 and 4 → demo (AI-assisted editing — the other half of the feature request)
4. User Story 3 → validate via `quickstart.md` Scenario 3 → demo (iterative refinement on top of both flows)
5. Polish (T032-T035) → full regression pass

### Parallel Team Strategy

1. One developer completes Foundational (T002-T008) while a second starts drafting US1's frontend tests (T012) against the not-yet-implemented endpoint (expected to fail until T014 lands)
2. Once Foundational lands, split by story: Developer A takes User Story 1 (T009-T016), Developer B takes User Story 2 (T017-T026) — both only share `apps/web/lib/documentAssist.ts` (T015/T024), a small, low-conflict file
3. User Story 3 (T027-T031) is best picked up by whichever developer already owns the file being extended (`AddDocumentModal.tsx` vs. `AiSuggestionPanel.tsx`/`edit/page.tsx`) to avoid merge conflicts

---

## Notes

- [P] tasks touch different files (or independent, non-conflicting additions to the same test file) with no unmet dependency
- Verify each test fails before writing its implementation (Constitution Principle IV)
- Commit after each task or logical group
- Stop at any checkpoint (end of Phase 3, 4, or 5) to validate a story independently before continuing
- The creation flow (US1/US3) writes AI output directly into the content field per FR-002/Acceptance Scenario 1.1, with a separate Discard/Refine affordance layered on top; the edit flow (US2/US3) keeps AI output in a distinct, unapplied panel until Accept per FR-005 — these are intentionally different interaction patterns for the same underlying capability, not an inconsistency (spec.md Acceptance Scenarios)
- `generate_draft()` and `generate_revision()` are added to the same shared `ai_assist/prompts.py` file (T013, T022) rather than a service class, matching the existing `rag/assistant.py` module's style of small, self-contained async functions rather than introducing a new abstraction layer
