# Contracts: Company Profile (060)

**Plan**: [plan.md](../plan.md) | **Data model**: [../data-model.md](../data-model.md)

Two new endpoints on the companies router. The active company is addressed as
the singleton `current` — its id comes exclusively from the authenticated
company context (JWT `company_id` claim); no company id is ever accepted from
the client.

Common error envelope (repo convention):
`{"detail": {"error": {"code": "<code>", "message": "<human text>"}}}`.

Shared auth failures (from `_resolve_company_membership`, both endpoints):

| Status | Code | When |
|---|---|---|
| 401 | — | Missing/invalid/expired token |
| 403 | `credential_not_scoped` | Token has no company scope (select/onboarding kind) |
| 403 | `company_suspended` | Active company suspended |
| 403 | `not_a_member` | Membership revoked or never existed |

---

## GET /v1/companies/current

Read the active company's profile. **Auth**: any member
(`CompanyMemberContext`).

**Response 200**:

```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "name": "Acme Corp",
  "industry": "Technology",
  "team_size": "11-50",
  "created_at": "2026-03-14T09:26:53Z",
  "role": "admin"
}
```

- `industry` / `team_size` are `null` when never provided (client renders
  "Not provided" — FR-003).
- `role` is the **caller's** role (`"admin"` | `"member"`) in this company;
  the client uses it to show or hide edit controls (server remains the
  enforcement point).

---

## PATCH /v1/companies/current

Update the profile. **Auth**: company admin (`CompanyAdminContext`).

**Request body** (all fields required — the form always submits the full
editable profile):

```json
{
  "name": "Acme Corporation",
  "industry": null,
  "team_size": "51-200"
}
```

| Field | Type | Rules |
|---|---|---|
| `name` | string | Required; non-blank after trim; ≤255 chars |
| `industry` | string \| null | ≤100 chars; `null` clears |
| `team_size` | string \| null | One of `1-10`, `11-50`, `51-200`, `201-1000`, `1000+`; `null` clears |

**Response 200**: same shape as GET (the authoritative saved profile —
`role` is always `"admin"` here).

**Errors** (beyond shared auth failures):

| Status | Code | When |
|---|---|---|
| 403 | `forbidden` | Caller is a member but not an admin (FR-008); data unchanged |
| 422 | `invalid_name` | Empty/whitespace-only or >255-char name; stored value preserved (FR-005) |
| 422 | `invalid_team_size` | Value outside the accepted set (same code as `POST /v1/companies`) |

**Side effects**: one `company.updated` audit record (actor, timestamp,
company id, changed-fields map — FR-010/SC-004). Concurrency:
last-write-wins; the response body is always exactly one edit's outcome.

---

## Frontend route contract: `/settings/company`

| Aspect | Contract |
|---|---|
| Access | Authenticated members (via `AuthGuard`; onboarding/tenant guards apply as everywhere). A user with no company never reaches it (guards route to onboarding/select-company). |
| Entry point | `CompanyMenu` dropdown link "Company" — visible to **all** members (admin gate removed). |
| View mode (all members) | Name, industry, team size, creation date; `null` optionals render "Not provided"; creation date read-only always. |
| Edit mode (admins only) | "Edit" button → form prefilled with current values; industry/team-size selects use the shared onboarding option lists; Save / Cancel. |
| Cancel | Discards form state, returns to view mode with original values (FR-006). |
| Save success | View mode with response values; `reloadCompanies()` refreshes the company menu name (FR-007). |
| Save failure (network/5xx) | Stays in edit mode, entered values intact, error banner shown (edge case). |
| Validation | Empty name blocked client-side with message; server 422 messages rendered in the banner. |
| Non-admin | No edit controls rendered (US3); a forged submission is refused server-side with 403. |
