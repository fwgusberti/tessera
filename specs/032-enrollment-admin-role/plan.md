# Implementation Plan: Enrollment Admin Role Assignment

**Branch**: `032-enrollment-admin-role` | **Date**: 2026-06-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/032-enrollment-admin-role/spec.md`

## Summary

When a user completes company enrollment as the company creator, the system must guarantee they hold the `CompanyRole.ADMIN` membership at the moment enrollment is marked complete. The implementation extends the `POST /onboarding/complete` endpoint to read the `company_join_method` recorded during the company-creation step and idempotently ensure the admin membership exists, covering retry and partial-failure scenarios. A new nullable `company_id` column on `onboarding_progress` carries the created company's ID forward to enrollment completion without requiring a secondary lookup.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (async), Pydantic v2, Alembic, pytest / pytest-anyio

**Storage**: PostgreSQL (system of record); `company_memberships` table with unique constraint `(user_id, company_id)`

**Testing**: pytest with `@pytest.mark.anyio` (API package); `fastapi.testclient.TestClient` (sync) for integration tests

**Target Platform**: Linux server (containerized)

**Project Type**: Web service (multi-package monorepo: `packages/core`, `apps/api`)

**Performance Goals**: No specific goals; single-user enrollment path, negligible throughput concern

**Constraints**: Changes must be backward-compatible at the DB level (nullable column, no column removal)

**Scale/Scope**: Single new DB column, two modified endpoints, one new migration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Domain-Driven Architecture ✅
- `OnboardingProgress` domain entity updated in `packages/core` (domain layer)
- No framework imports in entity or port files
- Router changes remain in the infrastructure/adapter layer

### II. Separation of Concerns ✅
- Domain entity (`OnboardingProgress`) and port (`OnboardingRepository`) are technology-agnostic
- SQLAlchemy model and `SqlOnboardingRepository` remain in the adapter layer

### III. Data Locality & Consent ✅
- No client-side data storage introduced

### IV. Test-Driven Development ✅ (GATE)
- Failing tests written before implementation for every new behavior
- Integration tests cover the golden path (creator gets admin at completion) and edge cases (idempotency, non-creator does not get admin)
- 85% statement coverage maintained

### V. Quality Gates ✅
- Ruff + Black pass before commit

### VI. Tenant Data Isolation ✅
**Tables accessed**: `onboarding_progress`, `company_memberships`

| Table | Scoping | Notes |
|---|---|---|
| `onboarding_progress` | `WHERE user_id = <authenticated user>` | One row per user; `user_id` derived from JWT, never from request body |
| `company_memberships` | `WHERE user_id = <authenticated user> AND company_id = <progress.company_id>` | `company_id` taken from the server-side `OnboardingProgress` record, not from caller |

**Cross-tenant isolation**: The `company_id` stored in `OnboardingProgress` is set server-side during company creation (not user-supplied at completion time). A user cannot target another tenant's company by manipulating the complete request.

**Isolation tests to write**:
- A user who created Company A cannot have their `onboarding/complete` call assign admin on Company B
- A user who joined (not created) a company receives no admin assignment at completion

## Project Structure

### Documentation (this feature)

```text
specs/032-enrollment-admin-role/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
packages/core/tessera_core/
├── domain/
│   └── entities.py          # Add company_id field to OnboardingProgress
└── ports/
    └── repositories.py      # Update advance_step signature on OnboardingRepository

apps/api/tessera_api/
├── adapters/
│   ├── models.py            # Add company_id column to OnboardingProgressModel
│   └── repo.py              # Update SqlOnboardingRepository.advance_step + SqlOnboardingRepository._from_model
├── routers/
│   ├── onboarding.py        # Extend complete_onboarding to ensure admin membership
│   └── companies.py         # Pass company_id to advance_step in create_company
└── tests/
    ├── integration/
    │   ├── test_onboarding.py         # Add new tests for admin assignment at completion
    │   └── test_onboarding_gate.py    # Verify gate still passes
    └── unit/
        └── test_company_repo.py       # Idempotency unit test for add_membership

