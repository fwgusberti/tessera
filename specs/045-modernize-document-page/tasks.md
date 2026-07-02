---

description: "Task list for Modernize Document Page"

---

# Tasks: Modernize Document Page

**Input**: Design documents from `/specs/045-modernize-document-page/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/reused-endpoints.md, quickstart.md

**Tests**: Included and REQUIRED — `plan.md`'s Constitution Check commits this feature to Test-Driven Development (Constitution Principle IV): Vitest tests for markdown rendering, breadcrumb composition, version history states, and action-restyle parity are written first and must fail before the corresponding implementation exists.

**Organization**: Tasks are grouped by user story (from `spec.md`) to enable independent implementation and testing of each story. This is a frontend-only feature confined to `apps/web` — no `apps/api` or database changes (see `research.md` and `contracts/reused-endpoints.md`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task includes an exact file path

## Path Conventions

All paths are under `apps/web/` (existing Next.js App Router frontend). No backend paths are touched by this feature.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the new rendering/styling dependencies every later phase needs

- [X] T001 Add `react-markdown` (`^9`) and `remark-gfm` (`^4`) as runtime dependencies and `@tailwindcss/typography` (`^0.5`) as a dev dependency in `apps/web/package.json`, then run `npm install` in `apps/web` (research.md §1-2)
- [X] T002 Register the typography plugin in `apps/web/app/globals.css` via a `@plugin "@tailwindcss/typography";` directive (this project has no `tailwind.config.js` — Tailwind v4 CSS-first config), and override `--tw-prose-links`, `--tw-prose-code`, and `--tw-prose-bold` to use `indigo-600`/`indigo-700` instead of the plugin's default blue (research.md §2; depends on T001 for the package to exist)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared test scaffolding every user story's test tasks build on

**⚠️ CRITICAL**: No user story test/implementation work can begin until this phase is complete

- [X] T003 [P] Create `apps/web/tests/document-detail-modernized.test.tsx` test file skeleton: mock `@/lib/api` (`get`/`post`), `@/lib/auth` (`useAuth`), `@/lib/auth-guard` (`AuthGuard` passthrough), and `next/navigation` (`useParams` → `{ id: "d1" }`), following the pattern in `apps/web/tests/documents-reindex-admin.test.tsx`; add shared fixtures with no assertions yet: a document in a nested space (`space_id: "s2"`), an ancestors response `{ ancestors: [{ id: "s1", name: "Engineering", slug: "engineering" }] }`, an own-space response `{ space: { id: "s2", name: "Backend", slug: "backend", ... } }` (note the `{ space: {...} }` envelope — see `apps/api/tessera_api/routers/spaces.py:164-192`), a current version whose `content_markdown` contains a heading, a list, and a fenced code block, a 3-version list, and a zero-version list

**Checkpoint**: Foundation ready — user story work can now begin

---

## Phase 3: User Story 1 - Read a document in a modern, consistent layout (Priority: P1) 🎯 MVP

**Goal**: Replace the raw `<pre>` content block with rendered rich text, restyle the header (tags as pills, consistent typography), and add a full breadcrumb trail reflecting the document's space location.

**Independent Test**: Open a document's detail page and confirm the header, breadcrumb, and content area use the app's modern visual language, that formatted markdown (headings/lists/code) renders as distinct elements rather than raw source, and that a document in a nested space shows a full clickable ancestor trail.

### Tests for User Story 1 ⚠️

> Write these tests FIRST, run them, and confirm they FAIL before implementing anything below

- [X] T004 [P] [US1] In `apps/web/tests/document-detail-modernized.test.tsx`, add a test asserting the nested-space document's current version renders its heading, list, and code block as distinct elements (`getByRole("heading")`, `getAllByRole("listitem")`, a `<code>`/`<pre>` element) rather than raw `#`/`-`/backtick characters in text content (FR-002, SC-002)
- [X] T005 [P] [US1] In `apps/web/tests/document-detail-modernized.test.tsx`, add a test asserting the breadcrumb renders "Root › Engineering › Backend › {document title}" — the ancestor and own-space segments as links to `/spaces/{id}`, the document title as non-clickable trailing text — using the T003 ancestors/own-space fixtures (FR-008, Acceptance Scenario 3)
- [X] T006 [P] [US1] In `apps/web/tests/document-detail-modernized.test.tsx`, add a test asserting that when the `GET /v1/spaces/{id}` or `GET /v1/spaces/{id}/ancestors` call rejects (or resolves without the expected `space`/`ancestors` fields), the page still renders the document, content, actions, and version history, falling back to a plain "← Documents" link instead of crashing or showing an incorrect location (Constitution VI isolation test; `contracts/reused-endpoints.md` "Failure handling")
- [X] T007 [P] [US1] In `apps/web/tests/document-detail-modernized.test.tsx`, add a test asserting the header renders each entry in `document.tags` as an individual pill/chip element rather than a single comma-joined string (FR-001, research.md §5)
- [X] T008 [US1] Extend `apps/web/tests/documents-reindex-admin.test.tsx`: add `/v1/spaces/s1` and `/v1/spaces/s1/ancestors` entries to the existing `mockApi.get.mockImplementation` (returning a same-shape `{ space: {...} }` / `{ ancestors: [...] }` pair), and assert the breadcrumb renders correctly alongside the existing admin-reindex-button assertion (plan.md Project Structure)

