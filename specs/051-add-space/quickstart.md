# Quickstart Validation Guide: Add Space

## Prerequisites

- Stack running locally (`make dev`), including the API and web app.
- A registered user, `COMPANY_USER`, belonging to an active company (any role —
  space creation does not require company-admin).
- An existing space `PARENT_SPACE_ID` in the same company on which
  `COMPANY_USER` holds `ADMIN` `SpaceRole` (for the sub-space scenarios), and a
  second existing space `PARENT_SPACE_NOT_ADMIN_ID` where `COMPANY_USER` only
  holds `VIEWER`/`EDITOR`.
- A space `OTHER_COMPANY_SPACE_ID` belonging to a different company, for the
  cross-tenant check.
- A space already nested 9 levels deep (`DEEP_SPACE_ID`, at `_MAX_DEPTH - 1`) to
  exercise the depth-limit rejection.

## Scenario 1: Create a top-level space from the Spaces page (US1)

Frontend: sign in as `COMPANY_USER`, open `/spaces`, click **Add Space**, enter
a name, click **Create**. Expect: a new tile appears in the folder grid
immediately, no full page reload. Reload the page — the space persists. Open
it — the creator has admin access (Rename / Set parent / Members controls all
available).

API equivalent:
```bash
TOKEN="<COMPANY_USER access token>"
curl -s -X POST http://localhost:8000/v1/spaces \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Marketing"}' | jq
# Expected: 201 {"space": {"id": "...", "name": "Marketing", "sector": "General",
#   "slug": "marketing", "parent_space_id": null, ...}}

curl -s http://localhost:8000/v1/spaces -H "Authorization: Bearer $TOKEN" \
  | jq '.spaces[] | select(.name == "Marketing")'
# Expected: present, with "effective_role": "admin", "is_direct": true
```

## Scenario 2: Empty or whitespace-only name is rejected (Acceptance Scenario 2, FR-003)

```bash
curl -s -X POST http://localhost:8000/v1/spaces \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "   "}' -o /dev/null -w "%{http_code}\n"
# Expected: 400, and no space named "   " appears in GET /v1/spaces
```

## Scenario 3: Cancel leaves no trace (Acceptance Scenario 3)

Frontend only: sign in as `COMPANY_USER`, open **Add Space**, type a name,
click **Cancel**. Expect: no network request is sent, no new tile appears.

## Scenario 4: Duplicate names are allowed (Acceptance Scenario 4, FR-009)

```bash
curl -s -X POST http://localhost:8000/v1/spaces \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Marketing"}' | jq '.space.id'
# Expected: 201, a second distinct space with the same name and a
# disambiguated slug (e.g. "marketing-2")
```

## Scenario 5: Create a nested sub-space from a folder view (US2)

Frontend: sign in as `COMPANY_USER`, navigate to `/spaces/PARENT_SPACE_ID`,
click **Add Space**, enter a name, click **Create**. Expect: the new tile
appears in that folder view immediately, and its parent (visible via the
top-level Spaces page or its breadcrumb) is `PARENT_SPACE_ID`.

API equivalent:
```bash
curl -s -X POST http://localhost:8000/v1/spaces \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Q3 Campaigns", "parent_space_id": "'"$PARENT_SPACE_ID"'"}' | jq
# Expected: 201 {"space": {"name": "Q3 Campaigns", "parent_space_id": "<PARENT_SPACE_ID>", ...}}
```

## Scenario 6: Sub-space creation requires admin on the parent (FR-005/FR-006, Edge Cases)

```bash
curl -s -X POST http://localhost:8000/v1/spaces \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Should Fail", "parent_space_id": "'"$PARENT_SPACE_NOT_ADMIN_ID"'"}' \
  -o /dev/null -w "%{http_code}\n"
# Expected: 403, and no space is created
```

## Scenario 7: Depth limit is enforced (Acceptance Scenario 2 of US2, FR-006)

```bash
curl -s -X POST http://localhost:8000/v1/spaces \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Too Deep", "parent_space_id": "'"$DEEP_SPACE_ID"'"}' \
  -o /dev/null -w "%{http_code}\n"
# Expected: 400, and no space is created
```

## Scenario 8: Cross-tenant parent is rejected (Constitution Principle VI, FR-011)

```bash
TOKEN="<COMPANY_USER access token, still scoped to the original company>"
curl -s -X POST http://localhost:8000/v1/spaces \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name": "Should Not Nest", "parent_space_id": "'"$OTHER_COMPANY_SPACE_ID"'"}' \
  -o /dev/null -w "%{http_code}\n"
# Expected: 400 (parent not visible to this company — same shape as set_parent's
# existing cross_company rejection), and no space is created
```

## Scenario 9: Existing admin-console create form still works unchanged

```bash
curl -s -X POST http://localhost:8000/v1/spaces \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"slug": "legal-ops", "name": "Legal Ops", "sector": "legal", "default_language": "pt-BR"}' | jq
# Expected: 201, unchanged shape — explicit slug/sector pass through verbatim
```

## Running Unit Tests

```bash
cd packages/core
.venv/bin/python -m pytest tests/test_slug.py tests/test_space_hierarchy.py -v --no-cov

cd ../../apps/api
.venv/bin/python -m pytest tests/unit/test_spaces_router.py tests/test_space_hierarchy_isolation.py -v --no-cov
```

All tests must pass, including new cases for: root creation with only `name`
supplied, sub-space creation as parent-admin, sub-space creation rejected for a
non-admin-of-parent (`PermissionError`), cross-company parent rejected, depth
limit enforced, slug auto-derived and collision-suffixed, explicit slug/sector
passthrough preserved, and both `space_created` and `member_invited` audit
records written on success.

```bash
cd apps/web && npx vitest run tests/space-add.test.tsx
```
Must include: **Add Space** button visible on both the top-level Spaces page
and a folder view, cancel leaves no trace, successful create inserts a tile
immediately without reload, creating from a folder view nests under the
current space, and a failed create shows an error message while keeping the
attempted name editable and adding no tile.
