# Tasks: Tenant Data Isolation (031)

**Input**: Design documents from `/specs/031-tenant-data-isolation/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/api-isolation.md ✅, quickstart.md ✅

**Tests**: TDD is MANDATORY per Constitution §IV. Test tasks must be written and confirmed **failing** before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no outstanding dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- All file paths are repository-root-relative

---

## Phase 1: Setup

**Purpose**: Establish two-company test infrastructure and shared fixtures used by every isolation test.

- [X] T001 Create apps/api/tests/test_tenant_isolation.py with module-level imports and an empty test class to verify the file loads cleanly
- [X] T002 [P] Add `two_company_setup` fixture to apps/api/tests/conftest.py — registers alice/alpha and bob/beta, activates each company context, returns `(token_a, company_a_id, token_b, company_b_id)`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema change, domain entity update, JWT extension, and auth dependency — everything US1–US4 depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Write failing test for `Space(company_id=uuid4(), ...)` construction in packages/core/tests/test_entities.py — confirm test fails before T004
- [X] T004 Add `company_id: UUID` field to `Space` entity in packages/core/tessera_core/domain/entities.py
- [X] T005 Write migration `0007_space_company_id.py` in db/migrations/versions/ — add `company_id` as nullable FK to `companies`, backfill to oldest company id, set NOT NULL, add `ix_spaces_company` index
- [X] T006 Add `company_id` mapped column to `SpaceModel` in apps/api/tessera_api/adapters/models.py
- [X] T007 Update `_space_from_model` mapper to include `company_id` in apps/api/tessera_api/adapters/repo.py
- [X] T008 Write failing test for `create_access_token(user_id, email, is_admin, company_id=uuid)` — assert JWT payload contains `company_id` claim in apps/api/tests/test_jwt_auth.py
- [X] T009 Update `create_access_token` to accept `company_id: UUID | None = None` and embed it as a JWT claim in apps/api/tessera_api/auth/jwt_auth.py
- [X] T010 Write failing test for `require_company_context` — verify 403 with `"no_company_context"` code when JWT has no `company_id` claim in apps/api/tests/test_auth.py
- [X] T011 Implement `require_company_context` dependency in apps/api/tessera_api/auth/oidc.py — reads `company_id` from JWT claim or `session["user"]["active_company_id"]`; raises 401 if unauthenticated, 403 `"no_company_context"` if no active company; returns `(user_info, company_id)`
- [X] T012 Write failing test for `POST /companies/{company_id}/activate` — 200 + token for a member, 403 for a non-member in apps/api/tests/test_companies.py
- [X] T013 Implement `POST /companies/{company_id}/activate` endpoint in apps/api/tessera_api/routers/companies.py — validates membership via `SqlCompanyRepository`, issues new JWT with `company_id`, sets `session["user"]["active_company_id"]`, returns `{token, company_id, company_name}`

**Checkpoint**: Foundation complete — migration, entity, JWT, and auth dependency ready. All Phase 2 tests green. User story work can begin.

---

## Phase 3: User Story 1 — Block Cross-Company Space Access (Priority: P1) 🎯 MVP

**Goal**: Space listing and creation are scoped to the authenticated company. No user can see, access, or create in another company's spaces.

**Independent Test**: Alice (Company Alpha) and Bob (Company Beta) each have a space. `GET /spaces` with Bob's token returns zero Alpha spaces. Bob cannot create a document in Alice's space.

### Tests for User Story 1 (TDD — write BEFORE implementation, confirm FAILING)

- [X] T014 [US1] Write `test_company_a_cannot_list_company_b_spaces` in apps/api/tests/test_tenant_isolation.py — GET /spaces with token_b returns only Company B spaces (len == 0 when no Beta spaces exist)
- [X] T015 [US1] Write `test_company_a_cannot_get_company_b_space_by_id` in apps/api/tests/test_tenant_isolation.py — GET /spaces/{alpha_space_id} with token_b returns 403
- [X] T016 [US1] Write `test_space_create_binds_to_session_company` in apps/api/tests/test_tenant_isolation.py — POST /spaces with token_a returns a space whose `company_id` matches alpha's company id

### Implementation for User Story 1

- [X] T017 [P] [US1] Add `list_by_company(company_id: UUID) -> list[Space]` and `get_by_id_for_company(space_id: UUID, company_id: UUID) -> Space | None` to `SpaceRepository` protocol in packages/core/tessera_core/ports/repositories.py
- [X] T018 [P] [US1] Implement `SqlSpaceRepository.list_by_company` (WHERE company_id = ?) in apps/api/tessera_api/adapters/repo.py
- [X] T019 [P] [US1] Implement `SqlSpaceRepository.get_by_id_for_company` (WHERE id = ? AND company_id = ?) in apps/api/tessera_api/adapters/repo.py
- [X] T020 [US1] Update `SqlSpaceRepository.create()` to persist `company_id` from the `Space` entity in apps/api/tessera_api/adapters/repo.py
- [X] T021 [US1] Update `list_spaces` handler to use `require_company_context` and call `list_by_company(company_id)` in apps/api/tessera_api/routers/spaces.py
- [X] T022 [US1] Update `create_space` handler to use `require_company_context` and bind `space.company_id = company_id` from session in apps/api/tessera_api/routers/spaces.py
- [X] T023 [US1] Emit structured audit event (actor_id, entity_type="space", entity_id, company_id) on cross-tenant denial in apps/api/tessera_api/routers/spaces.py (FR-012)

**Checkpoint**: User Story 1 complete — T014–T016 all green. `GET /spaces` returns only the authenticated company's spaces.

---

## Phase 4: User Story 2 — Block Cross-Company Document Access (Priority: P1)

**Goal**: Document retrieval, creation, publishing, reindexing, search, and assistant answers are all scoped to the authenticated company.

**Independent Test**: Alice publishes a document. Bob's `GET /documents/{doc_id}` returns 403. Bob's `POST /search` returns zero results. Bob's `POST /assistant/answer` returns no Alpha citations.

### Tests for User Story 2 (TDD — write BEFORE implementation, confirm FAILING)

- [X] T024 [P] [US2] Write `test_company_a_cannot_get_company_b_document_by_id` in apps/api/tests/test_tenant_isolation.py — GET /documents/{alpha_doc_id} with token_b returns 403
- [X] T025 [P] [US2] Write `test_company_a_cannot_create_document_in_company_b_space` in apps/api/tests/test_tenant_isolation.py — POST /documents with token_b and space_id=alpha_space_id returns 403
- [X] T026 [P] [US2] Write `test_company_a_search_returns_only_company_a_results` in apps/api/tests/test_tenant_isolation.py — POST /search with token_b returns 0 results for Alpha-only content
- [X] T027 [P] [US2] Write `test_company_a_assistant_returns_only_company_a_citations` in apps/api/tests/test_tenant_isolation.py — POST /assistant/answer with token_b returns no citations from Alpha documents

### Implementation for User Story 2

- [X] T028 [P] [US2] Add `get_by_id_for_company(doc_id: UUID, company_id: UUID) -> Document | None` and `list_by_space_ids_for_company(space_ids: list[UUID], company_id: UUID, state: DocumentLifecycleState | None = None) -> list[Document]` to `DocumentRepository` protocol in packages/core/tessera_core/ports/repositories.py
- [X] T029 [US2] Implement `SqlDocumentRepository.get_by_id_for_company` — JOIN documents→spaces WHERE documents.id = ? AND spaces.company_id = ? in apps/api/tessera_api/adapters/repo.py
- [X] T030 [US2] Implement `SqlDocumentRepository.list_by_space_ids_for_company` — validates space_ids belong to company_id, then filters documents in apps/api/tessera_api/adapters/repo.py
- [X] T031 [US2] Update `list_documents` handler to use `require_company_context` and `list_by_space_ids_for_company`; validate any `space_id` query param belongs to session company in apps/api/tessera_api/routers/documents.py
- [X] T032 [US2] Update `get_document` handler to use `get_by_id_for_company`; return 403 on company mismatch (do not reveal existence) in apps/api/tessera_api/routers/documents.py
- [X] T033 [US2] Update `create_document` handler to validate `body.space_id` belongs to session company before creating; return 403 otherwise in apps/api/tessera_api/routers/documents.py
- [X] T034 [US2] Update `publish_document` handler to validate document belongs to session company before publishing in apps/api/tessera_api/routers/documents.py
- [X] T035 [US2] Update `reindex_document` handler to validate document belongs to session company before queuing in apps/api/tessera_api/routers/documents.py
- [X] T036 [US2] Update `search` handler to derive `allowed_space_ids` from `list_by_company(company_id)` instead of `list_all()`; cap any caller-supplied `space_ids` to company-owned IDs in apps/api/tessera_api/routers/search.py
- [X] T037 [US2] Update `assistant/answer` handler to scope space_ids to `list_by_company(company_id)` in apps/api/tessera_api/routers/assistant.py
- [X] T038 [US2] Emit structured audit event on cross-tenant document access denial in apps/api/tessera_api/routers/documents.py (FR-012)

**Checkpoint**: User Story 2 complete — T024–T027 all green. All P1 security gaps closed.

---

## Phase 5: User Story 3 — Isolate Member and Organizational Data (Priority: P2)

**Goal**: The member roster and company settings visible to any user contain only data from their active company. Revoked memberships are rejected at the auth boundary.

**Independent Test**: Alice views member list — only Alpha members visible. Bob views member list — only Beta members visible. A user whose membership was revoked receives 403 on the next request.

### Tests for User Story 3 (TDD — write BEFORE implementation, confirm FAILING)

- [X] T039 [US3] Write `test_company_a_member_list_excludes_company_b_members` in apps/api/tests/test_tenant_isolation.py — GET /companies/me member list with token_a contains no Beta users
- [X] T040 [US3] Write `test_require_company_context_rejects_revoked_member` in apps/api/tests/test_tenant_isolation.py — revoke Alice's membership then assert subsequent tenant-scoped request returns 403

### Implementation for User Story 3

- [X] T041 [US3] Update `require_company_context` to perform a DB membership check (call `SqlCompanyRepository.get_membership(user_id, company_id)`) and raise 403 if membership is absent or revoked in apps/api/tessera_api/auth/oidc.py
- [X] T042 [US3] Update `GET /spaces/{space_id}/members` handler to use `require_company_context` and validate that the requested space belongs to the session company before listing members in apps/api/tessera_api/routers/spaces.py

**Checkpoint**: User Story 3 complete — T039–T040 green. Member data never crosses company boundary; revoked sessions are blocked.

---

## Phase 6: User Story 4 — Enforce Isolation Across All Session and Context Switches (Priority: P2)

**Goal**: Activating a company context atomically replaces the previous one. After a switch all data views reflect only the new company. Auto-activation on login/register eliminates the "no context" state for single-company users.

**Independent Test**: Charlie belongs to both Alpha and Beta. After activating Alpha, `GET /spaces` returns only Alpha spaces. After activating Beta, the same call returns only Beta spaces — no Alpha data appears.

### Tests for User Story 4 (TDD — write BEFORE implementation, confirm FAILING)

- [X] T043 [P] [US4] Write `test_activate_company_forbidden_for_non_member` in apps/api/tests/test_tenant_isolation.py — POST /companies/{beta_id}/activate with token_a returns 403
- [X] T044 [P] [US4] Write `test_context_switch_scopes_correctly` in apps/api/tests/test_tenant_isolation.py — Charlie activates Alpha, lists Alpha spaces; activates Beta, lists Beta spaces; no cross-contamination

### Implementation for User Story 4

- [X] T045 [US4] Update `POST /companies/{id}/activate` to unconditionally overwrite `session["user"]["active_company_id"]` (not append) ensuring previous context is fully replaced in apps/api/tessera_api/routers/companies.py
- [X] T046 [US4] Update login flow to auto-activate company context when the user has exactly one active company membership in apps/api/tessera_api/routers/ (auth router)
- [X] T047 [US4] Update register/company-creation flow to auto-activate the newly created company immediately in apps/api/tessera_api/routers/ (companies router)

**Checkpoint**: User Story 4 complete — T043–T044 green. Context switch is atomic; login auto-activates for single-company users.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Audit logging completeness, regression check, quality gates, and scope documentation.

- [X] T048 [P] Verify all cross-tenant denial paths emit a structured `audit_records` INSERT with fields `(actor_id, entity_type, entity_id, company_id, denied_at)` — grep apps/api for every 403 raise and confirm audit call is present
- [X] T049 [P] Run full regression suite and fix any breakage: `cd apps/api && uv run pytest tests/ -v` (must include existing test_assistant_history.py passing)
- [X] T050 [P] Run ruff and black across all modified files; fix any violations before commit (Constitution §V quality gate)
- [X] T051 Run quickstart.md manual validation scenarios against local stack (`make dev`): Scenario 1 space isolation, Scenario 2 document isolation, Scenario 3 search isolation, Scenario 4 context switch
- [X] T052 Add a note to plan.md that `apps/mcp-server` tenant isolation is in-scope but will be addressed in a dedicated follow-up sub-task (not in this PR)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — **BLOCKS all user stories**; Space entity and JWT changes underpin everything
- **Phase 3 (US1)**: Depends on Phase 2 completion
- **Phase 4 (US2)**: Depends on Phase 2 completion — can run **in parallel with Phase 3**
- **Phase 5 (US3)**: Depends on Phase 2 (require_company_context with membership check from T041)
- **Phase 6 (US4)**: Depends on Phase 2 (activate endpoint T013 must be wired before T045–T047)
- **Phase 7 (Polish)**: Depends on all user story phases complete

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational — no dependencies on US2/US3/US4
- **US2 (P1)**: Starts after Foundational — no dependencies on US1; safe to implement in parallel
- **US3 (P2)**: Starts after Foundational; builds on `require_company_context` from T011
- **US4 (P2)**: Starts after Foundational; builds on activate endpoint from T013

### Within Each User Story

1. Write test tasks — **confirm tests FAIL** before continuing
2. Repository protocol changes (port) before SQLAlchemy implementation
3. Repository implementation before router updates
4. All story tests must be green at the phase checkpoint before moving on

### Parallel Opportunities

- T001 and T002 (Phase 1) can run in parallel
- T003, T008, T010, T012 (test-writing in Phase 2) can run in parallel
- T018, T019 (US1 repo impl) can run in parallel
- US1 (Phase 3) and US2 (Phase 4) can be worked simultaneously after Phase 2
- US3 (Phase 5) and US4 (Phase 6) can start in parallel with US1/US2 after Phase 2
- T024–T027 (US2 test writing) all parallelizable
- T048, T049, T050 (Phase 7 cleanup) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Write all three tests in parallel (different functions, same file):
Task: T014 — test_company_a_cannot_list_company_b_spaces
Task: T015 — test_company_a_cannot_get_company_b_space_by_id
Task: T016 — test_space_create_binds_to_session_company

# Confirm all three FAIL, then implement in parallel:
Task: T018 — SqlSpaceRepository.list_by_company
Task: T019 — SqlSpaceRepository.get_by_id_for_company
```

