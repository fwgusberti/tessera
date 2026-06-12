# Tasks: UI Compliance with Implemented Functionality

**Input**: Design documents from `specs/003-fix-ui-compliance/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ui-routes.md ✅ | quickstart.md ✅

**Scope**: Pure frontend additions to `apps/web/`. Zero backend changes required.

**Tests**: Included — constitution mandates ≥85% statement coverage for new `app/` and `components/` files.

**Organization**: Tasks grouped by user story to enable independent implementation, testing, and demo per story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no blocking dependency on incomplete tasks in the same phase)
- **[Story]**: Which user story this task belongs to (US1=Home Dashboard, US2=Document Browsing, US3=Space/Permission Admin, US4=Connectors+Credentials, US5=Metrics Nav)

---

## Phase 1: Setup

**Purpose**: Create the missing directory structure that new pages require.

- [x] T001 Create new directories: apps/web/app/documents/, apps/web/app/documents/[id]/, apps/web/components/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared TypeScript types and a reusable SpaceSelector component used by three different pages (home, /documents, /admin). All user stories that touch multi-space data depend on these.

**⚠️ CRITICAL**: No user story work beyond US5 can reliably begin until this phase is complete.

- [x] T002 [P] Define shared TypeScript entity types (Space, Document, DocumentVersion, Connector, Metrics, AgentCredential) in apps/web/lib/types.ts — use shapes from data-model.md
- [x] T003 [P] Create reusable SpaceSelector component in apps/web/components/SpaceSelector.tsx — props: `spaces: Space[], selectedId: string | null, onChange: (id: string) => void, disabled?: boolean`

**Checkpoint**: Shared types and SpaceSelector ready — all user story phases can now begin.

---

## Phase 3: User Story 5 + User Story 1 — Metrics Nav & Home Dashboard (Priority: P1) 🎯 MVP

**Goal**: Replace the Next.js boilerplate home page with a real Tessera dashboard and make the Metrics page discoverable via navigation.

**Independent Test**: Navigate to `/` — see Tessera stat cards (not Next.js logo). Click "Metrics" in the nav — reach `/metrics`. Both verifiable without any other new page being complete.

### Implementation for User Story 5

- [x] T004 [US5] Add `<a href="/metrics">Metrics</a>` link between "Proposals" and "Admin" in the nav flex row in apps/web/app/layout.tsx

### Tests for User Story 1

- [x] T005 [P] [US1] Write Vitest test for home dashboard in apps/web/tests/home.test.tsx — test: stat cards render with mocked API data; stat cards show "–" when both API calls fail; quick-nav links to /search, /proposals, /metrics, /admin are present

### Implementation for User Story 1

- [x] T006 [US1] Replace apps/web/app/page.tsx with Tessera home dashboard: parallel-fetch `GET /v1/spaces` and `GET /v1/metrics` using `Promise.all`; render three stat cards (Space Count, Total Queries, Documents with Drift) with loading state and "–" fallback on error; render four quick-nav link cards (Search, Proposals, Metrics, Admin)

**Checkpoint**: Home dashboard and Metrics nav link complete. US1 + US5 are fully functional and independently testable.

---

## Phase 4: User Story 2 — Document Browsing and Detail (Priority: P2)

**Goal**: Enable users to browse documents by space, open a document to read its content, view version history, and publish an ingested document.

**Independent Test**: Navigate to `/documents`, select a space, click a document, see content and version list. Click "Publish" on an ingested document and observe state change to "published". Fully verifiable without any admin form changes.

### Tests for User Story 2

- [x] T007 [P] [US2] Write Vitest tests for document browser and detail in apps/web/tests/documents.test.tsx — test: space dropdown populated on mount; selecting space triggers document fetch and renders list with state badges; document detail renders title + state + version count; "Publish" button present only for ingested state; "Publish" button hides on success and shows error on failure

### Implementation for User Story 2

- [x] T008 [P] [US2] Implement document browser page in apps/web/app/documents/page.tsx — on mount fetch `GET /v1/spaces` and render SpaceSelector; on space select fetch `GET /v1/documents?space_id={id}`; render table with columns: Title, State (color-coded badge: ingested=yellow, published=green, archived=gray), Confidentiality; each row is an `<a href="/documents/{id}">` link; show loading state and inline error; show empty-state message when no documents
- [x] T009 [P] [US2] Implement document detail page in apps/web/app/documents/[id]/page.tsx — parallel-fetch `GET /v1/documents/{id}` and `GET /v1/documents/{id}/versions`; render: document title, state badge, confidentiality label, tags; render current version content in `<pre className="whitespace-pre-wrap">` block (or "No content available" if `current_version` is null); render version history table (version number, approved_at, approver_user_id); render "Publish" button only when `document.state === "ingested"` — on click POST `/v1/documents/{id}/publish`, disable button during request, update state to "published" and hide button on success, show inline error on failure

**Checkpoint**: Document browsing, detail, and publish flow fully functional. US2 independently testable.

---

## Phase 5: User Story 3 — Space and Permission Management (Priority: P2)

**Goal**: Allow admins to create new spaces and assign role permissions through the Admin page, replacing the current read-only view.

**Independent Test**: Log in as admin, open `/admin`, fill "Create Space" form, submit, see new space in the table. Fill "Add Permission" form for a space, submit, see success message. Verifiable independently from connectors/credentials.

### Tests for User Story 3

- [x] T010 [P] [US3] Write Vitest tests for admin space management in apps/web/tests/admin.test.tsx — test: "Create Space" form renders required fields; submitting with empty slug shows inline validation error and makes no API call; successful POST /v1/spaces appends space to table and resets form; "Add Permission" form renders space selector and role/confidentiality selects; successful POST shows success message

### Implementation for User Story 3

- [x] T011 [US3] Refactor apps/web/app/admin/page.tsx into a multi-section admin layout — preserve existing spaces table (sourced from `GET /v1/admin/spaces`) and metrics summary; extract spaces data into component-level state reusable by new form sections; add section headings and visual dividers; no functional change to existing display
- [x] T012 [US3] Add "Create Space" form section to apps/web/app/admin/page.tsx below the spaces table — fields: slug (text, required), name (text, required), sector (text, required), default_language (text, default "pt-BR"); client-side validation: block submit if slug or name empty, show inline field error; on submit: POST `/v1/spaces`; on success: append new space to local spaces state, reset form, show inline "Space created" confirmation; on failure: show API error message inline
- [x] T013 [US3] Add "Space Permissions" form section to apps/web/app/admin/page.tsx below "Create Space" — space selector (uses spaces state from T011); fields: idp_group (text, required), role (select: viewer | editor | admin), max_confidentiality (select: public | internal | confidential); on submit: POST `/v1/spaces/{id}/permissions`; on success: show inline "Permission added" message, reset form; on failure: show inline error

**Checkpoint**: Space creation and permission management functional. US3 independently testable alongside US2.

---

## Phase 6: User Story 4 — Connector Management (Priority: P3)

**Goal**: Allow admins to create connectors for a space and trigger manual syncs through the Admin page.

**Independent Test**: Select a space, fill connector form, create connector, click "Sync Now", see job ID returned. Create agent credential, see one-time token displayed, revoke it, see it marked revoked.

### Implementation for User Story 4

- [x] T014 [US4] Add "Connectors" section to apps/web/app/admin/page.tsx — space selector for connector scope; form fields: type (text, required), config (textarea for JSON string, required with JSON.parse validation), schedule (text, optional); on submit: POST `/v1/spaces/{id}/connectors`; on success: add to session-local connector list with name/type/schedule columns and "Sync Now" button; "Sync Now": POST `/v1/connectors/{id}/sync` → display returned `{ job_id }` inline next to the button; note above section: "Connectors created in previous sessions are not listed here"
- [x] T015 [US4] Add "Agent Credentials" section to apps/web/app/admin/page.tsx — form fields: name (text, required), scoped_space_ids (checkbox group from spaces state, at least 1 required), max_confidentiality (select: public | internal | confidential); on submit: POST `/v1/agent-credentials`; on success: display raw `token` value in a highlighted alert box with a copy-to-clipboard button and warning text "This token will not be shown again. Copy it now."; add credential (without token) to session-local list with name/confidentiality/status columns and "Revoke" button; "Revoke": POST `/v1/agent-credentials/{id}/revoke` → update list entry to show "Revoked" status and disable the button

**Checkpoint**: All five user stories complete. Full UI parity with implemented backend API.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Quality assurance across all new pages.

- [x] T016 [P] Audit loading and error states in all new pages — every fetch must show a loading indicator within 100ms and an inline error message (not a crash) on failure; check: apps/web/app/page.tsx, apps/web/app/documents/page.tsx, apps/web/app/documents/[id]/page.tsx, apps/web/app/admin/page.tsx
- [x] T017 [P] Run TypeScript strict type check (tsc --noEmit) in apps/web/ and resolve all type errors in new files
- [x] T018 Run Vitest with coverage (npx vitest run --coverage) in apps/web/ and confirm ≥85% statement coverage for apps/web/app/ and apps/web/components/ — address any gaps before marking done
- [ ] T019 Execute quickstart.md validation scenarios 1–8 against a running environment and confirm all scenarios pass; document any failures as follow-up issues

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (directories exist) — BLOCKS US2, US3, US4
- **Phase 3 (US5+US1)**: T004 can start after Phase 1; T005+T006 depend on Phase 2 (types.ts)
- **Phase 4 (US2)**: Depends on Phase 2 (SpaceSelector + types)
- **Phase 5 (US3)**: Depends on Phase 2 (SpaceSelector + types)
- **Phase 6 (US4)**: Depends on Phase 5 (uses admin page structure from T011)
- **Phase 7 (Polish)**: Depends on all user story phases complete

### User Story Dependencies

- **US5 (P1)**: Depends only on Phase 1 — `layout.tsx` edit needs no shared types
- **US1 (P1)**: Depends on Phase 2 (types.ts for Metrics/Space types) — independent of US2–US4
- **US2 (P2)**: Depends on Phase 2 (SpaceSelector + types) — independent of US1, US3, US4
- **US3 (P2)**: Depends on Phase 2 (SpaceSelector + types) — can run in parallel with US2
- **US4 (P3)**: Depends on US3 being complete (adds sections to admin page built in US3)

### Within Each User Story

- Tests (T005, T007, T010) should be written before or alongside their implementation tasks
- For US3: T011 (refactor) must complete before T012 (create space form) and T013 (permissions form)
- For US4: T014 (connectors) and T015 (credentials) are sequential (same file)

### Parallel Opportunities

- T002 and T003 (Phase 2) can run in parallel — different files
- T004 (US5 nav link) can run alongside T005+T006 (US1) — different files
- T005 (US1 test) and T006 (US1 implementation) can run in parallel — different files
- T007 (US2 test), T008 (document list), T009 (document detail) can all run in parallel — different files
- T010 (US3 test) can run alongside T011 (admin refactor) — different files
- T016 (error audit) and T017 (type check) can run in parallel — different concerns

---

## Parallel Execution Examples

### Phase 2 — Foundational (run together)

```text
Task T002: "Define shared TypeScript entity types in apps/web/lib/types.ts"
Task T003: "Create reusable SpaceSelector component in apps/web/components/SpaceSelector.tsx"
```

### Phase 4 — Document Browsing (run together after Phase 2)

```text
Task T007: "Write Vitest tests for document browser and detail in apps/web/tests/documents.test.tsx"
Task T008: "Implement document browser page in apps/web/app/documents/page.tsx"
Task T009: "Implement document detail page in apps/web/app/documents/[id]/page.tsx"
```

---

## Implementation Strategy

### MVP First (US5 + US1)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete T004 (US5 nav link)
4. Complete T005+T006 (US1 home dashboard)
5. **STOP and VALIDATE**: Home page shows Tessera dashboard; Metrics link is in nav
6. This is demonstrable immediately

### Incremental Delivery

1. Setup + Foundational → shared infra ready
2. US5 + US1 → working dashboard (MVP!)
3. US2 → document browsing + publish flow
4. US3 → space + permission admin forms
5. US4 → connector + credential management
6. Polish → coverage and type-check gates pass

### Parallel Team Strategy

After Phase 2 completes:
- Developer A: US1 (home dashboard)
- Developer B: US2 (document browsing — documents/page.tsx and documents/[id]/page.tsx)
- Developer C: US3 (admin forms — admin/page.tsx refactor + create-space + permissions)
- US4 must wait for US3 (Developer C) to finish T011 before starting T014

---

## Notes

- `[P]` tasks operate on different files; no same-file conflicts
- US4 (T014, T015) is sequential because both add sections to `apps/web/app/admin/page.tsx`
- Backend has no `GET` endpoints for connectors or agent credentials — session-local lists only (documented in research.md Decision 3/4)
- Agent credential raw token must NEVER be stored in localStorage or any persistent browser storage — display in React state only
- All API calls go through `apps/web/lib/api.ts` — no direct `fetch()` calls in new code
- Commit after each task or after each user story checkpoint
