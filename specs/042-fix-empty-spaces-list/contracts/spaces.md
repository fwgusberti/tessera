# API Contract: Spaces (Fix Empty Spaces List additions)

**Feature**: 042-fix-empty-spaces-list | **Date**: 2026-06-30

All endpoints require `Authorization: Bearer <access_token>` and are prefixed `/v1`.

---

## Modified Endpoint

### POST /v1/spaces

**Request/response schema: unchanged.** Behavior change only.

**New side effect**: the authenticated caller is granted an admin
`SpaceMembership` on the newly created space, in the same request that
creates it. This is what makes the space immediately appear in:

- `GET /v1/spaces` (for the creator)
- `GET /v1/spaces/{space_id}/members` (creator listed with `role: "admin"`)
- Any frontend view that filters by accessible spaces (Spaces page, document
  search space filter)

**Response** `201 Created`: unchanged shape —

```json
{ "space": { "id": "uuid", "slug": "...", "name": "...", "...": "..." } }
```

No regression for existing callers: nothing is removed from the response,
and the new membership row does not need to be read back by the client to
take effect — the next `GET /v1/spaces` call simply reflects it.

---

## No New Endpoints

The orphaned-space backfill (spaces created before this fix, with zero
recorded members) is a one-time data migration, not an API surface — there is
no endpoint to trigger or query it. Its effect is observed the same way as
above: previously-empty `GET /v1/spaces` responses for affected companies'
admins now include their existing spaces, once the migration has run.
