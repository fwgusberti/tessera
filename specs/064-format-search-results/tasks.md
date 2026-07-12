# Tasks: Formatted Search Results with Document Navigation

**Input**: Design documents from `/specs/064-format-search-results/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/search-result-card.md, quickstart.md

**Tests**: INCLUDED — Constitution Principle IV (Test-Driven Development) is non-negotiable and research R5 mandates test-first component tests in `apps/web/tests/search.test.tsx`. Each story writes failing tests before implementation.

**Organization**: Tasks are grouped by user story. Note: both stories modify the same two files (`apps/web/app/search/page.tsx` and `apps/web/tests/search.test.tsx`), so tasks are intentionally sequential — no same-file `[P]` conflicts exist in this feature.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in descriptions

## Path Conventions

Monorepo web app — all paths are repository-root relative under `apps/web/` (Next.js 15 App Router). No backend (`apps/api`) changes.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm a green baseline before test-first work begins — no scaffolding is needed (all dependencies already installed: `react-markdown`, `remark-gfm`, `@tailwindcss/typography`, Vitest + Testing Library).

- [X] T001 Establish test baseline: run `npx vitest run tests/search.test.tsx` from `apps/web/` and confirm all existing search page tests pass before any modification; record any pre-existing failures so they are not attributed to this feature

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extend the shared `MarkdownContent` component with the optional `components` prop that US1's snippet rendering depends on, without breaking its existing call sites (document page `DocumentContent`, chat `MessageBubble`).

**⚠️ CRITICAL**: US1 implementation (T005) cannot start until this phase is complete.

- [X] T002 Extend `apps/web/components/markdown/MarkdownContent.tsx` with an optional `components?: Components` prop (type imported from `react-markdown`): merge caller-provided entries over the component's own `openLinksInNewTab` link override so caller entries take precedence, per contracts/search-result-card.md § Component contract; keep the prop optional with unchanged behavior when omitted
- [X] T003 Regression-check existing `MarkdownContent` callers: run the full web suite (`npx vitest run` from `apps/web/`) and confirm document page and chat tests still pass with the extended component

**Checkpoint**: `MarkdownContent` accepts caller overrides; all existing tests green — user story work can begin.

---

## Phase 3: User Story 1 - Readable, Formatted Search Result Snippets (Priority: P1) 🎯 MVP

**Goal**: Each search-mode result card shows the document title prominently on top (with `"Untitled document"` fallback) and, below it, the excerpt rendered as compact, safe, contained Markdown instead of raw source, with the score still visible.

**Independent Test**: Search a term matching a Markdown-rich document and verify the result card shows the title on top and a formatted (not raw) excerpt below it — automated via `npx vitest run tests/search.test.tsx`, manually via quickstart.md steps 1, 3, 4, 5.

### Tests for User Story 1 ⚠️ write FIRST, confirm they FAIL

- [X] T004 [US1] Add failing component tests to `apps/web/tests/search.test.tsx` (existing mock pattern: `vi.mock("@/lib/api")`, mocked `AuthGuard`) covering: (a) `citation.document_title` renders at the top of the card, above and visually more prominent than the excerpt (FR-001); (b) a result with missing/empty title renders the `"Untitled document"` fallback (FR-008); (c) a snippet containing `**bold**` renders a `<strong>` element and no literal `**` text (FR-002); (d) a snippet containing `# Heading` renders the heading text without an element at page-title scale — assert the compact override, not a default `<h1>` style (FR-005); (e) a snippet containing `<script>alert(1)</script>` and `<img src=x onerror=...>` mounts no `script`/`img` element inside the card — the markup appears only as escaped text (FR-003); (f) the score remains visible as a percentage, e.g. `87%` for `score: 0.87` (FR-009). Run `npx vitest run tests/search.test.tsx` and confirm the new tests FAIL against the current raw-snippet implementation

### Implementation for User Story 1

- [X] T005 [US1] Rework the search-mode result card in `apps/web/app/search/page.tsx` (the `results.map` block): header row with the document title (`r.citation.document_title` trimmed, falling back to `"Untitled document"`) styled prominently (`text-sm font-semibold text-slate-900`) and the existing score badge kept on the right; remove the old raw `<p>{r.snippet}</p>` and title-as-footnote; render the excerpt below via `<MarkdownContent content={r.snippet} className="prose prose-sm max-w-none ..." components={snippetOverrides} />` where `snippetOverrides` downscales `h1`–`h6` to a single compact style (`text-sm font-semibold`, tight margins); apply `overflow-hidden break-words` containment on the card body so malformed/truncated Markdown stays inside the card (FR-004); follow the design system (slate neutrals, no gray-*/blue-*)
- [X] T006 [US1] Run `npx vitest run tests/search.test.tsx` from `apps/web/` and confirm all T004 tests now PASS with no regressions in the pre-existing search tests

**Checkpoint**: Search results are readable, formatted, safe, and contained — US1 is independently deliverable as the MVP.

---

## Phase 4: User Story 2 - Navigate to a Document from a Search Result (Priority: P2)

**Goal**: The entire result card is a clickable, keyboard-accessible link target that navigates client-side to `/documents/{document_id}`, with clear hover affordance, predictable behavior for links inside the excerpt, and Back returning to the search page.

