# Tasks: Frontend Spaces Page

**Input**: Design documents from `/specs/040-frontend-spaces-page/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Required — Constitution Principle IV (TDD non-negotiable); plan.md mandates Vitest tests for all new components and page; coverage target 85% for new files.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete-task dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in all task descriptions

## Path Conventions

- **Pages**: `apps/web/app/<route>/page.tsx`
- **Components**: `apps/web/components/<domain>/Component.tsx`
- **Tests**: `apps/web/tests/<name>.test.tsx`
- **Types**: `apps/web/lib/types.ts`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add TypeScript types that all user story phases depend on

- [X] T001 Add `SpaceRole` union type (`"admin" | "editor" | "viewer"`), `MySpaceMembership` interface, and `SpaceWithRole` interface to `apps/web/lib/types.ts`

---

## Phase 2: User Story 1 — Browse Available Spaces (Priority: P1) 🎯 MVP

**Goal**: Users visiting `/spaces` see an alphabetically sorted list of all accessible spaces in the active company, each displayed as a card with name, sector, and role badge.

**Independent Test**: Log in, navigate to `http://localhost:3000/spaces`, confirm space cards render with name, sector, and role badge; confirm alphabetical order; confirm empty-state message renders when there are no spaces; confirm error message renders when the API fails; confirm unauthenticated users are redirected to `/login?redirect=%2Fspaces`.

### Tests for User Story 1 ⚠️ Write FIRST — confirm they FAIL before implementing

- [X] T002 [P] [US1] Write failing Vitest tests for `SpaceCard` component (name display, sector display, `RoleBadge` renders correct role, null role renders no badge, long space name does not overflow layout) in `apps/web/tests/space-card.test.tsx`
- [X] T003 [P] [US1] Write failing Vitest tests for `SpacesPage` (loading state, empty-state message when API returns empty list, error message when `GET /v1/spaces` fails, correct number of cards rendered, cards sorted alphabetically by name, auth redirect to `/login?redirect=%2Fspaces` when unauthenticated) in `apps/web/tests/spaces.test.tsx`

### Implementation for User Story 1

- [X] T004 [US1] Implement `SpaceCard` component displaying space `name`, `sector`, and the existing `RoleBadge` component (`apps/web/components/members/RoleBadge.tsx`) for the user's role; renders no badge when role is `null`; use `slate-*` neutrals and `indigo-600`/`indigo-700` accents per UI constitution in `apps/web/components/spaces/SpaceCard.tsx` (depends on T002)
- [X] T005 [US1] Implement `SpacesPage`: auth guard via `useAuth` (redirect to `/login?redirect=%2Fspaces` when unauthenticated), fetch `GET /v1/spaces`, parallel role fetches via `Promise.allSettled` over `GET /v1/spaces/{id}/members/me` (404 → `role: null`, non-fatal), loading/empty/error UI states (FR-005, FR-006), and `localeCompare` alphabetical sort before render in `apps/web/app/spaces/page.tsx` (depends on T003, T004)

**Checkpoint**: Visit `/spaces` with a logged-in user — space cards render with name, sector, and role badges, sorted A → Z. User Story 1 is independently functional.

---

## Phase 3: User Story 2 — Navigate to Space Members (Priority: P2)

**Goal**: Each space card exposes a "Members" link to `/spaces/{id}/members` and a "Documents" link to `/documents?space={id}`; both are available to all authenticated users regardless of role.

**Independent Test**: Navigate to `/spaces`, click "Members" on any card → confirm arrival at `/spaces/{id}/members`. Click "Documents" on any card → confirm arrival at `/documents?space={id}` pre-filtered to that space. Press browser Back → confirm return to `/spaces`.

### Tests for User Story 2 ⚠️ Write FIRST — confirm they FAIL before implementing

- [X] T006 [P] [US2] Add failing Vitest tests for action links on `SpaceCard`: "Members" link has `href="/spaces/{id}/members"`, "Documents" link has `href="/documents?space={id}"`, both links present for all role values and for null role in `apps/web/tests/space-card.test.tsx`

### Implementation for User Story 2

- [X] T007 [US2] Add "Members" (`/spaces/${space.id}/members`) and "Documents" (`/documents?space=${space.id}`) action links to `SpaceCard` component in `apps/web/components/spaces/SpaceCard.tsx` (depends on T006)

**Checkpoint**: Space cards now show both navigation links. User Stories 1 and 2 are functional end-to-end.

---

## Phase 4: User Story 3 — Access Spaces from Navigation (Priority: P3)

**Goal**: Authenticated users see a "Spaces" link in the NavBar that is visually highlighted (indigo active state) on any `/spaces/*` route; unauthenticated users do not see the link.

