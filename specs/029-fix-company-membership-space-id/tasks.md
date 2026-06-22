# Tasks: Fix Company Membership space_id AttributeError

**Input**: Design documents from `specs/029-fix-company-membership-space-id/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/post-companies.md

**Organization**: Single user story (US1). No setup or foundational phases required — the fix is scoped to one function rename and three call-site updates in an existing file, plus unit test additions.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1)

---

## Phase 1: User Story 1 — Create Company Successfully (Priority: P1) 🎯 MVP

**Goal**: `POST /v1/companies` returns a 2xx response with company details and the caller recorded as owner, with no 500 error.

**Root cause**: `_membership_from_model` is defined twice in `apps/api/tessera_api/adapters/repo.py`; the `SpaceMembership` version (line 1372) silently overwrites the `CompanyMembership` version (line 985), so all three `SqlCompanyRepository` callers invoke the wrong mapper and crash with `AttributeError: 'CompanyMembershipModel' object has no attribute 'space_id'`.

**Independent Test**: `POST /v1/companies` with a valid JWT returns HTTP 201 and `"role": "admin"` in the body. All unit tests in `apps/api/tests/unit/test_company_repo.py` pass.

### Tests for User Story 1 (TDD — write first, confirm they FAIL, then implement)

- [X] T001 [US1] Add failing test `test_add_membership_returns_company_membership_type` to `apps/api/tests/unit/test_company_repo.py` — asserts `result` is `CompanyMembership`, has `company_id` attribute, and has no `space_id` attribute
- [X] T002 [P] [US1] Add failing test `test_add_membership_role_round_trips` to `apps/api/tests/unit/test_company_repo.py` — asserts `result.role == CompanyRole.ADMIN` after `add_membership` call
- [X] T003 [P] [US1] Add failing test `test_get_membership_returns_company_membership_when_found` to `apps/api/tests/unit/test_company_repo.py` — mocks a `CompanyMembershipModel` row return and asserts `get_membership` returns a `CompanyMembership` with correct `company_id`
- [X] T004 [P] [US1] Add failing test `test_list_memberships_for_user_returns_company_memberships` to `apps/api/tests/unit/test_company_repo.py` — mocks two `CompanyMembershipModel` rows, asserts `list_memberships_for_user` returns a list of `CompanyMembership` instances

### Implementation for User Story 1

- [X] T005 [US1] Rename function `_membership_from_model` at line 985 to `_company_membership_from_model` in `apps/api/tessera_api/adapters/repo.py` (the `CompanyMembershipModel → CompanyMembership` mapper; the `SpaceMembership` mapper at line 1372 is unchanged)
- [X] T006 [US1] Update call site in `SqlCompanyRepository.add_membership` in `apps/api/tessera_api/adapters/repo.py` (~line 1029): replace `_membership_from_model(model)` with `_company_membership_from_model(model)`
- [X] T007 [US1] Update call site in `SqlCompanyRepository.get_membership` in `apps/api/tessera_api/adapters/repo.py` (~line 1039): replace `_membership_from_model(model)` with `_company_membership_from_model(model)`
- [X] T008 [US1] Update call site in `SqlCompanyRepository.list_memberships_for_user` in `apps/api/tessera_api/adapters/repo.py` (~line 1045): replace `_membership_from_model(m)` with `_company_membership_from_model(m)`

### Verification

- [X] T009 [US1] Run unit tests and confirm all pass: `cd apps/api && uv run pytest tests/unit/test_company_repo.py -v`
- [X] T010 [US1] Run linting and formatting checks: `cd apps/api && uv run ruff check tessera_api/adapters/repo.py && uv run black --check tessera_api/adapters/repo.py`

**Checkpoint**: T001–T004 fail before T005–T008. After T005–T008, all tests pass and `POST /v1/companies` returns 201.

---

## Dependencies & Execution Order

### Task Dependencies

- **T001**: No dependencies — write first, must fail before T005
- **T002, T003, T004**: [P] — no dependencies on each other, write in parallel with T001, must fail before their respective fix tasks
- **T005**: No dependencies — the rename; T001–T004 must exist and fail before this
- **T006**: Depends on T005 (function must be renamed before updating call site)
- **T007**: Depends on T005
- **T008**: Depends on T005
- **T009**: Depends on T005–T008 — confirms fix works
- **T010**: Depends on T005–T008 — confirms no lint regressions

### Parallel Opportunities

```bash
# Step 1 — write all failing tests in parallel:
T001: test_add_membership_returns_company_membership_type
T002: test_add_membership_role_round_trips
T003: test_get_membership_returns_company_membership_when_found
T004: test_list_memberships_for_user_returns_company_memberships

# Step 2 — apply fix (T005 first, then T006/T007/T008 in parallel):
T005: rename _membership_from_model → _company_membership_from_model
T006 + T007 + T008: update three call sites (different lines, no conflicts)

# Step 3 — verify in parallel:
T009: run pytest
T010: run ruff + black
```

---

## Implementation Strategy

### MVP (this is the only story — complete all phases)

1. Write failing tests T001–T004
2. Confirm tests fail (`AttributeError` on `space_id`)
3. Apply rename T005 and update call sites T006–T008
4. Confirm tests pass (T009)
5. Confirm lint passes (T010)

---

## Notes

- [P] tasks operate on different test methods within the same file — write each as a separate `def test_*` function; no file-level conflict
- T005–T008 all touch `repo.py` — apply sequentially or as one edit
- The `_membership_from_model` at line 1372 (space membership) MUST NOT be renamed; only the company membership mapper at line 985 changes
- Avoid: any refactoring beyond the rename and its three call sites
