# API Contract: Space Members (Add Space Membership additions)

**Feature**: 043-add-space-membership | **Date**: 2026-06-30

All endpoints require `Authorization: Bearer <access_token>` and are prefixed `/v1`.

---

## New Endpoint

### GET /v1/spaces/{space_id}/members/search

Search company members eligible to be added to this space (FR-002, FR-003).
Authorization is scoped to the target space (FR-002a): the caller must be an
admin of `space_id` (or a company admin) — the same rule enforced by
`POST /v1/spaces/{space_id}/members`.

**Query parameters**:
- `q` (string, required) — name/email search fragment. Server applies the
  query as given; the frontend is responsible for the 2-character minimum and
  debouncing (FR-007).

**Response** `200 OK`:
```json
{
  "members": [
    {
      "user_id": "uuid",
      "display_name": "Ada Lovelace",
      "email": "ada@acme.com"
    }
  ]
}
```
- Results are members of the caller's active company who are **not** already
  members of `space_id` (FR-003), ordered by `display_name`, capped at 20.
- Empty `members: []` is a valid, successful response (FR-008 empty state is a
  frontend concern — the API does not distinguish "no matches" from "not
  searched yet").

**Response** `403 Forbidden`:
```json
{ "error": { "code": "forbidden", "message": "Only space admins can search members" } }
```
Returned when the caller is not an admin of `space_id` and not a company admin.

**Response** `404 Not Found`:
```json
{ "error": { "code": "not_found", "message": "Not found" } }
```
Returned when `space_id` does not belong to the caller's active company
(indistinguishable from a non-existent space — same pattern as the other
members endpoints).

---

## Reused Endpoint (unchanged)

### POST /v1/spaces/{space_id}/members

No contract changes. `AddMemberForm` calls this exactly as `InviteMemberForm`
did, with `{ "user_id": "<selected user's uuid>", "role": "<chosen role>" }`.
Existing responses already cover the FR-006 failure cases:

| Scenario | Status | Body / handling |
|---|---|---|
| Success | `201 Created` | `{ "membership": { ... } }` |
| Already a member (race with another admin) | `400 Bad Request` | message contains "already a member" → maps to FR-006 "already a member" case |
| Caller not a space/company admin | `403 Forbidden` | maps to FR-006 "insufficient permission" case |
| Selected user no longer resolvable (e.g. left company) | `404 Not Found` | maps to FR-006 "no longer eligible" case |
| Network/server error | n/a (fetch failure / 5xx) | maps to FR-006 "generic/network failure" case |