**Independent Test**: While authenticated on any page, confirm "Spaces" link appears in the NavBar. Click it and confirm navigation to `/spaces`. Confirm the link is highlighted when on `/spaces` or `/spaces/[id]/members`. Log out and confirm the link is absent.

### Tests for User Story 3 ⚠️ Write FIRST — confirm they FAIL before implementing

- [X] T008 [P] [US3] Add failing Vitest tests for "Spaces" NavBar link: present and links to `/spaces` when authenticated, visually active (aria or class check) when `pathname` starts with `/spaces`, absent when unauthenticated in `apps/web/tests/navbar.test.tsx`

### Implementation for User Story 3

- [X] T009 [US3] Add "Spaces" link to `NavBar` using `pathname.startsWith("/spaces")` for active-state detection (mirrors existing Documents link pattern) with `indigo-600`/`indigo-700` active styling; hidden for unauthenticated users in `apps/web/components/NavBar.tsx` (depends on T008)

**Checkpoint**: All three user stories are complete and independently testable.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Coverage gate and end-to-end quickstart validation

- [X] T010 [P] Run `cd apps/web && npm test -- --coverage` and confirm ≥ 85% statement coverage on `app/spaces/page.tsx`, `components/spaces/SpaceCard.tsx`, and changed `components/NavBar.tsx` (Constitution Principle IV)
- [X] T011 Run all 6 validation scenarios from `specs/040-frontend-spaces-page/quickstart.md` against running dev server (`cd apps/web && npm run dev`) to confirm end-to-end correctness

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **US1 (Phase 2)**: Depends on T001 (types) — BLOCKS US2 implementation (SpaceCard must exist)
- **US2 (Phase 3)**: Depends on T004 (SpaceCard must exist to add links)
- **US3 (Phase 4)**: Depends on T001 only — **fully independent of US1 and US2** (touches only `NavBar.tsx`)
- **Polish (Phase 5)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Depends on T001; no dependency on US2 or US3
- **US2 (P2)**: Depends on T004 (SpaceCard component); no dependency on US3
- **US3 (P3)**: Depends on T001 only — can proceed in parallel with US1 and US2

### Within Each User Story (TDD Order)

1. Write tests → confirm they **FAIL**
2. Implement until tests **PASS**
3. Verify checkpoint before moving to the next story

### Parallel Opportunities

- T002 and T003 run in parallel (different test files)
- T006 and T008 run in parallel (different test files, independent stories)
- US3 (T008 → T009) can be worked in parallel with US1/US2 (independent file: `NavBar.tsx`)
- T010 and T011 in Polish run in parallel

---

## Parallel Example: User Story 1

```bash
# Step 1 — write tests in parallel (both files independent)
Task T002: Write SpaceCard tests in apps/web/tests/space-card.test.tsx
Task T003: Write SpacesPage tests in apps/web/tests/spaces.test.tsx

# Step 2 — implement sequentially within the story
Task T004: Implement SpaceCard (after T002 written and confirmed FAILING)
Task T005: Implement SpacesPage (after T003 written + T004 complete)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: User Story 1 (T002 + T003 in parallel → T004 → T005)
3. **STOP and VALIDATE**: Visit `/spaces` — confirm live listing
4. Deploy/demo if ready — MVP is a fully functional, tested Spaces listing page

### Incremental Delivery

1. Phase 1 + Phase 2 (US1): Spaces listing with role badges → **MVP**
2. Phase 3 (US2): Members + Documents links → navigate from the listing
3. Phase 4 (US3): NavBar "Spaces" link → full discoverability
4. Phase 5: Coverage + quickstart validation → release-ready

### Parallel Team Strategy

After T001 (types, ~5 minutes):

- **Developer A**: US1 (T002 → T003 in parallel, then T004 → T005)
- **Developer B**: US3 (T008 → T009) — fully independent, only touches `NavBar.tsx`

Developer A continues to US2 (T006 → T007) after US1 checkpoints.

---

## Notes

- `[P]` = different files, no dependency on an incomplete task in the same phase — safe to run concurrently
- `[Story]` label maps every task to its user story for full traceability
- **TDD mandatory**: tests MUST be written and confirmed failing BEFORE any implementation starts (Constitution Principle IV)
- **UI design system**: `slate-*` for all neutral surfaces/text, `indigo-600`/`indigo-700` for interactive accents — do NOT introduce `blue-*` or `gray-*` (Constitution)
- `RoleBadge` already exists at `apps/web/components/members/RoleBadge.tsx` — reuse it in SpaceCard
- `Space` type already exists in `apps/web/lib/types.ts` — only the three new membership types (T001) need adding
- Auth guard pattern (`useAuth` redirect) follows the existing documents page pattern
