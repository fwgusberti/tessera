# Quickstart: Fix Empty Spaces List Validation

**Feature**: 042-fix-empty-spaces-list | **Date**: 2026-06-30

This guide describes how to verify the fix end-to-end once implemented.

---

## Prerequisites

- Docker Compose stack running (`make dev` or equivalent), migrations applied
  through `0013`
- A company with at least one pre-existing space that currently shows zero
  members (the bug state) — e.g. the reporting user's `Gusba.dev` company
  with spaces `a`, `b`, `D`

---

## Scenario 1 — Backfill restores existing orphaned spaces (US2, FR-002, FR-003, SC-001)

```bash
# Before migration 0013: confirm the bug state
SELECT s.id, s.name, count(sm.id)
FROM spaces s LEFT JOIN space_memberships sm ON sm.space_id = s.id
WHERE s.company_id = '<gusba.dev company id>'
GROUP BY s.id, s.name;
# Expected (bug state): count = 0 for spaces a, b, D

# Run migrations
alembic upgrade head   # (or make db-migrate)

# After: every space now has at least one admin membership
SELECT s.name, sm.role, u.email
FROM spaces s
JOIN space_memberships sm ON sm.space_id = s.id
JOIN users u ON u.id = sm.user_id
WHERE s.company_id = '<gusba.dev company id>';
# Expected: a/b/D each have a row with role='admin', user = the company's admin(s)

# As felipe@gusba.dev:
GET /v1/spaces
# Expected: a, b, D all present with effective_role: "admin"
```

## Scenario 2 — Backfill is idempotent and doesn't touch legitimate memberships (FR-003, SC-004)

```bash
# Re-run the same migration (or re-execute BACKFILL_SQL directly)
# Expected: no new rows inserted, no errors

# For a space that already had a real (non-backfilled) member before the fix,
# e.g. a viewer added via the existing invite flow:
SELECT role FROM space_memberships WHERE space_id = '<space with pre-existing member>' AND user_id = '<that viewer>';
# Expected: still 'viewer' — untouched, not overwritten or duplicated
```

## Scenario 3 — Newly created spaces are immediately visible (US1, FR-001, SC-002)

```bash
POST /v1/spaces
Body: { "slug": "new-space", "name": "New Space", "sector": "tech" }
Auth: any company member

GET /v1/spaces
Auth: same user
# Expected: "new-space" appears immediately, effective_role: "admin", is_direct: true

GET /v1/spaces/{new_space_id}/members
# Expected: the creator listed with role: "admin"
```

## Scenario 4 — Consistency across surfaces (US3, FR-004, SC-003)

```bash
# As felipe@gusba.dev, after Scenario 1's backfill:
GET /v1/spaces                      # Spaces page data source
# In the web UI: visit /spaces                    -> a, b, D appear
# In the web UI: visit /documents (space filter)   -> a, b, D appear as filter options
# Both MUST show the same three spaces — no surface lags behind another
```

---

## Automated coverage

- `apps/api/tests/test_migration_0013_backfill_space_memberships.py` — real-DB,
  rolled-back-transaction test (mirrors `test_migration_0010_backfill.py`):
  orphaned space gets backfilled, multi-admin company gets every admin
  backfilled, space with an existing member is untouched, idempotent re-run,
  cross-company isolation (company A's admin never lands on company B's space).
- `apps/api/tests/unit/test_spaces_router.py` — `create_space` grants the
  caller an admin `SpaceMembership` in the same call.
