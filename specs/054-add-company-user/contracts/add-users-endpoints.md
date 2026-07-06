# Contract: Add-User Endpoints

All three endpoints live on the existing `companies` router, are gated by
`CompanyAdminContext`, and derive `company_id` solely from the authenticated
context. Common auth failures for every endpoint:

- **401** — unauthenticated (no session / no bearer). Body: `{"detail": "Not authenticated"}` or `{"error": {"code": "invalid_token", ...}}`.
- **403** — authenticated but not an admin of the active company, or no active-company context. Body: `{"error": {"code": "forbidden", "message": "Access denied"}}`.

`role` is `"admin" | "member"` and defaults to `"member"` when omitted (FR-004).

---

## GET /v1/companies/addable-users

Type-ahead search of registered users **not already in the active company** (US2, FR-005).

**Query params**
- `q` (string, required, min length 2) — matched case-insensitively against `display_name` and `email`. A shorter/empty `q` → **422**.

**200 Response**
```json
{
  "users": [
    { "user_id": "uuid", "display_name": "Ada Lovelace", "email": "ada@x.com" }
  ]
}
```
Returns identity fields only; excludes current members of the active company;
ordered by display name; capped (limit 20). Never reveals a candidate's
memberships in other companies.

---

## POST /v1/companies/members

Direct-add an already-registered user to the active company **immediately** (US2, FR-003).

**Request**
```json
{ "user_id": "uuid", "role": "member" }
```

**201 Response** — new membership created (roster reflects it in place, FR-013):
```json
{
  "member": {
    "user_id": "uuid",
    "display_name": "Ada Lovelace",
    "email": "ada@x.com",
    "role": "member"
  }
}
```

**Errors**
- **404** `{"error": {"code": "no_such_user", ...}}` — no account matches `user_id` (edge case: direct-add target does not exist).
- **409** `{"error": {"code": "already_member", ...}}` — user is already a member (FR-007); also returned when a concurrent insert trips `uq_company_membership`.
- **422** — malformed body / invalid `role`.

Emits audit `company.member_added` (actor = admin, entity = new membership id).

---

## POST /v1/companies/invitations

Invite a person by email to the active company with a chosen role (US1, FR-002).

**Request**
```json
{ "email": "new.person@x.com", "role": "member" }
```
`email` is validated as an email address (Pydantic `EmailStr`); malformed → **422**
and nothing is sent (FR-006).

**201 Response** — pending invitation created and email dispatched:
```json
{ "status": "sent", "email": "new.person@x.com", "role": "member" }
```

**Errors**
- **409** `{"error": {"code": "already_member", ...}}` — the email belongs to a current member (FR-007).
- **409** `{"error": {"code": "already_invited", ...}}` — a pending invitation for this email already exists in the active company (FR-008); also returned when a concurrent insert trips the partial unique index.
- **502** `{"error": {"code": "send_failed", ...}}` — the invitation row was created but email delivery failed; the admin is told it was not delivered (edge case: email delivery failure). *(Implementation note: mirror the existing `send_invitation_email` try/except; surface the failure rather than reporting success.)*

Emits audit `invitation.sent` (actor = admin, entity = invitation id) on success.

---

## Outcome → message mapping (FR-012, SC-007)

Every attempt yields exactly one unambiguous outcome the frontend renders:

| Outcome            | Endpoint / status                         |
|--------------------|-------------------------------------------|
| success (member)   | `POST /companies/members` 201             |
| success (invited)  | `POST /companies/invitations` 201         |
| already a member   | 409 `already_member` (either add path)    |
| already invited    | 409 `already_invited` (invite path)       |
| invalid email      | 422 (invite path)                         |
| no such user       | 404 `no_such_user` (direct-add path)      |
| delivery failure   | 502 `send_failed` (invite path)           |
| forbidden          | 403 (non-admin) — no write performed      |
| unauthenticated    | 401 — no write performed                  |