### Implementation for User Story 1

- [X] T009 [P] [US1] Create `apps/web/components/documents/DocumentContent.tsx`: renders a `{ version: DocumentVersion | null }` prop's `content_markdown` via `react-markdown` + `remark-gfm` (no `rehype-raw`) inside a `prose prose-slate max-w-none` wrapper; renders the existing "No content available for this document." empty-state message when `version` is `null` (FR-002, FR-006, research.md §1-2)
- [X] T010 [US1] Update `apps/web/app/documents/[id]/page.tsx`: once `document` is loaded, add an independent `GET /v1/spaces/{document.space_id}` + `GET /v1/spaces/{document.space_id}/ancestors` fetch in its own try/catch (separate from the existing document/versions `Promise.all`, so a failure here never blocks the main page render); on success, compose `[...ancestors, { id: space.id, name: space.name, slug: space.slug }]` (reading the space from the `{ space: {...} }` envelope) and render the existing `SpaceBreadcrumb` (`@/components/spaces/SpaceBreadcrumb`) with `currentName={document.title}`; on failure or a malformed/missing response, keep today's plain "← Documents" link (data-model.md; research.md §3; `contracts/reused-endpoints.md`)
- [X] T011 [US1] Update `apps/web/app/documents/[id]/page.tsx` header block: replace `document.tags.join(", ")` with a `flex flex-wrap gap-1` row of individual pill/chip `<span>`s (matching the existing `STATE_STYLES` pill treatment), and align title/status/confidentiality spacing with the Spaces folder browser's visual language (FR-001, research.md §5)
- [X] T012 [US1] Update `apps/web/app/documents/[id]/page.tsx` "Current Content" section to render `<DocumentContent version={currentVersion} />` (T009) in place of the raw `<pre>{currentVersion.content_markdown}</pre>` block (FR-002)
- [X] T013 [US1] Update `apps/web/app/documents/[id]/page.tsx` loading/error/not-found states (currently plain `<p>` tags) to a styled empty-state treatment consistent with the Spaces folder browser (e.g. centered message in a bordered container) (FR-007)

**Checkpoint**: User Story 1 is fully functional and independently testable — modern layout, formatted content, and breadcrumb work end-to-end.

---

## Phase 4: User Story 2 - Take document actions with clear, modern controls (Priority: P2)

**Goal**: Restyle the Publish/Reindex controls and their loading/success/error feedback to match the app's modern action-control convention, with zero change to eligibility rules or request/response handling.

**Independent Test**: As an eligible user, publish an ingested document and reindex a published document, confirming each action shows a modern-styled control with correct loading/success/error feedback, and that ineligible users still do not see actions they cannot perform.

