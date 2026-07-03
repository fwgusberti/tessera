# Implementation Plan: AI Assistance for Creating and Editing Documents

**Branch**: `050-ai-document-assistance` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/050-ai-document-assistance/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add optional, explicit-acceptance AI assistance to two existing flows: the
document creation form (009) gets a prompt-driven draft generator that fills
the content field, and the document edit view (046) gets a revision control
that proposes a replacement for the selected text (or the whole document by
default) without touching the user's content until accepted. Both flows
support iterative follow-up refinement. Technically, this is two new
stateless FastAPI endpoints that reuse the existing `AnthropicLLMProvider`
port and the existing `can_write_document` permission check — no new
database tables, no retrieval/RAG, no persisted suggestion state. Suggestions
live only in frontend component state until the user explicitly accepts
them, at which point they flow through the existing document-creation and
document-draft-autosave paths unchanged.

## Technical Context

**Language/Version**: Python 3.12 (`apps/api`, `packages/core`); TypeScript / Next.js 15 / React 19 (`apps/web`)

**Primary Dependencies**: FastAPI + Pydantic + async SQLAlchemy (API); `anthropic` AsyncAnthropic SDK via the existing `LLMProvider` port (`tessera_core.ports.providers.LLMProvider`, implemented by `tessera_api/adapters/llm.py:AnthropicLLMProvider`); Next.js App Router + the existing `lib/api.ts` fetch client (web)

**Storage**: PostgreSQL — no schema change. AI suggestions are never persisted; only content the user explicitly accepts flows into the existing `document` / `document_version` / `document_draft` tables via the existing endpoints (`POST /documents`, `PUT /documents/{id}/draft`, `POST /documents/{id}/draft/finish`).

**Testing**: pytest (`apps/api/tests/{contract,unit,integration}`) for the API; Vitest + Testing Library (`apps/web/tests/*.test.tsx`) for the frontend

**Target Platform**: Existing Linux server deployment (Docker/Kubernetes) — unchanged by this feature

**Project Type**: Web application (existing `apps/api` + `apps/web` + `packages/core` monorepo)

**Performance Goals**: AI suggestion round-trip perceived by the user in well under 15s for a typical request (SC-001/SC-002) — bounded primarily by the existing LLM provider's latency, no new bottleneck introduced

**Constraints**: No new persisted entities (suggestions are stateless/ephemeral per spec Assumptions); must reuse the existing `AnthropicLLMProvider` rather than a new provider integration; authorization must reuse the existing `can_write_document` / space-membership checks byte-for-byte with how `POST /documents` and the draft endpoints already enforce them; new UI must follow the constitution's slate/indigo palette (no new color families)

**Scale/Scope**: Two new backend endpoints, zero new DB migrations; frontend changes confined to `AddDocumentModal.tsx`, the document edit page, and one new shared suggestion-review component

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Domain-Driven Architecture** — PASS. Prompt construction and response
  shaping live in a new `tessera_api/ai_assist/` module (application layer,
  same location as the existing `tessera_api/rag/assistant.py`), not in
  `packages/core`. `tessera_core` gains no new framework-facing code; the
  only `tessera_core` reuse is the existing pure `can_write_document`
  permission function.
- **II. Separation of Concerns** — PASS. Both new endpoints call the LLM
  exclusively through the existing `LLMProvider` port. Swapping the LLM
  vendor requires touching only `adapters/llm.py`, not the router, the
  domain, or the frontend contract.
- **III. Data Locality & Consent** — PASS. No new client-side persistence.
  Pending AI suggestions live only in transient React component state
  (never `localStorage`/`sessionStorage`/disk) and vanish on accept,
  discard, or navigation — nothing new to document for consent purposes.
- **IV. Test-Driven Development (NON-NEGOTIABLE)** — PASS (planned).
  Contract tests for both new endpoints, unit tests for the permission-gate
  and language-matching behavior, an integration test for tenant isolation,
  and Vitest tests for the two modified components are all specified in
  Phase 1 artifacts and required before implementation is considered done.
  85% statement coverage gate applies to the new Python modules.
