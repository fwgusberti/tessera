# Data Model: Enrollment Admin Role Assignment (032)

## Changed Entity

### `OnboardingProgress` (packages/core/tessera_core/domain/entities.py)

| Field | Type | Nullable | Default | Notes |
|---|---|---|---|---|
| id | UUID | No | uuid4() | |
| user_id | UUID | No | — | FK to User |
| completed_steps | list[str] | No | [] | |
| current_step | str | No | "profile" | |
| company_join_method | str \| None | Yes | None | "created" or "joined" |
| **company_id** | **UUID \| None** | **Yes** | **None** | **NEW — ID of company created during enrollment** |
| completed_at | datetime \| None | Yes | None | |
| created_at | datetime \| None | Yes | None | |
| updated_at | datetime \| None | Yes | None | |

**Key rule**: `company_id` is set only when `company_join_method == "created"`. It is `None` for joiners and for any enrollment where company step is not yet reached.

---

## DB Schema Change

### `onboarding_progress` table (migration 0008)

```sql
ALTER TABLE onboarding_progress
  ADD COLUMN company_id UUID
    REFERENCES companies(id) ON DELETE SET NULL;
```

- Nullable: no backfill needed for existing rows
- `ON DELETE SET NULL`: if a company is deleted, the enrollment record is safely preserved without a dangling FK

---

## Unchanged Entities (referenced for context)

### `CompanyMembership`

| Field | Type | Notes |
|---|---|---|
| id | UUID | |
| user_id | UUID | |
| company_id | UUID | |
| role | CompanyRole | ADMIN or MEMBER |
| joined_at | datetime \| None | |

Unique constraint: `(user_id, company_id)` — enforces idempotency.

### `Company`

| Field | Type | Notes |
|---|---|---|
| id | UUID | |
| name | str | |
| industry | str \| None | |
| team_size | str \| None | |
| admin_user_id | UUID | First admin — not modified by this feature |
| created_at | datetime \| None | |
| updated_at | datetime \| None | |

---

## State Transitions

```
Enrollment flow for creator:
  profile step → company step
    POST /companies called:
      Company created
      CompanyMembership(role=ADMIN) created      ← admin assigned here (for invite step)
      OnboardingProgress.company_join_method = "created"
      OnboardingProgress.company_id = company.id  ← NEW
    → invite step
  complete step
    POST /onboarding/complete called:
      OnboardingProgress.completed_at = now
      if company_join_method == "created" and company_id:
        get_membership(user_id, company_id) → if None: add_membership(ADMIN)  ← idempotent
      User.onboarding_completed = True

Enrollment flow for joiner (via invitation or domain):
  profile step → company step
    POST /companies/{id}/join called:
      CompanyMembership(role=MEMBER) created
      OnboardingProgress.company_join_method = "joined"
      OnboardingProgress.company_id = None          ← not set
    → complete step
  complete step
    POST /onboarding/complete called:
      OnboardingProgress.completed_at = now
      company_join_method != "created" → skip admin block
      User.onboarding_completed = True
```