**Independent Test**: Click any search result (or focus it and press Enter) and verify the router navigates to `/documents/{document_id}` — automated via `npx vitest run tests/search.test.tsx` with a mocked router, manually via quickstart.md step 2.

### Tests for User Story 2 ⚠️ write FIRST, confirm they FAIL

- [X] T007 [US2] Add a `next/navigation` router mock (`vi.mock("next/navigation")` exposing a spy `push`, following the pattern used in other web tests) to `apps/web/tests/search.test.tsx`, then add failing tests covering: (a) clicking anywhere on a result card calls `router.push("/documents/{document_id}")` (FR-006); (b) pressing Enter (and Space) with the card focused triggers the same navigation (FR-006); (c) the card exposes `role="link"`, `tabIndex={0}`, and a pointer-cursor/hover-state class (FR-007); (d) a snippet containing a Markdown link `[text](https://example.com)` renders as styled non-anchor text — no `<a>` element inside the card — and clicking it triggers card navigation to the document, not the external URL (edge case, research R3). Run `npx vitest run tests/search.test.tsx` and confirm the new tests FAIL

### Implementation for User Story 2

- [X] T008 [US2] Implement card navigation in `apps/web/app/search/page.tsx`: import `useRouter` from `next/navigation`; on each result card add `role="link"`, `tabIndex={0}`, `cursor-pointer`, hover feedback per design system (`hover:border-indigo-500 hover:bg-slate-50` style affordance), `onClick` and `onKeyDown` (Enter/Space, preventing default page scroll on Space) calling `router.push(\`/documents/${r.document_id}\`)`; extend `snippetOverrides` with an `a` → `span` override that keeps the link color but never navigates, so a click anywhere in the card does exactly one thing (research R3); do NOT wrap the card in `next/link` (avoids nested `<a>`)
- [X] T009 [US2] Run `npx vitest run tests/search.test.tsx` from `apps/web/` and confirm all T007 tests now PASS with US1 tests still green

**Checkpoint**: Search-to-read loop closed — both stories independently functional.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Whole-suite regression, static checks, and end-to-end validation per quickstart.md.

- [X] T010 Run the full web suite (`npx vitest run` from `apps/web/`) to confirm no regressions in other `MarkdownContent` callers (document page, chat) or any other page
- [X] T011 [P] Run the web static gates from `apps/web/`: `npx tsc --noEmit` (or the repo's typecheck script) and `npm run lint`; fix any violations introduced by this feature
- [X] T012 Execute the manual end-to-end validation in `specs/064-format-search-results/quickstart.md` (backend stack up, `npm run dev` in `apps/web`): formatted snippet + title, click/hover/Back navigation, script-injection safety, truncated-Markdown containment, fallback title — confirm SC-001 through SC-004

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on T001 baseline — BLOCKS US1 implementation (T005); does not block US2's test writing conceptually, but see file-conflict note below
- **User Story 1 (Phase 3)**: Depends on Phase 2 (T005 consumes the new `components` prop)
- **User Story 2 (Phase 4)**: Depends on Phase 2 completion; independent of US1 in behavior, but T007/T008 edit the same files as T004/T005 — execute after Phase 3 to avoid same-file conflicts
- **Polish (Phase 5)**: Depends on all desired story phases being complete

### Task Dependencies

- T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → (T011 ∥ T012)

### Within Each User Story

- Tests are written and confirmed FAILING before implementation (T004 before T005; T007 before T008)
- Verification run closes each story (T006, T009)

### Parallel Opportunities

Minimal by design: every story task touches `apps/web/app/search/page.tsx` and/or `apps/web/tests/search.test.tsx`, so `[P]` markers would create same-file conflicts. The only genuine parallel pair is in Polish: **T011** (typecheck/lint) can run alongside **T012** (manual quickstart validation) once T010 is green. With two developers, one could take Phase 2 (`MarkdownContent.tsx`) while the other drafts T004's test cases, merging before T005.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (baseline) and Phase 2 (`MarkdownContent` extension + regression)
2. Complete Phase 3: failing tests → card rework → green
3. **STOP and VALIDATE**: run `npx vitest run tests/search.test.tsx` and quickstart.md steps 1/3/4/5 — formatted, safe, contained snippets with titles ship value on their own
4. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → shared component ready, everything green
2. US1 → test independently → deploy/demo (MVP: readability fix)
3. US2 → test independently → deploy/demo (navigation closes the loop)
4. Polish → full regression + static gates + manual E2E

---

## Notes

- Frontend-only: no Python modules change, so the 85% Python coverage gate (Constitution IV) and Ruff/Black gates (Constitution V) are not triggered; web lint/typecheck still apply (T011)
- No new data-access path: tenant isolation is enforced by the existing `POST /v1/search` and `GET /v1/documents/{id}` endpoints (plan.md § Tenant Isolation) — no new isolation tests required
- Do not add `rehype-raw` or any HTML-enabling plugin: react-markdown's default escaping is the FR-003 safety mechanism
- Design system (Constitution § UI Design System): slate neutrals, indigo-600/700/500 accents only — no `gray-*`/`blue-*`
- Commit after each task or logical group; stop at any checkpoint to validate the story independently