---

## Parallel Example: User Story 2

```bash
# Write all four tests in parallel:
Task: T024 — test_company_a_cannot_get_company_b_document_by_id
Task: T025 — test_company_a_cannot_create_document_in_company_b_space
Task: T026 — test_company_a_search_returns_only_company_a_results
Task: T027 — test_company_a_assistant_returns_only_company_a_citations

# Confirm all four FAIL, then implement in parallel:
Task: T029 — SqlDocumentRepository.get_by_id_for_company
Task: T030 — SqlDocumentRepository.list_by_space_ids_for_company
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 — both P1)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational — CRITICAL gate
3. Complete Phase 3: User Story 1 — Space isolation
4. **STOP and VALIDATE**: T014–T016 green; `GET /spaces` scoped correctly
5. Complete Phase 4: User Story 2 — Document, search, assistant isolation
6. **STOP and VALIDATE**: T024–T027 green; all P1 isolation gaps closed
7. Deploy — the reported security breach is remediated

### Incremental Delivery

1. Setup + Foundational → migration live, entity updated, JWT extended
2. US1 → Space cross-tenant gap closed
3. US2 → Document + search + assistant cross-tenant gaps closed (**P1 complete — shippable**)
4. US3 → Member data isolation hardened
5. US4 → Context switch atomicity enforced
6. Polish → Audit completeness, regressions clean, quality gates pass

---

## Notes

- [P] tasks involve different files or have no incomplete dependencies between them
- [Story] label maps every task to a traceable user story from spec.md
- TDD is non-negotiable (Constitution §IV): every test task must produce a **failing** test before its paired implementation tasks begin
- Cross-tenant denials return **HTTP 403** (not 404) per contracts/api-isolation.md and quickstart.md; spec FR-006 says 404 but the plan and contracts override — use 403 uniformly
- `apps/mcp-server` is explicitly out of this PR (see T052); enforce isolation there in a follow-up
- Run `cd apps/api && uv run pytest tests/test_tenant_isolation.py -v` as final validation before opening the PR
