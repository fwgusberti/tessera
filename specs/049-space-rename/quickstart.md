# Quickstart Validation Guide: Space Rename

## Prerequisites

- Stack running locally (`make dev`), including the API and web app.
- Two registered users in the same company sharing space `SPACE_ID`:
  `SPACE_ADMIN` (holds `ADMIN` `SpaceRole` on `SPACE_ID`) and `SPACE_VIEWER`
  (holds `VIEWER` or `EDITOR` `SpaceRole` on `SPACE_ID`, but not admin).
- A second space `OTHER_COMPANY_SPACE_ID` belonging to a different company,
  for the cross-tenant check.

## Scenario 1: Admin renames a space from the Spaces menu (US1)

Frontend: sign in as `SPACE_ADMIN`, open `/spaces`, find the tile for
`SPACE_ID`, click **Rename**, change the name, click **Save**. Expect: the
tile updates immediately with the new name, no full page reload. Reload the
page — the new name persists.

API equivalent:
```bash
TOKEN="<SPACE_ADMIN access token>"
curl -s -X PATCH http://localhost:8000/v1/spaces/$SPACE_ID/name \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Renamed Space"}' | jq
# Expected: {"space": {"id": "<SPACE_ID>", "name": "Renamed Space", ...}}

curl -s http://localhost:8000/v1/spaces -H "Authorization: Bearer $TOKEN" \
  | jq '.spaces[] | select(.id == "'"$SPACE_ID"'") | .name'
# Expected: "Renamed Space"
```

## Scenario 2: Empty or whitespace-only name is rejected (Acceptance Scenario 2, FR-004)

```bash
curl -s -X PATCH http://localhost:8000/v1/spaces/$SPACE_ID/name \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "   "}' -o /dev/null -w "%{http_code}\n"
# Expected: 400

curl -s http://localhost:8000/v1/spaces -H "Authorization: Bearer $TOKEN" \
  | jq '.spaces[] | select(.id == "'"$SPACE_ID"'") | .name'
# Expected: unchanged from before this scenario
```

## Scenario 3: Cancel leaves the space untouched (Acceptance Scenario 3)

Frontend only: sign in as `SPACE_ADMIN`, open the rename control, change the
text, click **Cancel**. Expect: no network request is sent, the tile still
shows the original name.

## Scenario 4: Non-admin cannot rename (US2, FR-002/FR-005)

Frontend: sign in as `SPACE_VIEWER`, open `/spaces`. Expect: no **Rename**
control appears on the `SPACE_ID` tile.

API equivalent (bypassing the UI):
```bash
TOKEN="<SPACE_VIEWER access token>"
curl -s -X PATCH http://localhost:8000/v1/spaces/$SPACE_ID/name \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Hijacked Name"}' -o /dev/null -w "%{http_code}\n"
# Expected: 403, and the space's name is unchanged
```

## Scenario 5: Duplicate names are allowed (Acceptance Scenario 4, FR-008)

```bash
curl -s -X PATCH http://localhost:8000/v1/spaces/$SPACE_ID/name \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "<name of another existing space in the same company>"}' | jq
# Expected: 200, rename succeeds — no uniqueness error
```

## Scenario 6: Cross-tenant rename returns 404 (Constitution Principle VI)

```bash
TOKEN="<SPACE_ADMIN access token, still scoped to the original company>"
curl -s -X PATCH http://localhost:8000/v1/spaces/$OTHER_COMPANY_SPACE_ID/name \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Should not work"}' -o /dev/null -w "%{http_code}\n"
# Expected: 404 (indistinguishable from a nonexistent space ID)
```

## Running Unit Tests

```bash
cd packages/core
.venv/bin/python -m pytest tests/test_space_hierarchy.py -v --no-cov

cd ../../apps/api
.venv/bin/python -m pytest tests/unit/test_spaces_router.py -v --no-cov
```

All tests must pass, including new cases for: admin can rename, non-admin
rejected with `PermissionError`, empty/whitespace name rejected, name over
255 chars rejected, duplicate name across spaces allowed, cross-tenant space
ID returns not-found and the repository's `rename` is never called, and the
audit record is written with `action="space_renamed"`.

```bash
cd apps/web && npx vitest run tests/space-rename.test.tsx
```
Must include: Rename control visible for admin, hidden for non-admin, cancel
leaves state untouched, save calls the rename endpoint and updates the tile
in place, and a failed save shows an error message while keeping the
original name displayed.
