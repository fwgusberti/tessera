# Quickstart Validation Guide: User Roles (024)

## Prerequisites

- Tessera API running locally (`make dev` from repo root, or `uvicorn tessera_api.main:app --reload` from `apps/api`)
- PostgreSQL running and migrated through **0006_space_memberships** (`alembic upgrade head` from `apps/api`)
- At minimum 3 test accounts created (Admin, Editor, Viewer) and a test space created
- `httpie` or `curl` for API calls, or use the web UI at `http://localhost:3000`

---

## Scenario 1 — US1: Space Admin Invites a User

**Setup**: Log in as `admin_user` (a user with space ADMIN membership in `test-space`). Get a JWT.

```bash
# Invite editor_user to the space as Editor
http POST localhost:8000/spaces/{SPACE_ID}/members \
  Authorization:"Bearer {ADMIN_JWT}" \
  user_id={EDITOR_USER_ID} role=editor

# Expected: 201 Created with membership object
# membership.role == "editor"
```

**Then list members** to confirm:
```bash
http GET localhost:8000/spaces/{SPACE_ID}/members \
  Authorization:"Bearer {ADMIN_JWT}"

# Expected: member list includes editor_user with role "editor"
```

**Verify US1 AC4 (non-admin cannot change roles)**:
```bash
http PUT localhost:8000/spaces/{SPACE_ID}/members/{VIEWER_USER_ID} \
  Authorization:"Bearer {EDITOR_JWT}" \
  role=admin

# Expected: 403 Forbidden
```

---

## Scenario 2 — US2: Editor Writes, Viewer Cannot

**Setup**: `editor_user` has EDITOR role, `viewer_user` has VIEWER role in `test-space`.

**Editor creates a document**:
```bash
http POST localhost:8000/documents \
  Authorization:"Bearer {EDITOR_JWT}" \
  space_id={SPACE_ID} title="Editor Doc" content_markdown="# Hello"

# Expected: 201 Created
```

**Viewer attempts to create a document**:
```bash
http POST localhost:8000/documents \
  Authorization:"Bearer {VIEWER_JWT}" \
  space_id={SPACE_ID} title="Should Fail" content_markdown="# No"

# Expected: 403 Forbidden with explanation
```

**Viewer reads a published document**:
```bash
http GET localhost:8000/documents/{DOC_ID} \
  Authorization:"Bearer {VIEWER_JWT}"

# Expected: 200 OK — viewer can read
```

---

## Scenario 3 — US3: Global Admin Acts Across Spaces

**Setup**: `global_admin` user has `is_admin=True`. Not explicitly a member of `other-space`.

**Global admin accesses a space's member list without invitation**:
```bash
http GET localhost:8000/spaces/{OTHER_SPACE_ID}/members \
  Authorization:"Bearer {GLOBAL_ADMIN_JWT}"

# Expected: 200 OK — returns member list even though not a member
```

**Global admin promotes a regular user**:
```bash
http PUT localhost:8000/users/{TARGET_USER_ID}/platform-role \
  Authorization:"Bearer {GLOBAL_ADMIN_JWT}" \
  is_admin=true

# Expected: 200 OK — target user now has is_admin=true
```

**Regular user attempts to access global admin controls**:
```bash
http PUT localhost:8000/users/{USER_ID}/platform-role \
  Authorization:"Bearer {REGULAR_JWT}" \
  is_admin=true

# Expected: 403 Forbidden
```

---

## Scenario 4 — Last-Admin Guard

**Setup**: `test-space` has exactly one ADMIN member (`admin_user`).

**Attempt to demote the last admin**:
```bash
http PUT localhost:8000/spaces/{SPACE_ID}/members/{ADMIN_USER_ID} \
  Authorization:"Bearer {ADMIN_JWT}" \
  role=editor

# Expected: 409 Conflict — "Cannot remove the last admin of a space"
```

**Attempt to remove the last admin**:
```bash
http DELETE localhost:8000/spaces/{SPACE_ID}/members/{ADMIN_USER_ID} \
  Authorization:"Bearer {ADMIN_JWT}"

# Expected: 409 Conflict
```

---

## Audit Log Verification

After any role change, confirm the audit record was written:
```bash
# Query audit_records for the affected membership
psql $DATABASE_URL -c "
  SELECT action, actor_id, entity_type, metadata
  FROM audit_records
  WHERE entity_type = 'space_membership'
  ORDER BY occurred_at DESC
  LIMIT 5;
"

# Expected: rows with action in {member_invited, role_changed, member_removed}
# metadata contains space_id, user_id, and role info
```

---

## Role Visibility (SC-006)

**From the web UI at `http://localhost:3000`**:
1. Log in as any space member.
2. Navigate to a space (step 1 from space home).
3. Click "Members" in the space nav (step 2).
4. Confirm your own role badge is visible.

Total navigation steps: ≤ 2 ✓

---

## Test Suite

```bash
# Domain unit tests (packages/core)
cd packages/core && python -m pytest tests/ -v

# Integration tests (apps/api) — requires live DB
cd apps/api && python -m pytest tests/integration/test_members.py -v

# Contract tests
cd apps/api && python -m pytest tests/contract/test_members.py -v

# Frontend component tests
cd apps/web && npm test -- members
```

See `data-model.md` for schema details and `contracts/members-api.md` for full endpoint specs.
