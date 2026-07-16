# Quickstart: Validating Human-Readable Member Identity

**Feature**: `065-fix-member-display` | **Date**: 2026-07-12

Validation guide for the enriched space-members list. Contracts:
[contracts/space-members-api.md](./contracts/space-members-api.md); data
shape: [data-model.md](./data-model.md).

## Prerequisites

- Repo dependencies installed (`uv sync` for Python workspaces, `npm install`
  in `apps/web`).
- For end-to-end checks: local stack running with
  `FRONTEND_URL=http://192.168.0.8:3000` (CORS allows only this origin — not
  `localhost`).

## 1. Automated tests (primary validation)

```bash
# Core: value-object projection
cd packages/core && uv run pytest tests/test_space_member_listing.py -v

# API: enriched list, ordering, tenant isolation
cd apps/api && uv run pytest tests/integration/test_members.py tests/contract/test_members.py -v

# Web: label fallback chain, no-UUID rendering, actions still work
cd apps/web && npx vitest run tests/members.test.tsx
```

**Expected**: all pass. Known pre-existing failures elsewhere (test_ports,
migration_0002, tessera_mcp suites) are out of scope — assert zero *new*
failures only. Quality gates: `uv run ruff check . && uv run black --check .`
on touched Python packages.

## 2. API-level validation (curl)

With a seeded space (register → company → space → add member) and an access
token for a space member:

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/spaces/$SPACE_ID/members | jq '.members[]'
```

**Expected**: every element has non-null `display_name` and `email` alongside
the previous fields; array ordered by `display_name`.

Cross-tenant probe (token from a *different* company):

```bash
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $OTHER_TOKEN" \
  http://localhost:8000/v1/spaces/$SPACE_ID/members
```

**Expected**: `404`, generic body, no identity data.

## 3. Browser validation (acceptance scenarios)

1. Sign in as a space admin at `http://192.168.0.8:3000`, open a space →
   members panel.
   **Expected**: each row shows the person's name with their email in muted
   text beneath — no UUID anywhere in the table (US1 / SC-001).
2. Change a member's role via the row dropdown; remove a member via the row's
   Remove action.
   **Expected**: both succeed against the intended person, and the row
   remains identified by name+email throughout (US2 / FR-005, SC-003).
3. For a member with a blank display name, the row's primary label is their
   email (FR-003).
4. Visit the company Users page and the add-member search in the same
   session.
   **Expected**: identical identity presentation — name primary, email
   secondary; never an identifier (US3 / SC-004).
5. Sign in as a non-admin space member and open the same panel.
   **Expected**: same readable list, read-only (edge case).