### Tests for User Story 2 ⚠️

> Write these tests FIRST, run them, and confirm they FAIL before implementing anything below

- [X] T014 [P] [US2] In `apps/web/tests/document-detail-modernized.test.tsx`, add a test asserting the Publish button still shows a loading state then reflects the published state after a successful publish (parity check on the restyled control) (FR-003, Acceptance Scenario 1)
- [X] T015 [P] [US2] In `apps/web/tests/document-detail-modernized.test.tsx`, add a test asserting a failed publish/reindex action shows a clearly styled inline error message near the action without hiding or breaking the rest of the page (FR-003, Acceptance Scenario 3)

### Implementation for User Story 2

- [X] T016 [US2] Update `apps/web/app/documents/[id]/page.tsx`: restyle the Publish button and its loading/error feedback to match the modernized action-control convention used elsewhere in the app (e.g. `AddDocumentModal`'s/`SetParentModal`'s primary button — `rounded`, `focus:ring-2 focus:ring-indigo-500`, `disabled:opacity-50`), preserving `handlePublish`'s existing logic, state, and copy unchanged (FR-003)
- [X] T017 [US2] Update `apps/web/app/documents/[id]/page.tsx`: restyle the Reindex button and its queued-message/error feedback the same way, preserving `handleReindex`'s existing logic, the 3-second auto-dismiss timer, and the `canReindex` eligibility check unchanged (FR-003)

**Checkpoint**: User Stories 1 AND 2 both work independently — layout/content/breadcrumb and restyled actions.

---

## Phase 5: User Story 3 - Scan version history at a glance (Priority: P3)

**Goal**: Replace the bare `<table>` version history with a modern, scannable, unpaginated list of version cards.

**Independent Test**: Open a document with 3+ versions and confirm each version's number, approval date/time, and approver are legible and visually distinct; open a document with no versions and confirm a styled empty state replaces the empty table.

### Tests for User Story 3 ⚠️

> Write these tests FIRST, run them, and confirm they FAIL before implementing anything below

- [X] T018 [P] [US3] In `apps/web/tests/document-detail-modernized.test.tsx`, add a test using the T003 3-version fixture asserting each version's number, approval date/time, and approver render as a scannable list of rows, with no `<table>` element present in the rendered output (FR-004, Acceptance Scenario 1)
- [X] T019 [P] [US3] In `apps/web/tests/document-detail-modernized.test.tsx`, add a test using the T003 zero-version fixture asserting a clear, styled empty-state message renders in place of the version history table (FR-006, Acceptance Scenario 2)

### Implementation for User Story 3

