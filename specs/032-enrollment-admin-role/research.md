# Research: Enrollment Admin Role Assignment (032)

## Q1: Unique constraint on `company_memberships(user_id, company_id)`?

**Decision**: Yes — `uq_company_membership` exists in the DB schema.

**Rationale**: Verified in `db/migrations/versions/0004_onboarding.py` and `apps/api/tessera_api/adapters/models.py` (`CompanyMembershipModel.__table_args__`). Duplicate `add_membership` calls for the same `(user_id, company_id)` pair raise an IntegrityError.

**How to apply**: Idempotent admin assignment at enrollment completion must call `get_membership` first and only call `add_membership` if the membership does not yet exist.

---

## Q2: Finding the company created during enrollment without a new column?

**Decision**: Cannot be done reliably — must store `company_id` in `OnboardingProgress`.

**Rationale**: `Company.admin_user_id` is not a reliable enrollment-time pointer because a user may create additional companies after onboarding. `list_memberships_for_user` + filter for ADMIN would also be ambiguous in the multi-company case. A nullable `company_id` column on `onboarding_progress` is the only design that unambiguously ties an enrollment record to its created company.

**Alternatives considered**:
- Lookup by `Company.admin_user_id == user_id`: ambiguous for multi-company users.
- Filtering ADMIN memberships at completion: fragile; a user could acquire ADMIN elsewhere.

---

## Q3: Does adding `company_id` to `OnboardingProgress` break the invite step?

**Decision**: No — admin membership is still assigned at company creation time.

**Rationale**: The invite step (step 3 of onboarding) calls invitation endpoints that require the caller to be a company admin. If admin assignment were moved entirely to enrollment completion (step 4), the invite step would fail. The implementation therefore keeps admin assignment in `POST /companies` and adds idempotent verification at `POST /onboarding/complete`.

---

## Q4: Behavior for users who join (not create) a company?

**Decision**: No admin assignment at enrollment completion for joiners.

**Rationale**: FR-004 explicitly prohibits assigning admin to joiners. `company_join_method == "joined"` → skip admin block in `complete_onboarding`. MEMBER role was already assigned by the join endpoint.

---

## Q5: Should admin assignment be moved to enrollment completion only?

**Decision**: No — keep existing assignment in `POST /companies`; add verification at `POST /onboarding/complete`.

**Rationale**: Explained in Q3. The "keep + verify" model satisfies FR-001 (admin ensured at completion), FR-002 (atomic at creation), FR-006 (idempotent at completion), and FR-007 (immediate from creation).
