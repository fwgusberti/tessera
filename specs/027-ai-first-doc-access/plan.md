# Implementation Plan: AI-First Interface with Doc Access

**Branch**: `027-ai-first-doc-access` | **Date**: 2026-06-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/027-ai-first-doc-access/spec.md`

## Summary

This feature establishes the AI chat as the default entry point for Tessera and adds seamless
navigation to the document browser. The root page already renders `ChatInterface` (delivered
in feature 026). What remains is: (1) a persistent, clearly-labelled Chat/Documents navigation
control in `NavBar`; (2) surfacing document links from existing citation data inside the chat
response; (3) forwarding `document_id` from the backend citation builder so the frontend can
construct document URLs.

## Technical Context

**Language/Version**: TypeScript 5 / React 18 (frontend); Python 3.12 (backend)

**Primary Dependencies**: Next.js 14 App Router, Tailwind CSS, Vitest + RTL (frontend); FastAPI, Pydantic, SQLAlchemy + asyncpg (backend)

**Storage**: PostgreSQL — no new tables or migrations required

**Testing**: Vitest + React Testing Library (frontend); pytest + anyio (backend)

**Target Platform**: Web browser (Chrome/Firefox/Safari, desktop + mobile)

**Project Type**: Web application (monorepo: apps/web, apps/api)

**Performance Goals**: No new latency-critical paths; citation links are derived from data already in the response

**Constraints**: Chat state lives in React component state — navigation away from `/` resets it (per spec assumption). No server-side conversation persistence this feature.

**Scale/Scope**: ~6 files modified, no DB migrations, no new services

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | ✅ Pass | Citation builder change is in application service layer; domain entities unchanged |
| II. Separation of Concerns | ✅ Pass | Nav logic in NavBar; citation rendering in MessageBubble; no mixing of domain + infra |
| III. Data Locality & Consent | ✅ Pass | No new local persistence; chat state is ephemeral component state |
| IV. Test-Driven Development | ✅ Pass | All changed code will have companion tests written first |
| V. Quality Gates | ✅ Pass | TypeScript strict mode; Ruff/Black enforced in CI |
| UI Design System | ✅ Pass | Using `slate-*` for neutrals, `indigo-600` for active/interactive |
| PostgreSQL as system of record | ✅ Pass | No storage changes |
| Security — JWT auth | ✅ Pass | Navigation changes do not touch auth; citation endpoint already gated |

No violations. No complexity-tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/027-ai-first-doc-access/
├── plan.md              # This file
├── research.md          # Phase 0 — decisions and alternatives
├── data-model.md        # Phase 1 — Citation DTO extension
├── quickstart.md        # Phase 1 — validation guide
├── contracts/
│   └── assistant-answer.md   # Updated /v1/assistant/answer contract
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (files touched)

```text
apps/web/
├── components/
│   ├── NavBar.tsx                         # Add Chat link + active state
│   └── chat/
│       └── MessageBubble.tsx              # Render citation document links
├── lib/
│   └── types.ts                           # Add document_id to Citation
└── tests/
    ├── navbar.test.tsx                    # Tests for Chat/Documents nav + active state
    └── chat.test.tsx                      # Tests for citation document link rendering

apps/api/
├── tessera_api/rag/
│   └── citations.py                       # Add document_id to build_citation output
└── tests/unit/
    └── test_citations.py                  # New/updated citation unit tests
```

## Implementation Phases

### Phase A — Backend: Expose document_id in citations

**Goal**: `build_citation` must include `document_id` so the frontend can link to `/documents/{id}`.

**Files**:
- `apps/api/tessera_api/rag/citations.py` — add `"document_id": str(chunk_row["document_id"])` to the returned dict
- `apps/api/tests/unit/test_citations.py` — assert `document_id` is present and correct in the output

**Why this first**: The frontend citation link depends on `document_id` being in the response. Backend change is a one-liner; tests prove the contract is satisfied.

---

### Phase B — Frontend: Citation type update

**Goal**: Add `document_id: string` to the `Citation` interface.

**File**: `apps/web/lib/types.ts`

```ts
export interface Citation {
  chunk_id: string;
  document_id: string;        // NEW
  document_version_id: string;
  quote: string;
  score: number;
}
```

**No tests needed for the type change itself** — it is a compile-time contract; tests in Phase C cover the runtime behaviour.

---

### Phase C — Frontend: Render citation links in MessageBubble

**Goal**: Below the answer text, show a "Sources" section listing each citation as a link to `/documents/{document_id}`.

**File**: `apps/web/components/chat/MessageBubble.tsx`

**Behaviour**:
- Only shown when `turn.status === "complete"` AND `!turn.answer.dont_know` AND `citations.length > 0`
- Each entry is an `<a href={/documents/${doc_id}} target="_blank" rel="noopener noreferrer">` labelled with the first 80 chars of `citation.quote`
- Section heading: "Sources" (visually muted, `text-xs text-slate-400 mt-2`)
- Links styled: `text-xs text-indigo-600 hover:underline`

**Tests** (`apps/web/tests/chat.test.tsx`):
- Renders "Sources" heading and one link when the answer has a single citation with `document_id`
- Does not render Sources section when `dont_know: true`
- Does not render Sources section when `citations` is empty or absent
- Each citation link has `href="/documents/{document_id}"` and `target="_blank"`

---

### Phase D — Frontend: Chat/Documents navigation in NavBar

**Goal**: Add clearly labelled "Chat" and "Documents" primary-nav links. Highlight the active destination.

**File**: `apps/web/components/NavBar.tsx`

**Behaviour**:
- Desktop: "Chat" and "Documents" appear as the first two items in the nav link row, before "Search" and other items
- The active link (determined by `pathname === "/" ` for Chat, `pathname.startsWith("/documents")` for Documents) uses `text-indigo-600 font-medium` instead of `text-slate-600`
- Mobile hamburger menu: same two entries added at the top of the mobile menu list
- Logo `<a href="/">` remains but is no longer the sole way to reach Chat
- "Search", "Proposals", "Metrics", "Admin" remain in the nav but are secondary items

**Tests** (`apps/web/tests/navbar.test.tsx`):
- Renders a "Chat" link pointing to `/`
- Renders a "Documents" link pointing to `/documents`
- Both links are visible on desktop (not hidden by responsive classes in shallow render)
- Mobile menu contains "Chat" and "Documents" entries
- "Chat" link has active styling when `pathname === "/"`
- "Documents" link has active styling when `pathname === "/documents"`
- (existing tests must continue to pass)

---

## Cross-Cutting Concerns

### Conversation state on navigation

Per spec assumption: chat conversation is component state. Navigating to `/documents` and back resets the conversation. This is acceptable per the spec ("chat state preserved in component state or session storage — full server-side persistence out of scope"). No additional work required.

### Access-denied state (FR-007, edge case)

The citation builder only includes documents that passed ACL filtering in `acl_first_search`. A user will never receive a citation to a document they can't access because the document would not have been retrieved. No additional access-denied state is needed in the UI.

### Empty document browser state (FR-007, edge case)

Already implemented in `apps/web/app/documents/page.tsx` — an empty-state paragraph is shown when `documents.length === 0` and `selectedSpaceId` is set or unset.

## Dependency Order

```
Phase A (backend citations.py)
  └─▶ Phase B (frontend types.ts)
        └─▶ Phase C (MessageBubble citation links)

Phase D (NavBar) — independent of A/B/C
```

Phases A→B→C are sequentially dependent (type flows from backend contract to frontend type to component). Phase D is independent and can be developed in parallel.
