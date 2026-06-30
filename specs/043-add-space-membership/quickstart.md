# Quickstart: Add Space Membership Validation

**Feature**: 043-add-space-membership | **Date**: 2026-06-30

This guide describes how to verify the feature end-to-end once implemented.

---

## Prerequisites

- Docker Compose stack running (`make dev` or equivalent)
- One company with at least two existing company members: `alice` (admin of
  space `Engineering`) and `bob` (company member, not yet in `Engineering`)
- API base URL: `http://localhost:8000`, web app at `http://localhost:3000`

---

## Scenario 1 — Search and add an existing company member (US1, FR-001–FR-005)

```bash
# 1. As alice, log in and open /spaces/{engineering_id}/members
# 2. Click "Add Member", type "bo" (2+ chars) into the search field
GET /v1/spaces/{engineering_id}/members/search?q=bo
Auth: alice (admin of Engineering)
# Expected: 200, members includes bob, excludes alice (already a member)

# 3. Select bob, choose role "editor", confirm
POST /v1/spaces/{engineering_id}/members
Body: { "user_id": "{bob_id}", "role": "editor" }
Auth: alice
# Expected: 201, membership returned; member list on the page updates without reload
```

## Scenario 2 — Search excludes existing members (FR-003)

```bash
# Repeat the search from Scenario 1 after bob has been added
GET /v1/spaces/{engineering_id}/members/search?q=bo
Auth: alice
# Expected: 200, members does NOT include bob (now an existing member)
```

## Scenario 3 — Search is authorized per target space (FR-002a, Tenant Isolation)

```bash
# As a user who is a member but NOT an admin of Engineering
GET /v1/spaces/{engineering_id}/members/search?q=bo
Auth: non-admin member of Engineering
# Expected: 403 Forbidden

# As alice, searching against a space_id belonging to a different company
GET /v1/spaces/{other_company_space_id}/members/search?q=bo
Auth: alice
# Expected: 404 Not Found (indistinguishable from absent)
```

## Scenario 4 — Failure messaging on add (US2, FR-006, FR-010)

```bash
# Simulate a race: another admin adds bob to Engineering between alice's search and submit
POST /v1/spaces/{engineering_id}/members
Body: { "user_id": "{bob_id}", "role": "viewer" }
Auth: alice (search/selection happened before the race)
# Expected: 400 "already a member" -> UI shows the "already a member" message,
# refreshes the member list, and retains alice's search term/role selection (FR-010)
```

## Scenario 5 — Empty results messaging (FR-008)

```bash
# In the web UI, type a fragment that matches no company member, e.g. "zzz"
GET /v1/spaces/{engineering_id}/members/search?q=zzz
Auth: alice
# Expected: 200, members: [] -> UI shows "No matches" rather than a blank list
```

---

## Frontend component check

- `apps/web/components/members/AddMemberForm.tsx` renders inside
  `SpaceMembersPanel` only when `myRole === "admin"` (mirrors the old
  `InviteMemberForm` gating).
- `InviteMemberForm.tsx` is removed; no remaining import references it.

## Automated coverage

- API: `apps/api/tests/unit/test_members_router.py` — search endpoint auth
  (admin/company-admin allowed, non-admin 403, cross-company 404), exclusion of
  existing members, empty results.
- Web: `apps/web/tests/add-member-form.test.tsx` — debounced search, minimum
  query length, empty-state message, select + submit success, each FR-006
  failure path retains form state.
