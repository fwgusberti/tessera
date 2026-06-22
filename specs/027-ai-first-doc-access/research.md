# Research: AI-First Interface with Doc Access

## Decision: Root-page chat is already in place

**Decision**: Feature 026 already delivers US1 — `apps/web/app/page.tsx` renders `ChatInterface` as the primary content and `AuthGuard` wraps it. FR-001 is satisfied with zero changes required.

**Rationale**: The spec assumption ("026 is the foundation") is confirmed by reading the code.

**Alternatives considered**: Redirect-on-login middleware; server component landing page — neither is needed.

---

## Decision: Persistent navigation via NavBar — add "Chat" entry

**Decision**: The existing `NavBar` already links to `/documents` but has no named "Chat" destination. The Tessera logo `<a href="/">` serves as an implicit home link, but FR-004 requires both destinations to be clearly labelled. The fix is to add an explicit "Chat" `<a href="/">` alongside the "Documents" link in the NavBar, styled identically to the other nav links, and use `usePathname` to mark the active link with an `indigo-600` accent.

**Rationale**: The NavBar is rendered in every primary view via `app/layout.tsx`. Adding two visually consistent links there satisfies FR-002, FR-004, and SC-001/SC-002 in a single, contained change.

**Alternatives considered**:
- Dedicated top-bar tab strip separate from NavBar: heavier DOM, duplicates layout logic.
- Floating action button: not persistent, fails SC-005 (visibility without scrolling).
- Secondary sidebar: out of scope; mobile complicates the layout.

---

## Decision: Document links in chat via existing citation data

**Decision**: The `/v1/assistant/answer` response already returns `citations[]`, and each citation already has `document_version_id` in the payload. The chunk row also carries `document_id`. The plan is:

1. Add `document_id` to `build_citation` in `rag/citations.py` so the API surfaces it.
2. Add `document_id: string` to the frontend `Citation` interface in `types.ts`.
3. In `MessageBubble`, render a "Sources" section beneath the answer listing linked document titles (constructed as `/documents/{document_id}`). Links open in `target="_blank"` to preserve chat state (FR-006).

**Rationale**: No new API endpoint or backend service is required. The data already flows from the vector store through the retrieval pipeline and appears in the response — it just wasn't forwarded to the frontend.

**Alternatives considered**:
- New `/v1/assistant/document-links` endpoint: unnecessary indirection.
- Inline document cards (separate fetch for each citation): adds latency and complexity; deferred to a future enhancement.
- Open document in a slide-over panel without leaving the page: richer UX but higher implementation cost; the spec says "opens in same view below, side panel, or new tab — preserving chat state" — new tab is the simplest compliant choice.

---

## Decision: Empty / dont_know state is sufficient for FR-007

**Decision**: The existing `DontKnowResponse` path renders "I don't have enough information to answer that" + space suggestion. The document browser already shows an empty-state paragraph when `documents.length === 0`. No new UI components are needed for FR-007.

**Rationale**: Both empty states are functional and discoverable. The spec says "clear… state rather than failing silently" — both conditions are already met.

---

## Decision: No server-side conversation persistence

**Decision**: Chat state lives in React component state (`useState` in `ChatInterface`). Navigating to `/documents` and back resets the conversation. The spec explicitly scopes this out: "full server-side conversation persistence is out of scope."

**Rationale**: Implementing `sessionStorage` persistence would be a low-risk addition but is not required by any acceptance criterion. The navigation model (NavBar links → new page load) means conversation state is lost when the user leaves the page, which is consistent with the stated assumption.

**Alternatives considered**:
- `sessionStorage` serialisation: easy but untested; deferred.
- URL-encoded conversation state: impractical for long conversations.

---

## Decision: Mobile navigation — hamburger menu already handles collapse

**Decision**: The existing hamburger-based mobile menu in `NavBar` just needs the "Chat" entry added alongside "Documents". No responsive layout changes are needed for the navigation control itself.

**Rationale**: The current `NavBar` already collapses to a hamburger on `md:hidden` viewports. Adding "Chat" follows the exact same pattern used for all other links. SC-005 requires visibility on mobile — the hamburger reveal satisfies this.
