# Contract: `DELETE /v1/spaces/{space_id}` (new)

New endpoint in the spaces router (`apps/api/tessera_api/routers/spaces.py`),
alongside the existing `DELETE /v1/spaces/{space_id}/parent` (`remove_space_parent`).

## Request

```
DELETE /v1/spaces/8f0e2f2a-....
Authorization: Bearer <access_token>
Content-Type: application/json

{ "password": "the-caller's-current-account-password" }
```

| Field | Type | Required |
|-------|------|----------|
| `password` | `string` | yes |

`company_id` and `actor_id` are never accepted in the body — both come from
the authenticated context (Tenant Isolation).

## Resolution & authorization order

1. Resolve `(user_info, company_id, caller_membership)` from `CompanyMemberContext`
   (same dependency `delete_document` already uses); `actor_id = UUID(user_info["sub"])`,
   `company_admin = is_company_admin(caller_membership)`.
2. Verify the caller's password: `SqlUserRepository.get_by_id(actor_id)` then
   `verify_password(body.password, user.password_hash)`.
   - Missing user, no password hash, or mismatch → `401
     {"error": {"code": "invalid_credentials", "message": "Current password is incorrect"}}`
     (identical shape to `/v1/auth/change-password`'s failure response). Nothing is touched.
3. Call `SpaceHierarchyService.delete(actor_id, space_id, company_id, is_company_admin=company_admin)`
   — a single call that resolves, authorizes, *and executes*, exactly like `rename`/`set_parent`
   do today:
   - Resolves the target space via `get_by_id_for_company(space_id, company_id)`; miss →
     `ValueError("not_found")` → router writes a `cross_tenant_denied` audit, commits, and raises
     `404 {"error": {"code": "not_found", ...}}` (identical pattern to `rename_space`'s not-found
     branch).
   - Not ADMIN on the space and not a company admin → `PermissionError` → router raises
     `403 {"error": {"code": "forbidden", ...}}` (existing `_forbidden()` helper). Nothing is
     deleted.
   - Otherwise calls `self._spaces.delete_subtree(space_id)` and returns its
     `(deleted_space_count, deleted_document_count)`.
4. On success: write one `space_deleted` audit record with both counts in `metadata`; return `200`.

Password verification (step 2) intentionally runs *first*, before the space is
even resolved — it depends only on the caller's own credentials, so checking
it first can't leak anything about the target space's existence or the
caller's permissions on it, and it lets `SpaceHierarchyService.delete` stay a
single check-and-mutate call like every other space-hierarchy method
(`rename`, `set_parent`, `remove_parent`, `create`) instead of splitting
authorization from execution.

## Response

**Success** (`200`):

```json
{
  "deleted": true,
  "space_id": "8f0e2f2a-...",
  "deleted_space_count": 4,
  "deleted_document_count": 17
}
```

`deleted_space_count` includes the target space itself (so `1` for a leaf
space with no children).

**Errors**:

| Status | Body | Condition |
|---|---|---|
| 404 | `{"error": {"code": "not_found", ...}}` | Space doesn't exist, or belongs to a different company |
| 403 | `{"error": {"code": "forbidden", ...}}` | Caller is not ADMIN on the space and not a company admin |
| 401 | `{"error": {"code": "invalid_credentials", "message": "Current password is incorrect"}}` | `password` field doesn't match the caller's account password |
| 422 | FastAPI default validation error | `password` field missing/wrong type |

## Side effects

- Deletes the target space and every descendant space at any depth.
- Cascades (via existing DB foreign keys, no new code) to: documents, document
  versions, document drafts, update proposals, chunks (search index), space
  memberships, role permissions, connectors, and connectors' source artifacts —
  scoped to the deleted spaces.
- Writes exactly one audit record, `action: "space_deleted"`, `entity_type:
  "space"`, `entity_id: <target space_id>`, with `metadata: {"company_id":
  ..., "deleted_space_count": ..., "deleted_document_count": ...}`. The audit
  record has no foreign key to `spaces` and survives the deletion.
- Does not affect any space outside the deleted subtree, in this company or any other.
