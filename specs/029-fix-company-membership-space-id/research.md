# Research: Fix Company Membership space_id AttributeError

## Root Cause Analysis

**Decision**: The bug is a Python name-shadowing defect in `apps/api/tessera_api/adapters/repo.py`.

**Rationale**:
Two module-level functions share the name `_membership_from_model`:

1. Line 985 — maps `CompanyMembershipModel → CompanyMembership` (company domain object)
2. Line 1372 — maps `SpaceMembershipModel → SpaceMembership` (space domain object)

Python resolves module-level names by last-write-wins: by the time the module finishes loading, `_membership_from_model` refers only to the `SpaceMembership` mapper (line 1372). The three callers inside `SqlCompanyRepository` — `add_membership` (line 1029), `get_membership` (line 1039), and `list_memberships_for_user` (line 1045) — all call the space mapper on a `CompanyMembershipModel` instance. That mapper attempts `m.space_id`, which does not exist on `CompanyMembershipModel`, causing `AttributeError: 'CompanyMembershipModel' object has no attribute 'space_id'` and the 500 response.

**Alternatives considered**:
- Merging the two mapper functions: rejected — `CompanyMembership` and `SpaceMembership` are intentionally distinct domain entities with different fields.
- Moving the company mapper after the space mapper so it wins the last-write: rejected — creates the symmetric bug for `SpaceMembership`, and is confusing to read.
- Namespace isolation via classes: overkill for a one-line rename.

## Fix

Rename the company mapper (line 985) to `_company_membership_from_model` and update the three callers:
- `add_membership` → replace `_membership_from_model(model)` with `_company_membership_from_model(model)`
- `get_membership` → same
- `list_memberships_for_user` → same

No migration, no schema change, no interface change required.

## Affected Entities

| Entity | ORM Model | Mapper (before) | Mapper (after) |
|---|---|---|---|
| `CompanyMembership` | `CompanyMembershipModel` | `_membership_from_model` (shadowed) | `_company_membership_from_model` |
| `SpaceMembership` | `SpaceMembershipModel` | `_membership_from_model` | `_membership_from_model` (unchanged) |

## Testing Approach

**Unit tests** (anyio, sync mocks) already exist in `apps/api/tests/unit/test_company_repo.py`. The existing `test_add_membership_persists_record` test would reproduce the bug if run before the fix — after the fix it must pass. Additional tests needed:
- `test_add_membership_returns_company_membership` — asserts returned object has `company_id`, not `space_id`
- `test_get_membership_returns_correct_type` — asserts `CompanyMembership` domain type is returned, not `SpaceMembership`
- `test_list_memberships_for_user_returns_company_memberships` — asserts list items are `CompanyMembership`

No integration tests needed for this defect: the failure is in pure mapping code, fully exercisable with unit tests and mocked sessions.