- **V. Quality Gates** — PASS. Ruff/Black run pre-commit as with every other
  change in this repo; no exception requested.
- **VI. Tenant Data Isolation (NON-NEGOTIABLE)** — PASS, see dedicated
  subsection below (required by the Security Requirements section of the
  constitution).

### Tenant Isolation

- **Tables accessed**: `space` (read, to scope a `space_id` to the caller's
  company before draft generation), `document` (read, to scope a
  `document_id` before revision), `space_membership` (read, for the
  `can_write_document` role check). No table is written by either new
  endpoint — no new tenant-scoped storage is introduced by this feature.
- **`company_id` scoping**: `POST /v1/documents/assist/draft` resolves
  `space_id` via `SqlSpaceRepository.get_by_id_for_company(space_id,
  company_id)` — the exact call `POST /documents` already makes — before any
  LLM call. `POST /v1/documents/{document_id}/assist/revise` resolves
  `document_id` via the existing `_resolve_document_for_draft_write` helper
  (`SqlDocumentRepository.get_by_id_for_company` + `can_write_document`) —
  the exact helper the draft PUT/finish endpoints already use — before any
  LLM call. Both return the standard `_not_found()` 404 and write a
  `cross_tenant_denied` audit record on a cross-tenant miss, identical to
  every other document endpoint.
- **No new cross-tenant surface**: the LLM only ever receives content the
  authenticated caller supplied in the request body (their own prompt, or
  the document/passage they are actively viewing) — there is no server-side
  document lookup by ID across spaces and no retrieval step (per FR-008),
  so there is no path for one company's content to reach another company's
  request.
- **Isolation tests to be written**: two new tenant-isolation tests
  (`apps/api/tests/integration/test_document_assist_tenant_isolation.py`)
  mirroring the existing `test_document_permissions.py` pattern — Company
  A's session calling `assist/draft` with Company B's `space_id` MUST get
  404, and Company A's session calling `assist/revise` with Company B's
  `document_id` MUST get 404 — in both cases without ever invoking the LLM
  provider (asserted via a mock/spy on `AnthropicLLMProvider`).

## Project Structure

### Documentation (this feature)

```text
specs/050-ai-document-assistance/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/api/tessera_api/
├── ai_assist/
│   ├── __init__.py                        # new
│   └── prompts.py                         # new — generate_draft(), generate_revision(); system-prompt
│                                           #   language-matching rule (FR-016)
├── routers/
│   └── document_assist.py                 # new — POST /v1/documents/assist/draft
│                                           #        POST /v1/documents/{id}/assist/revise
├── adapters/llm.py                        # unchanged — reused AnthropicLLMProvider
└── main.py                                # modified — register document_assist.router

apps/api/tests/
├── contract/test_document_assist.py                       # new
├── unit/test_document_assist_router.py                    # new
└── integration/test_document_assist_tenant_isolation.py   # new

apps/web/
├── components/documents/
│   ├── AddDocumentModal.tsx               # modified — "Generate with AI" control (Story 1)
│   └── AiSuggestionPanel.tsx              # new — shared accept/discard/refine UI (Stories 2 & 3)
├── app/documents/[id]/edit/page.tsx       # modified — "Ask AI to revise" control + AiSuggestionPanel
├── lib/
│   ├── documentAssist.ts                  # new — generateDraft(), reviseContent() API client calls
│   └── types.ts                           # modified — AI assist request/response types
└── tests/
    ├── document-create-ai-assist.test.tsx # new
    └── document-edit-ai-assist.test.tsx   # new
```

**Structure Decision**: Existing monorepo layout is reused as-is
(`apps/api` FastAPI service, `apps/web` Next.js app, `packages/core` shared
domain). This feature adds one new API module (`ai_assist/`) alongside the
existing `rag/` module it mirrors, one new router, and one new shared React
component — no new top-level project or package is introduced.

## Complexity Tracking

*No constitution violations — this section is intentionally empty.*
