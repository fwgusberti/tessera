# Tasks: Human-Readable Member Identity in User Management

**Input**: Design documents from `/specs/065-fix-member-display/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/space-members-api.md, quickstart.md

**Tests**: Included — Constitution IV mandates test-first at every layer (core, API, web). Each story writes its failing tests before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Monorepo web application per plan.md: `packages/core` (domain + ports), `apps/api` (FastAPI adapters + routers), `apps/web` (Next.js App Router). Suite conventions: core uses `@pytest.mark.asyncio`; API uses `@pytest.mark.anyio` with `fastapi.testclient.TestClient` and module-level imports in routers; web uses Vitest + @testing-library/react.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new dependencies, tables, or migrations — setup is limited to capturing the pre-change baseline so "zero new failures" is verifiable later.

- [X] T001 Record the pre-change test baseline: run `cd apps/api && uv run pytest tests/integration/test_members.py tests/contract/test_members.py -v` and `cd apps/web && npx vitest run tests/members.test.tsx`, noting current pass/fail state (known out-of-scope failures: test_ports, migration_0002, tessera_mcp suites)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: None required. The feature is an additive read path over existing tables, auth, and routing — no shared infrastructure precedes the user stories.

**Checkpoint**: Proceed directly to Phase 3.

---

## Phase 3: User Story 1 - Space members are identified by name and email (Priority: P1) 🎯 MVP

**Goal**: `GET /v1/spaces/{space_id}/members` returns each member's `display_name` and `email` via a single tenant-scoped SQL JOIN (ordered by `display_name`), and the space members panel renders name primary / email secondary with the fallback chain `display_name → email → "Unknown user"` — never a UUID.

**Independent Test**: Open any space's members panel as an admin and verify each row shows a human-readable name with the email beneath it, and no raw identifier appears anywhere in the table (SC-001).

### Tests for User Story 1 (write FIRST, ensure they FAIL) ⚠️

- [X] T002 [P] [US1] Value-object test: `SpaceMemberListing` holds all nine fields (`id`, `space_id`, `user_id`, `display_name`, `email`, `role`, `invited_by_user_id`, `created_at`, `updated_at`), mirroring `test_company_member_listing.py`, in packages/core/tests/test_space_member_listing.py
- [X] T003 [P] [US1] Integration tests: list response includes non-null `display_name`/`email` per member; rows ordered by `display_name` ascending; Company A admin requesting Company B's space gets generic 404 with no member identity in the body; repository-level `list_by_space_with_identity(space_id, wrong_company_id)` returns `[]` even when the space has members — in apps/api/tests/integration/test_members.py (anyio markers, `fastapi.testclient.TestClient`)
- [X] T004 [P] [US1] Contract test: enriched response shape `{id, space_id, user_id, display_name, email, role, invited_by_user_id, created_at, updated_at}` per row inside `{"members": [...]}`; `display_name` may be `""` but never null; all pre-existing fields preserved — in apps/api/tests/contract/test_members.py
- [X] T005 [P] [US1] Component tests: row shows display name with email beneath in muted text; blank `display_name` → email as primary label with no duplicated secondary line; both blank → literal "Unknown user"; the member's UUID never appears in rendered output — in apps/web/tests/members.test.tsx

### Implementation for User Story 1

- [X] T006 [P] [US1] Create `SpaceMemberListing` plain domain class (no framework imports, mirrors `CompanyMemberListing`) in packages/core/tessera_core/domain/space_member_listing.py, exported following the existing domain package convention
- [X] T007 [US1] Add abstract method `async def list_by_space_with_identity(self, space_id: UUID, company_id: UUID) -> list[SpaceMemberListing]` to `SpaceMembershipRepository` in packages/core/tessera_core/ports/repositories/space_membership.py (depends on T006)
- [X] T008 [US1] Implement `list_by_space_with_identity` in `SqlSpaceMembershipRepository`: single query joining `users` (identity columns) and `spaces` (enforcing `spaces.company_id == company_id` inside the query per Constitution VI), `ORDER BY users.display_name`, returning `SpaceMemberListing` rows — in apps/api/tessera_api/adapters/repositories/space_membership.py (depends on T007)
- [X] T009 [US1] Update `list_members` in apps/api/tessera_api/routers/members.py: call `list_by_space_with_identity` with `company_id` from the authenticated `CompanyMemberContext`; derive the `SpaceMembership` list needed by `can_read_space_document` from the enriched rows instead of a second `list_by_space` query (research R6); return the enriched rows in the existing `{"members": [...]}` envelope (depends on T008)
- [X] T010 [US1] Update apps/web/components/members/SpaceMembersPanel.tsx: primary label `display_name || email || "Unknown user"` (remove the `user_id` fallback entirely); secondary email line only when `display_name` is non-blank; `truncate` with bounded cell width for long names/emails so the table layout holds
- [X] T011 [US1] Verify US1: run `cd packages/core && uv run pytest tests/test_space_member_listing.py -v`, `cd apps/api && uv run pytest tests/integration/test_members.py tests/contract/test_members.py -v`, `cd apps/web && npx vitest run tests/members.test.tsx`; then `uv run ruff check . && uv run black --check .` on touched Python packages — all new tests green, zero new failures vs T001 baseline

**Checkpoint**: The reported defect is fixed — members panel shows names and emails, no UUIDs. MVP deliverable.

---

## Phase 4: User Story 2 - Administrators can confidently act on the right person (Priority: P2)

**Goal**: Role change and removal keep targeting the row's `user_id` (`PUT`/`DELETE /v1/spaces/{space_id}/members/{user_id}`) while the row stays identified by name+email throughout the interaction (FR-005).

**Independent Test**: As a space admin, change a member's role and remove a member; in each case the acted-on row displays that person's name and email, and the mutation lands on the intended `user_id` (SC-003).

### Tests for User Story 2 (write FIRST, ensure they FAIL) ⚠️

- [X] T012 [P] [US2] Component tests: role change fires `PUT /v1/spaces/{space_id}/members/{user_id}` and removal fires `DELETE /v1/spaces/{space_id}/members/{user_id}` using the row's `user_id` (not the display label); two members sharing a display name are disambiguated by their email lines — in apps/web/tests/members.test.tsx
- [X] T013 [P] [US2] Integration test: after the enriched list response, `PUT` role change and `DELETE` removal against a listed member's `user_id` still succeed with unchanged semantics (mutation endpoints untouched by the enrichment) — in apps/api/tests/integration/test_members.py

### Implementation for User Story 2

- [X] T014 [US2] Confirm/adjust action handlers in apps/web/components/members/SpaceMembersPanel.tsx so the role dropdown and Remove button keep sourcing `member.user_id` for their API calls after the T010 label changes (display-only change; fix any handler that reads the rendered label)
- [X] T015 [US2] Verify US2: run `cd apps/web && npx vitest run tests/members.test.tsx` and `cd apps/api && uv run pytest tests/integration/test_members.py -v` — all US2 tests green, zero new failures

**Checkpoint**: Management actions verified to target the correct member with readable identity throughout.

---

## Phase 5: User Story 3 - Member identity is consistent across all management surfaces (Priority: P3)

**Goal**: Every member-listing surface (company Users page, add-member search results) uses the same fallback chain terminating in "Unknown user" — a raw identifier is never rendered as a person's label anywhere (SC-004).

**Independent Test**: Visit the company Users page and the add-member search; verify identical name-primary/email-secondary presentation and that a user with both fields blank renders as "Unknown user", never an identifier.

### Tests for User Story 3 (write FIRST, ensure they FAIL) ⚠️

- [X] T016 [P] [US3] Component tests: company Users page row with blank `display_name` and blank `email` renders "Unknown user" (currently `display_name || email` can render empty); AddMemberForm search-result label falls back `display_name → email → "Unknown user"` (currently bare `display_name`) — in apps/web/tests/members.test.tsx (or the existing suite covering app/users/page.tsx if separate)

### Implementation for User Story 3

- [X] T017 [P] [US3] Add the "Unknown user" terminal fallback to the member label in apps/web/app/users/page.tsx (`display_name || email || "Unknown user"`)
- [X] T018 [P] [US3] Apply the same fallback chain to search-result labels in apps/web/components/members/AddMemberForm.tsx
- [X] T019 [US3] Verify US3: run `cd apps/web && npx vitest run tests/members.test.tsx` — all US3 tests green, zero new failures

**Checkpoint**: All member-listing surfaces present identity consistently; no surface can render a UUID as a label.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Full-feature validation per quickstart.md and quality gates.

- [X] T020 Run the full quickstart automated validation (quickstart.md §1): core, API, and web suites plus `uv run ruff check . && uv run black --check .` on touched Python packages — assert zero new failures vs the T001 baseline
- [X] T021 [P] API-level validation per quickstart.md §2: curl the enriched endpoint with a seeded space (every row has `display_name`/`email`, ordered by `display_name`) and cross-tenant probe returns generic 404 with no identity data
- [X] T022 [P] Browser validation per quickstart.md §3 at `http://192.168.0.8:3000` (CORS allows only this origin): members panel scenarios (US1), role change/removal (US2), Users page + add-member search consistency (US3), non-admin read-only view (edge case)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Empty — no blocking work
- **User Stories (Phase 3–5)**: US1 (Phase 3) is the backend + primary-surface fix. US2 (Phase 4) depends on US1's enriched list being in place (it verifies actions against the new rendering). US3 (Phase 5) is frontend-only and independent of US2; it can run in parallel with US2 once US1's T010 is done (different files)
- **Polish (Phase 6)**: After all desired stories complete

