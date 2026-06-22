# Implementation Plan: Fix Company Membership space_id AttributeError

**Branch**: `029-fix-company-membership-space-id` | **Date**: 2026-06-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/029-fix-company-membership-space-id/spec.md`

## Summary

`POST /v1/companies` raises `AttributeError: 'CompanyMembershipModel' object has no attribute 'space_id'` because two module-level functions share the name `_membership_from_model` in `apps/api/tessera_api/adapters/repo.py` (lines 985 and 1372). Python last-write-wins semantics cause the space-membership mapper to overwrite the company-membership mapper, so all `SqlCompanyRepository` callers invoke the wrong mapper. The fix is a targeted rename of the company mapper function and its three call sites — no schema changes, no new dependencies.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, SQLAlchemy (async), Pydantic v2, pytest + anyio

**Storage**: PostgreSQL (no schema changes required)

**Testing**: pytest + anyio (`@pytest.mark.anyio`) for API package unit tests

**Target Platform**: Linux server (Docker/Kubernetes)

**Project Type**: Web service (REST API)

**Performance Goals**: No performance impact; change is purely cosmetic at the function-name level

**Constraints**: Fix must be scoped to the mapper rename — no refactoring of unrelated code

**Scale/Scope**: Single file (`repo.py`), single function rename, three call-site updates, new unit tests

## Constitution Check

### Pre-Design Gate

| Principle | Status | Notes |
|---|---|---|
| I. Domain-Driven Architecture | PASS | Fix preserves distinct `CompanyMembership` and `SpaceMembership` domain entities; no cross-domain coupling introduced |
| II. Separation of Concerns | PASS | No product/domain definitions changed; only infrastructure mapper code corrected |
| III. Data Locality & Consent | N/A | No new persistence or client-side storage |
| IV. Test-Driven Development | PASS | New failing tests will be written first to reproduce the bug, then the fix applied |
| V. Quality Gates | PASS | Ruff + Black must pass before commit |
| PostgreSQL system of record | PASS | No alternative storage introduced |
| Audit logging | PASS | Existing `company.created` audit log unaffected |
| Secret management | PASS | No secrets involved |

No violations. No complexity tracking entry required.

### Post-Design Re-check

No design decisions alter the pre-design assessment. The rename is a pure infrastructure correction that tightens the boundary between `CompanyMembership` and `SpaceMembership`, strengthening DDD separation.

## Project Structure

### Documentation (this feature)

```text
specs/029-fix-company-membership-space-id/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── post-companies.md
└── tasks.md             # Phase 2 output (/speckit-tasks — not yet created)
```

### Source Code (affected paths only)

```text
apps/api/
├── tessera_api/
│   └── adapters/
│       └── repo.py                         # rename + 3 call-site updates
└── tests/
    └── unit/
        └── test_company_repo.py            # new tests for mapper correctness
```

## Implementation Detail

### Change 1 — Rename mapper (repo.py line 985)

```python
# Before
def _membership_from_model(m: CompanyMembershipModel) -> CompanyMembership:

# After
def _company_membership_from_model(m: CompanyMembershipModel) -> CompanyMembership:
```

### Change 2 — Update `add_membership` call site (repo.py ~line 1029)

```python
# Before
return _membership_from_model(model)

# After
return _company_membership_from_model(model)
```

### Change 3 — Update `get_membership` call site (repo.py ~line 1039)

```python
# Before
return _membership_from_model(model) if model else None

# After
return _company_membership_from_model(model) if model else None
```

### Change 4 — Update `list_memberships_for_user` call site (repo.py ~line 1045)

```python
# Before
return [_membership_from_model(m) for m in result.scalars().all()]

# After
return [_company_membership_from_model(m) for m in result.scalars().all()]
```

### Change 5 — New/updated unit tests (test_company_repo.py)

New tests to add to `TestSqlCompanyRepositoryMembership`:

- `test_add_membership_returns_company_membership_type` — asserts `result` is `CompanyMembership` and has `company_id` field (no `space_id`)
- `test_add_membership_role_value_round_trips` — asserts `result.role == CompanyRole.ADMIN`
- `test_get_membership_returns_company_membership_when_found` — mocks a `CompanyMembershipModel` return, asserts correct mapping
- `test_list_memberships_for_user_returns_company_memberships` — asserts each item in list is a `CompanyMembership`

## Complexity Tracking

No constitution violations. This section is intentionally empty.
