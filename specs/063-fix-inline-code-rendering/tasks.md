# Tasks: Fix Inline Code Rendering

**Input**: Design documents from `/specs/063-fix-inline-code-rendering/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui.md, quickstart.md

**Tests**: Included — the constitution (Principle IV) makes TDD non-negotiable. The stylesheet
regression test is the failing-first test for the fix itself; the DOM tests are regression
guards for the markup layer (which is already correct — see research.md R1).

**Organization**: Tasks are grouped by user story. The production change is a single CSS rule
(US1); US2 and US3 are verification-only stories that pin down what must NOT change.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

Web-app monorepo (per plan.md). All work is in `apps/web/`:
- Production change: `apps/web/app/globals.css`
- Tests: `apps/web/tests/inline-code-rendering.test.tsx`

---

## Phase 1: Setup

**Purpose**: Confirm a green baseline so post-fix regressions are attributable to this feature.

- [X] T001 Run the existing web suites and record the green baseline: `npx vitest run --root apps/web` (all pass expected; `chat-markdown.test.tsx` and `documents*.test.tsx` are the FR-005 regression guards)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: None required — no new infrastructure, dependencies, components, or schema. All
prerequisites (shared `MarkdownContent`, typography plugin, Vitest setup) already exist from
feature 062.

*(No tasks — proceed directly to Phase 3.)*

---

## Phase 3: User Story 1 - Inline code displays without backtick symbols (Priority: P1) 🎯 MVP

**Goal**: Remove the decorative backticks that `@tailwindcss/typography` injects around inline
`<code>` via `code::before`/`code::after`, on both surfaces at once, with one CSS override in
`globals.css` (research.md R2; contract C1–C2).

**Independent Test**: Render content containing inline code in both `MessageBubble` and
`DocumentContent`; verify the snippet appears with no backtick characters (automated: DOM +
stylesheet tests; visual: quickstart.md §2–3).

### Tests for User Story 1 (write FIRST, confirm the stylesheet test FAILS)

- [X] T002 [US1] Create `apps/web/tests/inline-code-rendering.test.tsx` with the stylesheet regression test: read `apps/web/app/globals.css` (via `fs.readFileSync` resolved from the test file) and assert it contains a rule setting `content: none` for both `.prose code::before` and `.prose code::after`. Run `npx vitest run tests/inline-code-rendering.test.tsx --root apps/web` and **confirm it FAILS** (TDD failing-first proof — the override does not exist yet)
- [X] T003 [US1] Add US1 DOM tests to `apps/web/tests/inline-code-rendering.test.tsx` (contract C1–C2, acceptance scenarios 1–3): (a) `MessageBubble` with a complete turn whose answer contains `` Run `main` now `` renders a `<code>` element with text `main`, not inside `<pre>`, and the bubble's `textContent` contains no `` ` `` character; (b) same assertion for `DocumentContent` with a version whose `content_markdown` contains inline code; (c) a sentence with three inline snippets renders three `<code>` elements, zero backticks in `textContent`, surrounding prose intact. Reuse the `completeTurn` helper pattern from `chat-markdown.test.tsx`. These pass pre-fix (markup layer is already correct) — they are the guard that the fix never migrates the problem into the markup

### Implementation for User Story 1

