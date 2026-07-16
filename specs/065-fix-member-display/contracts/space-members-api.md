# API Contract: Space Members List (enriched)

**Feature**: `065-fix-member-display` | **Date**: 2026-07-12

One modified endpoint. All other member endpoints (invite, change role,
remove, `/members/me`, `/members/search`) are unchanged.

## `GET /v1/spaces/{space_id}/members` (MODIFIED — additive)

**Auth**: Bearer JWT with active company context (`CompanyMemberContext`).
Caller must be a member of the space or a company admin — unchanged.

**Response `200`** — each row gains `display_name` and `email`; all previous
fields are preserved; rows are ordered by `display_name` ascending:

```json
{
  "members": [
    {
      "id": "5f3c…",
      "space_id": "9a1b…",
      "user_id": "c07d…",
      "display_name": "Ana Souza",
      "email": "ana@example.com",
      "role": "admin",
      "invited_by_user_id": null,
      "created_at": "2026-07-01T12:00:00Z",
      "updated_at": "2026-07-01T12:00:00Z"
    }
  ]
}
```

Field contracts:

| Field | Type | Contract |
|-------|------|----------|
| display_name | string | User's display name; may be `""` (blank) — never null |
| email | string | User's email; always present for registered users |
| (all others) | unchanged | Same types/semantics as before this feature |

**Errors** (unchanged): `401` unauthenticated / actor not found; `403` caller
not a member of the space (and not company admin); `404` generic body
`{"error": {"code": "not_found", "message": "Not found"}}` when the space
does not belong to the caller's active company (indistinguishable from
absent; cross-tenant probe additionally writes a `cross_tenant_denied` audit
record). Cross-tenant responses MUST NOT contain any member identity data.

**Backward compatibility**: additive — existing consumers reading
`user_id`/`role` (role-change and remove flows) are unaffected.

## UI contract: member identity presentation (all member-listing surfaces)

Applies to the space members panel (`SpaceMembersPanel`), the company Users
page, and the add-member search results (SC-004).

- **Primary label**: `display_name`; if blank → `email`; if both unavailable
  → literal `"Unknown user"`. A raw system identifier (UUID) is never
  rendered as a person's label (FR-004).
- **Secondary line**: `email` in muted small text (`text-xs text-slate-500`),
  shown only when `display_name` is non-blank (avoids duplicating the email
  when it is already the primary label).
- **Overflow**: long names/emails truncate within their cell (`truncate`);
  the row/table layout must not break (spec edge case).
- **Actions**: role change and removal keep targeting the row's `user_id`
  (`PUT`/`DELETE /v1/spaces/{space_id}/members/{user_id}`) — display change
  only (FR-005).
