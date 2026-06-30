# Quickstart: Nested Spaces Validation

**Feature**: 041-nested-spaces | **Date**: 2026-06-30

This guide describes how to verify the nested spaces feature end-to-end once implemented.

---

## Prerequisites

- Docker Compose stack running (`make dev` or equivalent)
- At least two company accounts with spaces set up (see setup below)
- API base URL: `http://localhost:8000`

---

## Setup

1. Run migrations: `make db-migrate` (applies `0012_space_parent`)
2. Seed via the API or existing test fixtures: create company A with spaces `Engineering` and `Frontend`
3. Ensure user `alice` is an admin of `Engineering`; user `bob` is a direct member of `Frontend`

---

## Scenario 1 — Parent inherits down (FR-002, SC-001)

```bash
# 1. Set Engineering as parent of Frontend
PATCH /v1/spaces/{frontend_id}/parent
Body: { "parent_space_id": "{engineering_id}" }
Auth: alice (admin in both)

# 2. Log in as a new user charlie who is admin of Engineering but NOT in Frontend
# 3. Fetch spaces list — Frontend must appear in charlie's accessible spaces
GET /v1/spaces
# Expected: both Engineering AND Frontend appear with effective_role="admin", is_direct=false for Frontend
```

---

## Scenario 2 — Child membership does not grant parent access (FR-003, US2)

```bash
# Bob is a direct member of Frontend only
# 1. GET /v1/spaces as bob
# Expected: only Frontend appears (Engineering absent)

# 2. GET /v1/spaces/{engineering_id} as bob
# Expected: 404 Not Found (not 403 — indistinguishable from absent)
```

---

## Scenario 3 — Cycle rejection (FR-004, SC-004)

```bash
# Hierarchy: Engineering → Frontend
# Try to make Engineering a child of Frontend
PATCH /v1/spaces/{engineering_id}/parent
Body: { "parent_space_id": "{frontend_id}" }
Auth: alice (admin in both)

# Expected: 400 Bad Request
# { "error": { "code": "invalid_parent", "message": "..." } }
```

---

## Scenario 4 — Self-parent rejection (FR-005, SC-004)

```bash
PATCH /v1/spaces/{engineering_id}/parent
Body: { "parent_space_id": "{engineering_id}" }
Auth: alice

# Expected: 400 Bad Request with code "invalid_parent"
```

---

## Scenario 5 — Parent deletion promotes children (FR-008)

```bash
# Hierarchy: Engineering → Frontend
# 1. Delete Engineering space (requires company admin or equivalent)
DELETE /v1/spaces/{engineering_id}  # (existing endpoint)

# 2. Fetch Frontend space
GET /v1/spaces/{frontend_id}
# Expected: 200 OK, parent_space_id = null
```

---

## Scenario 6 — Cross-company parent rejected (FR-007)

```bash
# Acting as admin of Company A
PATCH /v1/spaces/{company_a_space_id}/parent
Body: { "parent_space_id": "{company_b_space_id}" }

# Expected: 404 Not Found (cross-company space is invisible)
```

---

## Scenario 7 — Hierarchy display with orphaned child (FR-012)

```bash
# Bob is member of Frontend (child) but NOT Engineering (parent)
GET /v1/spaces as bob
# Expected: Frontend appears in list with parent_space_id set (not null)

GET /v1/spaces/{frontend_id}/ancestors as bob
# Expected: [{ id: engineering_id, name: "Engineering", slug: "engineering" }]
# (ancestors returned for breadcrumb even though Engineering is not in bob's accessible set)
```

---

## Automated Test Commands

```bash
# Core domain unit tests
cd packages/core
uv run pytest tests/test_space_hierarchy.py -v

# API integration + isolation tests
cd apps/api
uv run pytest tests/test_space_hierarchy.py tests/test_space_hierarchy_isolation.py -v

# Full suite (must stay above coverage baseline)
cd apps/api
uv run pytest --cov=tessera_api --cov-report=term-missing
```

---

## Acceptance Checklist

- [ ] SC-001: Child space appears in parent-member's listing without any manual action after parent-child link is created
- [ ] SC-002: Child-only member is denied access to parent 100% of the time (404, not 403)
- [ ] SC-003: `GET /v1/spaces` and `GET /v1/spaces/{id}` complete within existing response-time envelope
- [ ] SC-004: Cycle and self-parent requests return 400 with `invalid_parent` code
- [ ] SC-005: After parent reassignment, old inherited access is gone and new inherited access is present atomically in the same request/response
- [ ] SC-006: Removing a parent (promote to root) does not alter direct memberships or space contents
- [ ] Isolation: Company A user cannot access Company B spaces via any inherited path