- [X] T020 [P] [US3] Create `apps/web/components/documents/VersionHistory.tsx`: renders a `{ versions: DocumentVersion[] }` prop as a vertically stacked list of bordered rows (`bg-white rounded border border-slate-200`, matching `DocumentTile`'s card treatment), each showing version number, formatted approval date/time (or "—"), and approver (or "—"); renders a styled empty-state message when `versions.length === 0`; no pagination control (FR-004, FR-006, research.md §4)
- [X] T021 [US3] Update `apps/web/app/documents/[id]/page.tsx` "Version History" section to render `<VersionHistory versions={versions} />` (T020) in place of the raw `<table>` markup (FR-004)

**Checkpoint**: All three user stories are independently functional — this is the full feature.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T022 [P] Run `quickstart.md` scenarios 1-7 manually against local `apps/web` + `apps/api` dev servers, including the 360px responsive check (Scenario 6), confirming each expected outcome
- [X] T023 [P] Search the repository for any other reference assuming the old raw `<pre>`/`<table>` document rendering (docs, other tests, comments) and update or remove stale references
- [X] T024 Run the full `apps/web` Vitest suite (`npx vitest run` from `apps/web/`) and confirm all new/extended tests pass with zero regressions in existing suites (`documents.test.tsx`, `documents-reindex-admin.test.tsx`, spaces tests, etc.)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: No dependency on Setup completing first (different files) — BLOCKS all user story test/implementation work
- **User Story 1 (Phase 3)**: Depends on Setup (T001-T002) and Foundational (T003)
- **User Story 2 (Phase 4)**: Depends on Foundational (T003) only — touches the same `page.tsx` header/action area as US1 but is functionally independent of US1's breadcrumb/content changes; sequence after US1 to avoid concurrent edits to the same file
- **User Story 3 (Phase 5)**: Depends on Foundational (T003) only — independent of US1 and US2; sequence after both, or in parallel by a second developer once US1 lands, to avoid concurrent edits to `page.tsx`
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories — delivers the core modernized layout, content rendering, and breadcrumb
- **User Story 2 (P2)**: No functional dependency on US1; shares `apps/web/app/documents/[id]/page.tsx` as an edit target, so should be sequenced (or carefully merged) relative to US1
- **User Story 3 (P3)**: No functional dependency on US1 or US2; shares `apps/web/app/documents/[id]/page.tsx` as an edit target, so should be sequenced (or carefully merged) relative to the others

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- New components (`DocumentContent.tsx`, `VersionHistory.tsx`) before their integration into `page.tsx`
- Story complete and checkpointed before moving to the next priority

### Parallel Opportunities

- T001 and T002 (Setup) are sequential (T002's `@plugin` line needs T001's package present) but both can start immediately
- T003 (Foundational) can start immediately, independent of Setup
- T004, T005, T006, T007 (US1 tests) can run in parallel — same file, additive `it()` blocks with no shared state
- T009 (US1: `DocumentContent.tsx`) can be built in parallel with the US1 tests — different file
- T014, T015 (US2 tests) can run in parallel
- T018, T019 (US3 tests) can run in parallel
- T020 (US3: `VersionHistory.tsx`) can be built in parallel with the US3 tests — different file
- Once Foundational (T003) is done, US2 and US3 implementation could proceed in parallel by different developers since neither touches `DocumentContent.tsx`/`VersionHistory.tsx`/the breadcrumb fetch — but both edit `apps/web/app/documents/[id]/page.tsx`, so those edits should be coordinated or merged sequentially

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together (same file, independent it() blocks):
Task: "Add markdown-rendering test to document-detail-modernized.test.tsx"
Task: "Add breadcrumb-composition test to document-detail-modernized.test.tsx"
Task: "Add breadcrumb-degradation test to document-detail-modernized.test.tsx"
Task: "Add tag-pill test to document-detail-modernized.test.tsx"

# DocumentContent can be built alongside the tests:
Task: "Create apps/web/components/documents/DocumentContent.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003)
3. Complete Phase 3: User Story 1 (T004-T013)
4. **STOP and VALIDATE**: Run `quickstart.md` Scenarios 1, 2, 6, 7 — breadcrumb, formatted content, responsive check, breadcrumb degradation
5. Demo if ready — this alone already replaces the raw `<pre>` text and bare breadcrumb-less header with the modernized reading experience

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. User Story 1 → validate via `quickstart.md` Scenarios 1, 2, 6, 7 → demo (MVP)
3. User Story 2 → validate via `quickstart.md` Scenario 3 → demo
4. User Story 3 → validate via `quickstart.md` Scenario 4 → demo
5. Polish (T022-T024) → full regression pass

### Parallel Team Strategy

1. One developer completes Setup + Foundational + User Story 1 (the shared foundation)
2. Once US1 lands, a second developer can pick up User Story 3 (version history) while the first continues to User Story 2 (action restyle) — they touch different new component files but both edit `apps/web/app/documents/[id]/page.tsx`, which should be coordinated

---

## Notes

- No backend/database tasks appear in this list — every endpoint used already exists and is already tenant-scoped and authorization-checked (see `contracts/reused-endpoints.md`); this is deliberate, not an oversight
- [P] tasks touch different files (or independent, non-conflicting additions to the same test file) with no unmet dependency
- Verify each test fails before writing its implementation (Constitution Principle IV)
- Commit after each task or logical group
- Stop at any checkpoint (end of Phase 3, 4, or 5) to validate a story independently before continuing