### Task Dependencies (within US1)

- T006 (value object) → T007 (port imports it) → T008 (adapter implements port) → T009 (router calls adapter)
- T010 (panel) is independent of T006–T009 (frontend renders optional fields already declared) — can run in parallel with the backend chain
- T011 requires T002–T010

### Parallel Opportunities

- **US1 tests**: T002, T003, T004, T005 — four different files, all in parallel
- **US1 implementation**: T006 ∥ T010 (core vs web); then T007 → T008 → T009 sequentially (same dependency chain)
- **US2 tests**: T012 ∥ T013 (web vs API files)
- **US3**: T017 ∥ T018 (different files); whole story parallel with US2 after T010
- **Polish**: T021 ∥ T022 after T020

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together (write first, watch them fail):
Task: "Value-object test in packages/core/tests/test_space_member_listing.py"
Task: "Integration tests (identity, ordering, isolation) in apps/api/tests/integration/test_members.py"
Task: "Contract test (enriched shape) in apps/api/tests/contract/test_members.py"
Task: "Component tests (fallback chain, no-UUID) in apps/web/tests/members.test.tsx"

# Then start both implementation tracks in parallel:
Task: "Create SpaceMemberListing in packages/core/tessera_core/domain/space_member_listing.py"
Task: "Update label fallback in apps/web/components/members/SpaceMembersPanel.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (baseline capture)
2. Complete Phase 3: US1 tests → backend chain (T006→T009) ∥ frontend (T010) → verify (T011)
3. **STOP and VALIDATE**: members panel shows names+emails, no UUIDs — the reported defect is fixed
4. Deploy/demo if ready

### Incremental Delivery

1. US1 → validate independently → MVP (defect resolved)
2. US2 → validate actions target the right person → deploy
3. US3 → sweep remaining surfaces → deploy
4. Polish → quickstart end-to-end validation

### Parallel Team Strategy

With two developers, after US1's T010 lands: Developer A takes US2 (Phase 4), Developer B takes US3 (Phase 5) — disjoint files except the shared test suite `apps/web/tests/members.test.tsx`, so coordinate merges there.

---

## Notes

- [P] tasks = different files, no dependencies
- Verify each story's tests fail before implementing (Constitution IV)
- Additive API change only — never remove or rename existing response fields (backward compatibility, FR-005)
- Tenant scoping is enforced inside the new query itself (`spaces.company_id = :company_id`), not only at the route boundary (Constitution VI, defense in depth)
- Known pre-existing failures (test_ports, migration_0002, tessera_mcp) and the unreachable 85% API coverage gate are out of scope — assert zero *new* failures only
- Commit after each task or logical group