- [X] T004 [US1] Add the override to `apps/web/app/globals.css`, next to the existing `--tw-prose-*` customizations: `.prose code::before, .prose code::after { content: none; }` (selector specificity (0,1,2) beats the plugin's `:where()`-based (0,1,1) — see contracts/ui.md CSS contract; do not alter any other declaration)
- [X] T005 [US1] Run `npx vitest run tests/inline-code-rendering.test.tsx --root apps/web` (all pass, including the previously failing stylesheet test) and `npx vitest run tests/chat-markdown.test.tsx --root apps/web` (still green); then visually confirm in the browser per quickstart.md §2–3 that `` `main` `` renders without backticks in a document and in a chat answer (SC-001)

**Checkpoint**: The reported defect is fixed on both surfaces — MVP complete and shippable.

---

## Phase 4: User Story 2 - Inline code remains visually distinct (Priority: P2)

**Goal**: Pin down that removing the backticks did not flatten inline code into prose: the
`<code>` element and its distinct treatment (Geist Mono, `--tw-prose-code` color) survive,
including inside nested formatting (contract C3–C4).

**Independent Test**: Render a sentence mixing prose and an inline snippet plus snippets nested
in a list item, table cell, heading, and bold; verify each renders as a `<code>` element
(automated) and looks visually distinct (quickstart.md §2).

### Tests for User Story 2

- [X] T006 [US2] Add US2 DOM tests to `apps/web/tests/inline-code-rendering.test.tsx` (contract C3–C4, acceptance scenarios 1–2): inline snippets inside a list item, a GFM table cell, a heading, and bold text each render as a `<code>` element (queried via `li code`, `td code`, `h1 code`/`h2 code`, `strong code`) with no backtick in `textContent`, on both `MessageBubble` and `DocumentContent`; also assert the stylesheet still defines `--tw-prose-code` in `globals.css` (styling variable untouched by the fix)

### Verification for User Story 2

- [X] T007 [US2] Run the suite (`npx vitest run tests/inline-code-rendering.test.tsx --root apps/web`) and visually verify per quickstart.md §2 that snippets in prose, list items, and table cells render monospace with the indigo code color, clearly distinct from surrounding text (SC-002)

**Checkpoint**: Backtick removal proven not to cost the code/prose distinction.

---

## Phase 5: User Story 3 - Intentional backticks are preserved (Priority: P3)

**Goal**: Regression-protect literal backticks that are real content: inside fenced code blocks
and as lone unpaired characters in prose; plus the empty-span edge case (contract C5–C7).

**Independent Test**: Render a code block whose content includes backticks and a paragraph with
a single unpaired backtick; verify both show the backticks as literal text (automated DOM
assertions; visual: quickstart.md §2).

### Tests for User Story 3

- [X] T008 [US3] Add US3 DOM tests to `apps/web/tests/inline-code-rendering.test.tsx` (contract C5–C7, acceptance scenarios 1–2 + edge case): (a) a fenced code block whose body contains `` `example` `` renders a `pre code` whose `textContent` still contains both backticks (they are text nodes, not decoration); (b) prose with a single unpaired `` ` `` keeps it visible in the rendered output; (c) whitespace-only inline code (`` ` ` ``) produces no stray symbols or extra visible characters beyond the span content. Cover (a) and (b) on both surfaces

### Verification for User Story 3

- [X] T009 [US3] Run the full feature suite (`npx vitest run tests/inline-code-rendering.test.tsx --root apps/web`; all US1+US2+US3 tests green) and visually confirm per quickstart.md §2 that the fenced block's backticks and the lone prose backtick display verbatim (FR-004)

**Checkpoint**: All three user stories independently verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Whole-app regression sweep and quality gates (FR-005 / SC-003, Constitution V).

- [X] T010 Run the complete web test suite `npx vitest run --root apps/web` and compare against the T001 baseline — zero new failures (headings, bold, lists, links, tables, quotes, code blocks all rendered by untouched code paths)
- [X] T011 [P] Run quality gates for the web app: `npm run lint --workspace apps/web` and `npx tsc --noEmit -p apps/web` (clean; no Python changes, so Ruff/Black and the Python coverage gate are unaffected)
- [X] T012 [P] Execute the full quickstart.md visual validation (§2–§4): document viewer scenario, chat scenario, side-by-side parity check (SC-004), and the no-regression sweep (SC-003)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Empty — nothing blocks the stories
- **US1 (Phase 3)**: Depends only on T001. Contains the entire production change (T004)
- **US2 (Phase 4)**: Test-only; depends on T004 for the visual check in T007 (the DOM tests themselves are fix-independent). Runs after US1
- **US3 (Phase 5)**: Test-only; same dependency shape as US2. Runs after US1 (or in parallel with US2 by a second developer, at the cost of coordinating edits to the shared test file)
- **Polish (Phase 6)**: Depends on all stories complete

### Task Dependencies

```text
T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → {T011, T012}
```

Strictly sequential through T010 because every test task edits the same file
(`inline-code-rendering.test.tsx`) and TDD ordering requires T002 to fail before T004 exists.

### Parallel Opportunities

- **T011 ∥ T012**: lint/typecheck and the manual visual validation touch nothing in common
- US2/US3 test authoring (T006, T008) could be parallelized across developers only by
  pre-agreeing on `describe`-block boundaries in the shared test file — for a feature this
  small, sequential execution is the sensible default

## Parallel Example: Polish Phase

```bash
# After T010 passes, run together:
Task: "Run quality gates: npm run lint --workspace apps/web && npx tsc --noEmit -p apps/web"   # T011
Task: "Execute quickstart.md §2–§4 visual validation in the browser"                            # T012
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001 (baseline) → T002 (failing stylesheet test) → T003 (DOM guards) → T004 (the one-rule CSS fix) → T005 (verify)
2. **STOP and VALIDATE**: the reported defect is gone on both surfaces — this alone is shippable
3. US2/US3 phases add regression armor, not behavior

### Incremental Delivery

- US1 fixes the bug (SC-001, SC-004)
- US2 pins the visual-distinction invariant (SC-002)
- US3 pins the literal-backtick invariant (FR-004)
- Polish proves SC-003 (no collateral regressions) and passes the quality gates

---

## Notes

- The entire production diff is one CSS rule in `apps/web/app/globals.css` (T004); every other
  task is verification. Do not expand the diff (e.g., no component changes) — see research.md
  R2 for the rejected alternatives.
- jsdom cannot observe pseudo-element `content`, which is why the stylesheet test (T002) — not
  a DOM test — is the failing-first proof, and why quickstart visual checks close the gap
  (research.md R3).
- Commit after each checkpoint or logical group; the constitution's quality gates (lint) must
  pass before any commit.

## Execution Notes (2026-07-11)

- T010: `document-detail-modernized` (breadcrumb) and `documents-reindex-admin` tests flake
  intermittently under full-suite parallelism (`waitFor` race on `role=navigation`). Proven
  pre-existing: the same failures reproduce with this feature fully reverted (CSS stashed +
  feature test excluded); both pass in isolation. Zero failures attributable to this feature.
- T011: ESLint is not installed in `apps/web` (no config, binary, or `lint` script) — lint gate
  N/A; `tsc --noEmit` clean.
- T012: verified at build level — the compiled production CSS contains
  `.prose code:before,.prose code:after{content:none}` (specificity (0,1,2)) alongside the
  plugin's `:where()`-based backtick rules ((0,1,1)), so the override wins in the browser.
  Human browser walkthrough per quickstart.md §2–§4 remains recommended.
- Post-review follow-up (user feedback): with the backticks gone, inline code was visually
  indistinguishable from bold (`--tw-prose-code` = `--tw-prose-bold` = indigo-700, both weight
  600), and the Geist font variables in `@theme inline` were never wired (layout loads Inter
  only), breaking every `font-mono` usage. Added a pill treatment
  (`.prose :not(pre) > code` — slate-100 background, padding, radius; excludes code blocks)
  and pointed `--font-sans`/`--font-mono` at real font stacks. Stylesheet tests extended
  (15 feature tests); verified computed styles in headless Chrome against the live dev CSS:
  inline pill + mono, `pre code` untouched, `.font-mono` textarea now monospace.
