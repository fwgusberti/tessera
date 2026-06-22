# API Contract: Onboarding Endpoints (032 changes)

## POST /v1/onboarding/complete

**Auth**: Bearer JWT required

**Request body**: None (empty body OK)

**New behavior** (032):
- Reads `OnboardingProgress.company_join_method` for the authenticated user
- If `company_join_method == "created"` AND `company_id` is not null:
  - Checks whether a `CompanyMembership(user_id, company_id, role=ADMIN)` exists
  - If not found: creates it (idempotent — the unique constraint prevents duplicates on concurrent calls)
- If `company_join_method != "created"` or `company_id` is null: skips admin block

**Response** (unchanged):

```json
{
  "completed": true,
  "completed_at": "2026-06-22T15:00:00+00:00"
}
```

**Error cases** (unchanged):
- `401 Unauthorized` — missing/invalid JWT
- `500 Internal Server Error` — onboarding progress record not found (user must have called `/status` first)

---

## POST /v1/companies

**Auth**: Bearer JWT required

**Request body** (unchanged):
```json
{
  "name": "Acme Corp",
  "industry": "Technology",
  "team_size": "1-10"
}
```

**Behavior change** (032):
- `OnboardingProgress.company_id` is now set to the newly created company's ID in `advance_step`

**Response** (unchanged):
```json
{
  "id": "<uuid>",
  "name": "Acme Corp",
  "industry": "Technology",
  "team_size": "1-10",
  "role": "admin",
  "created_at": "2026-06-22T15:00:00+00:00",
  "token": "<company-scoped JWT>"
}
```

---

*No new endpoints are introduced by this feature.*
