# Quickstart Validation Guide: Delete Space

## Prerequisites

- Stack running locally (`make dev`), including the API and web app.
- `ADMIN_USER`, holding `ADMIN` `SpaceRole` on a space `PARENT_ID` that has at
  least one child space `CHILD_ID` (itself containing at least one document)
  and at least one document directly in `PARENT_ID` — this gives a subtree of
  2 spaces and 2+ documents to verify cascading removal.
- `ADMIN_USER`'s current account password, `ADMIN_PASSWORD`.
- `NON_ADMIN_USER`, holding `EDITOR` or `VIEWER` (not `ADMIN`) on a space
  `OTHER_SPACE_ID` in the same company.
- `COMPANY_ADMIN_USER`, a company admin with no direct `SpaceRole` membership
  on some space `UNMANNED_SPACE_ID` (e.g. its admins have all left) — to
  exercise the company-admin bypass.
- A space `OTHER_COMPANY_SPACE_ID` belonging to a different company, for the
  cross-tenant check.

## Scenario 1: Admin deletes a space with children and documents (US1)

Frontend: sign in as `ADMIN_USER`, open the Spaces page (or the folder view
listing `PARENT_ID`), click **Delete** on the `PARENT_ID` tile. Expect a
confirmation prompt describing that child spaces and documents will also be
removed. Confirm, then enter `ADMIN_PASSWORD` when prompted and submit. Expect:
the tile disappears immediately; reloading the page shows neither `PARENT_ID`
nor `CHILD_ID` anywhere, and their documents no longer appear in search or in
any listing.

API equivalent:
```bash
TOKEN="<ADMIN_USER access token>"
curl -s -X DELETE http://localhost:8000/v1/spaces/$PARENT_ID \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"password": "'"$ADMIN_PASSWORD"'"}' | jq
# Expected: 200 {"deleted": true, "space_id": "...", "deleted_space_count": 2,
#   "deleted_document_count": <N>}

curl -s http://localhost:8000/v1/spaces -H "Authorization: Bearer $TOKEN" \
  | jq '.spaces[] | select(.id == "'"$PARENT_ID"'" or .id == "'"$CHILD_ID"'")'
# Expected: empty (neither space appears)
```

## Scenario 2: Incorrect password blocks deletion (US2, FR-005)

```bash
curl -s -X DELETE http://localhost:8000/v1/spaces/$PARENT_ID \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"password": "definitely-wrong"}' -o /dev/null -w "%{http_code}\n"
# Expected: 401, and the space is still present in GET /v1/spaces
```

## Scenario 3: Cancel at either step leaves everything untouched (US2, FR-013)

Frontend only: open the delete flow, click **Cancel** at the confirmation
step — expect no network request. Repeat, confirm, then cancel/close at the
password step — expect no network request either. Reload the page: the space
and its contents are unchanged.

## Scenario 4: Non-admin cannot delete (US3, FR-002/FR-010)

Frontend: sign in as `NON_ADMIN_USER`, view a space they don't administer.
Expect: no **Delete** action rendered on that tile.

API equivalent (bypassing the UI):
```bash
TOKEN="<NON_ADMIN_USER access token>"
curl -s -X DELETE http://localhost:8000/v1/spaces/$OTHER_SPACE_ID \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"password": "<NON_ADMIN_USER password>"}' -o /dev/null -w "%{http_code}\n"
# Expected: 403, and the space is untouched
```

## Scenario 5: Company admin can delete a space with no direct membership

```bash
TOKEN="<COMPANY_ADMIN_USER access token>"
curl -s -X DELETE http://localhost:8000/v1/spaces/$UNMANNED_SPACE_ID \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"password": "<COMPANY_ADMIN_USER password>"}' | jq
# Expected: 200, deleted despite no SpaceMembership row for this user on that space
```

## Scenario 6: Cross-tenant delete is rejected (Constitution Principle VI)

```bash
TOKEN="<ADMIN_USER access token, scoped to the original company>"
curl -s -X DELETE http://localhost:8000/v1/spaces/$OTHER_COMPANY_SPACE_ID \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"password": "'"$ADMIN_PASSWORD"'"}' -o /dev/null -w "%{http_code}\n"
# Expected: 404 (indistinguishable from nonexistent), and the other company's
# space is fully intact
```

## Scenario 7: Deleting an already-deleted space fails gracefully (Edge Cases, FR-011)

```bash
# Re-run Scenario 1's request a second time against the same $PARENT_ID
curl -s -X DELETE http://localhost:8000/v1/spaces/$PARENT_ID \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"password": "'"$ADMIN_PASSWORD"'"}' -o /dev/null -w "%{http_code}\n"
# Expected: 404, no error, no crash
```

## Running Unit Tests

```bash
cd packages/core
.venv/bin/python -m pytest tests/test_space_hierarchy.py -v --no-cov

cd ../../apps/api
.venv/bin/python -m pytest tests/unit/test_spaces_router.py tests/test_space_hierarchy_isolation.py -v --no-cov
```

All tests must pass, including new cases for: deletion by the space's admin,
deletion by a company admin with no direct membership, deletion rejected for a
non-admin (`PermissionError`), deletion of a nonexistent/cross-company space
(`ValueError("not_found")`), a subtree with multiple descendant levels all
resolved and removed, and the returned `(deleted_space_count,
deleted_document_count)` matching the actual subtree contents.

```bash
cd apps/web && npx vitest run tests/space-delete.test.tsx
```
Must include: **Delete** action visible only on admin-accessible tiles,
confirmation step describes cascading scope, password step required before
the request fires, wrong-password error surfaces without removing the tile,
cancel at either step sends no request, and successful deletion removes the
tile immediately without a full reload.
