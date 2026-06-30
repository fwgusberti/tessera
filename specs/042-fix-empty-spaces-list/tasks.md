# Tasks: Fix Empty Spaces List

**Input**: Design documents from `/specs/042-fix-empty-spaces-list/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Required — Constitution Principle IV (TDD non-negotiable). The migration backfill is tested against a real Postgres connection inside a rolled-back transaction (mirroring the existing `test_migration_0010_backfill.py`), since a mocked session cannot prove a bulk `INSERT ... SELECT` is correct.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete-task dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in all task descriptions

## Path Conventions

- **API router**: `apps/api/tessera_api/routers/`
- **API unit tests**: `apps/api/tests/unit/`
- **API real-DB tests**: `apps/api/tests/` (top-level, matching `test_migration_0010_backfill.py`)
- **Migrations**: `db/migrations/versions/`

---

## Phase 1: User Story 1 - Creating a Space Grants Immediate Access (Priority: P1) 🎯 MVP

**Goal**: `POST /v1/spaces` grants the creator an admin `SpaceMembership` in the same request, so every space created from now on is immediately visible to its creator.

**Independent Test**: Create a space as any authenticated company member, then immediately call `GET /v1/spaces` as that same user and confirm the new space appears with `effective_role: "admin"`.

### Tests for User Story 1 ⚠️ Write FIRST — confirm they FAIL before implementing

- [X] T001 [P] [US1] Write failing pytest tests for `create_space` in `apps/api/tests/unit/test_spaces_router.py` (new file) covering: a `SpaceMembership` is created for the caller with `role=admin` and the new space's `id`, the membership's `user_id` matches the authenticated caller (not any request-supplied value), and an audit record is written (action `member_invited`, matching the existing pattern used elsewhere in this router)

### Implementation for User Story 1

- [X] T002 [US1] Modify `create_space` in `apps/api/tessera_api/routers/spaces.py`: after `repo.create(space)` succeeds, add a `SpaceMembership(space_id=created.id, user_id=<caller>, role=SpaceRole.ADMIN)` via `SqlSpaceMembershipRepository.add()`, then call `write_audit` (action `member_invited`, entity_type `space_membership`) — response shape unchanged (depends on T001 being red first)

**Checkpoint**: A newly created space is immediately visible to its creator via `GET /v1/spaces`. User Story 1 is independently functional.

---

## Phase 2: User Story 2 - Previously Created Spaces Become Visible Again (Priority: P1)

**Goal**: A one-time, idempotent migration backfills an admin `SpaceMembership` for every company admin on every space that currently has zero recorded members, without touching spaces that already have legitimate members.

**Independent Test**: Against a real database with an orphaned space (zero `space_memberships` rows) belonging to a company with one or more admins, run the migration's backfill SQL and confirm every company admin now has an admin membership on that space, while a control space with a pre-existing member is untouched.

### Tests for User Story 2 ⚠️ Write FIRST — confirm they FAIL before implementing

- [X] T003 [P] [US2] Write failing real-DB tests (rolled-back transaction, skip if DB unreachable — mirror `apps/api/tests/test_migration_0010_backfill.py`'s structure exactly) in `apps/api/tests/test_migration_0013_backfill_space_memberships.py` (new file) covering: (a) an orphaned space gets an admin membership for its company's admin; (b) a company with two admins gets both backfilled onto the same orphaned space; (c) a space that already has one membership (any role) gets nothing added — no duplicate, no role change; (d) re-running the backfill SQL a second time is a no-op (idempotent); (e) an admin of company A never receives a membership on an orphaned space belonging to company B (cross-tenant isolation, Constitution Principle VI); (f) FR-006 edge case — a space whose company has zero `role='admin'` memberships is left with zero inserted rows and the backfill does not error

### Implementation for User Story 2

- [X] T004 [US2] Create `db/migrations/versions/0013_backfill_space_memberships.py`: module-level `BACKFILL_SQL` constant performing `INSERT INTO space_memberships (space_id, user_id, role) SELECT s.id, cm.user_id, 'admin' FROM spaces s JOIN company_memberships cm ON cm.company_id = s.company_id AND cm.role = 'admin' WHERE NOT EXISTS (SELECT 1 FROM space_memberships sm WHERE sm.space_id = s.id) ON CONFLICT (space_id, user_id) DO NOTHING`, `upgrade()` calling `op.execute(BACKFILL_SQL)` then a follow-up `SELECT count(*) FROM spaces s WHERE NOT EXISTS (SELECT 1 FROM space_memberships sm WHERE sm.space_id = s.id)` logged as a warning if non-zero (FR-006 — surfaces companies with no admin to backfill onto, rather than failing silently), `downgrade()` as a documented no-op (mirroring `0010`'s rationale — backfilled rows are indistinguishable from organic ones), `revision = "0013"`, `down_revision = "0012"` (depends on T003 being red first)

**Checkpoint**: Running migrations restores every existing company's admin(s) to every space that currently has no members. User Stories 1 and 2 together mean no space — past or future — is ever left without at least one admin who can see it.

---

## Phase 3: User Story 3 - Space Visibility Is Consistent Everywhere (Priority: P2)

**Goal**: Confirm the fix closes the loop on the originally reported symptom — the Spaces page, the document search space filter, and the Spaces menu all reflect the same `GET /v1/spaces` data, with no surface left behind.

**Independent Test**: As a user with restored/granted access (per US1 or US2), confirm the Spaces page, the document search space filter, and any other space-aware view all show the identical set of spaces.

### Verification for User Story 3

- [X] T005 [US3] Re-run the live-DB diagnostic used to confirm this bug (the read-only queries against `spaces`/`space_memberships`/`company_memberships` used during investigation) against the dev database after migration `0013` is applied: confirm `felipe@gusba.dev`'s spaces `a`, `b`, `D` now have admin `space_memberships` rows, confirm `GET /v1/spaces` for that user returns all three, and confirm (by reading `apps/web/app/spaces/page.tsx` and `apps/web/app/documents/page.tsx`, both already calling `GET /v1/spaces` directly) that no separate code path exists that could diverge — no frontend changes are required for this story since both surfaces already share the single fixed source

**Checkpoint**: All three user stories verified — the originally reported bug (no spaces visible anywhere) is resolved for both existing and future spaces, consistently across every surface.

---

## Dependencies & Execution Order

### Phase Dependencies

- **User Story 1 (Phase 1)**: No dependencies — can start immediately
- **User Story 2 (Phase 2)**: No dependencies on US1 — independent code path (migration vs. router), can be done in parallel with Phase 1
- **User Story 3 (Phase 3)**: Depends on both US1 and US2 being complete (it verifies their combined effect)

### Parallel Opportunities

- T001 (US1 test) and T003 (US2 test) can be written in parallel — different files, no shared code
- T002 and T004 can be implemented in parallel once their respective tests are red — different files (`routers/spaces.py` vs a new migration), no dependency between them

---

## Parallel Example

```bash
# Both stories' tests can be written together:
Task: "Failing create_space membership-grant tests in apps/api/tests/unit/test_spaces_router.py"
Task: "Failing migration 0013 backfill tests in apps/api/tests/test_migration_0013_backfill_space_memberships.py"

# Then both implementations in parallel:
Task: "Add SpaceMembership grant to create_space in apps/api/tessera_api/routers/spaces.py"
Task: "Write migration 0013 in db/migrations/versions/0013_backfill_space_memberships.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: User Story 1
2. **STOP and VALIDATE**: New spaces are immediately visible to their creator
3. This alone stops the regression from getting worse, but existing orphaned spaces (the reporting user's actual blocker) remain broken until Phase 2 lands

### Full Fix

1. Complete User Story 1 (stop the bleeding) and User Story 2 (heal existing data) — independent, can be parallel
2. Complete User Story 3 (confirm the original report is actually resolved end-to-end)

---

## Notes

- [P] tasks = different files, no incomplete-task dependency
- [Story] label maps task to specific user story for traceability
- Verify each story's tests fail before implementing that story
- Commit after each task or logical group
- No Setup/Foundational phase: both fixes are narrow, independent, single-file changes with no shared infrastructure to stand up first