db/migrations/versions/
└── 0008_onboarding_company_id.py     # ALTER TABLE onboarding_progress ADD COLUMN company_id
```

**Structure Decision**: Standard multi-package layout. Changes span `packages/core` (domain + port), `apps/api` (adapter + router + tests), and `db/migrations`.

## Complexity Tracking

No constitution violations. No complexity justification required.

---

## Phase 0: Research

### Resolved Questions

**Q: Is there already a unique constraint on `(user_id, company_id)` in `company_memberships`?**
Decision: Yes — `uq_company_membership` constraint exists (verified in `0004_onboarding.py` migration and `CompanyMembershipModel.__table_args__`).
Rationale: The idempotent-assign strategy must use `get_membership` → conditional `add_membership` to avoid integrity errors on duplicate calls. An `ON CONFLICT DO NOTHING` SQL approach is an alternative but `get_membership` + conditional insert is cleaner within the existing pattern.
Alternatives considered: `ON CONFLICT DO NOTHING` (raw SQL, deviates from pattern), upsert via repository (overkill for a nullable path).

**Q: Can we find the company created during enrollment without adding a `company_id` column?**
Decision: No — reliable lookup requires storing `company_id` in `OnboardingProgress`.
Rationale: Looking up `Company WHERE admin_user_id = user_id` could return multiple companies (user may create a second company after onboarding). Using `list_memberships_for_user` + filter for ADMIN is possible but fragile and doesn't distinguish "enrollment company" from "later-created company". Adding a nullable `company_id` column is the only design that is unambiguous and forward-safe.
Alternatives considered: Lookup by `admin_user_id` (ambiguous for multi-company users), filtering admin memberships at completion (fragile).

**Q: Will storing `company_id` in `OnboardingProgress` break the invite step?**
Decision: No — the admin membership is still assigned at company creation time (needed for the invite step that follows). The `company_id` stored in `OnboardingProgress` is used only at `POST /onboarding/complete` for idempotent re-verification.
Rationale: `POST /companies` → assigns ADMIN membership → advance_step(…, company_id=company.id) → user continues to invite step as admin. Enrollment completion then re-verifies atomically.

**Q: What happens when a user joins via invitation or domain match?**
Decision: At `POST /onboarding/complete`, if `company_join_method == "joined"` (or `None`), no admin assignment is made. The join endpoints already assign `CompanyRole.MEMBER`.
Rationale: FR-004 requires only creators to receive admin. Joiners must never receive admin through this path.

**Q: Should admin assignment be moved out of `POST /companies` and into `POST /onboarding/complete`?**
Decision: No — keep the existing assignment in `POST /companies` and add verification at `POST /onboarding/complete`.
Rationale: The invite step (step 3 of onboarding) requires the creator to have admin access to send invitations. If admin is only assigned at enrollment completion (step 4), the invite step would fail. Keeping assignment at company creation is necessary; verifying at completion adds resilience.

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](./data-model.md) for full entity definitions.

**Key change**: `OnboardingProgress.company_id: UUID | None`

```
OnboardingProgress
├── id: UUID (PK)
├── user_id: UUID (FK users, unique)
├── completed_steps: list[str]
├── current_step: str
├── company_join_method: str | None   # "created" | "joined"
├── company_id: UUID | None           # NEW — set when method="created"
├── completed_at: datetime | None
├── created_at: datetime
└── updated_at: datetime
```

**Migration**: `ALTER TABLE onboarding_progress ADD COLUMN company_id UUID REFERENCES companies(id) ON DELETE SET NULL;`

### API Contracts

See [contracts/](./contracts/) for full OpenAPI fragments.

**Modified endpoints** (no new endpoints, no breaking changes):

`POST /v1/onboarding/complete`
- Input: (unchanged — no body)
- New behavior: if `progress.company_join_method == "created"` and `progress.company_id` is set, idempotently ensure `CompanyMembership(user_id, company_id, role=ADMIN)` exists
- Response: (unchanged)

`POST /v1/companies`
- Input/output: (unchanged)
- New behavior: passes `company_id=company.id` to `advance_step`

### Implementation Logic

#### `POST /companies` (create_company in companies.py)

```
# EXISTING: company and membership created atomically
company = await company_repo.create(...)
membership = await company_repo.add_membership(CompanyMembership(..., role=ADMIN))

# CHANGE: pass company_id to advance_step
await ob_repo.advance_step(user_id, "invite",
    company_join_method="created",
    company_id=company.id)          # NEW argument
```

#### `POST /onboarding/complete` (complete_onboarding in onboarding.py)

```
async with get_db() as session:
    ob_repo = SqlOnboardingRepository(session)
    progress = await ob_repo.complete(user_id)

    # NEW: idempotent admin role enforcement for company creators
    if progress.company_join_method == "created" and progress.company_id:
        company_repo = SqlCompanyRepository(session)
        existing = await company_repo.get_membership(user_id, progress.company_id)
        if existing is None:
            await company_repo.add_membership(
                CompanyMembership(user_id=user_id,
                                  company_id=progress.company_id,
                                  role=CompanyRole.ADMIN)
            )

    # EXISTING: mark user onboarding_completed=True
    await session.execute(sa_update(UserModel).where(...).values(onboarding_completed=True))

    await write_audit(..., action="onboarding.completed", ...)
    # NEW audit event (only if admin membership was ensured at this step)
```

#### `SqlOnboardingRepository.advance_step` (repo.py)

Add `company_id: UUID | None = None` parameter and persist to model:
```python
async def advance_step(
    self, user_id: UUID, next_step: str,
    company_join_method: str | None = None,
    company_id: UUID | None = None,          # NEW
) -> OnboardingProgress:
    ...
    if company_id is not None:
        model.company_id = company_id        # NEW
    ...
```

#### `OnboardingRepository.advance_step` (ports/repositories.py)

```python
@abstractmethod
async def advance_step(
    self, user_id: UUID, next_step: str,
    company_join_method: str | None = None,
    company_id: UUID | None = None,          # NEW
) -> OnboardingProgress: ...
```

### Test Coverage Plan

**Integration tests** (`apps/api/tests/integration/test_onboarding.py`):

| Test | Scenario | Assertion |
|---|---|---|
| `test_complete_assigns_admin_for_creator` | User who created company calls complete | CompanyMembership with ADMIN role exists |
| `test_complete_idempotent_admin_already_exists` | Admin membership already exists before complete | No error, still ADMIN (not duplicated) |
| `test_complete_does_not_assign_admin_for_joiner` | User who joined calls complete | No new membership created / MEMBER role unchanged |
| `test_complete_no_company_join_method_safe` | User completes without any company step | No error, no admin assignment |

**Existing tests to extend/not break**:
- `TestPostOnboardingComplete` — add mocks for `SqlCompanyRepository` where needed

### Quickstart Validation

See [quickstart.md](./quickstart.md) for runnable scenarios.
