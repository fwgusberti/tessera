# Phase 1 Data Model: Admin-Added Members Onboarding Trap

**No schema changes.** This feature reinterprets existing data; it adds no
tables, columns, indexes, or migrations. This document records the entities
involved and the invariant the fix establishes.

## Entities (existing, unchanged shape)

### CompanyMembership (`company_memberships`)
- **Fields (relevant)**: `id`, `user_id`, `company_id`, `role`.
- **Role in this feature**: its **existence for a `user_id`** is the authoritative
  signal that the user "has a company" and has therefore satisfied the
  company-setup portion of onboarding.
- **Access pattern added**: existence-by-`user_id`
  (`list_memberships_for_user(user_id)` → non-empty?). Keyed only on the
  authenticated caller's own id.

### OnboardingProgress (`onboarding_progress`)
- **Fields**: `id`, `user_id`, `completed_steps: list[str]`,
  `current_step: str` (default `"profile"`), `company_join_method: str | None`,
  `company_id: UUID | None`, `completed_at: datetime | None`, timestamps.
- **Role in this feature**: `completed_at` was the *sole* onboarding-completion
  signal and is the root cause when it stays `None` for admin-added users. After
  this change it is **one of two** satisfying conditions (the other being
  membership). Still written by the self-create/approve/complete flows, and now
  also by `add_company_member` (Decision 2).
- **`company_join_method`**: gains an `"added"` value for the admin-direct-add
  path (alongside existing `"created"` / `"joined"`). Free-form `str`; no schema
  change (`String(20)` column already permits it).

### User (`users`)
- **Field (relevant)**: `onboarding_completed: bool` (default `False`). Currently
  written by `/onboarding/complete` but **not read by any gate** (both gates use
  `OnboardingProgress.completed_at`). Left as-is; optionally set to `True` in the
  admin-add path for consistency (no gate depends on it).

## Domain predicate (new, pure)

Added to `packages/core/tessera_core/domain/onboarding_progress.py` — pure, no
framework/persistence imports (Principle I):

```
has_completed_onboarding(progress: OnboardingProgress | None,
                         has_company_membership: bool) -> bool
    returns True iff:
        has_company_membership
        OR (progress is not None AND progress.completed_at is not None)
```

**Invariant established**: *a user who belongs to at least one company is
considered onboarded, regardless of `completed_at`.* Conversely, a user with no
membership and no `completed_at` is **not** onboarded (preserves FR-007).

## State transition (added-user path, after fix)

```
registered, no company, completed_at = None
        │  (admin) POST /companies/members
        ▼
CompanyMembership created  ──►  onboarding persisted complete
                                (completed_at set, company_join_method="added",
                                 company_id set) + audit onboarding.completed
        │  next login
        ▼
login mints FULL token (membership count == 1)
        │
        ▼
server gate: has_company_membership → onboarding satisfied → NO 403
status endpoint: completed = true
        │
        ▼
frontend OnboardingGuard admits user → app + company documents (FR-004)
```

Existing already-trapped members (added before this change) reach the same
"onboarding satisfied" verdict purely via the membership branch of the predicate
on their next request — **no migration** (FR-006).
