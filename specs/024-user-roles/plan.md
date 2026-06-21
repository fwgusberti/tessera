# Implementation Plan: User Roles

**Branch**: `024-user-roles` | **Date**: 2026-06-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/024-user-roles/spec.md`

## Summary

Add direct user-space membership with three roles (Viewer, Editor, Admin) and a Global Admin platform role, replacing the current IDP-group-only access model with a per-user, per-space membership table. The implementation layers a `SpaceMembership` domain entity, a new `space_memberships` PostgreSQL table, a members REST API, a domain `MembershipService` enforcing the last-admin guard, and a members management UI panel.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript / Next.js 14 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (async), Alembic, Pydantic v2, pytest — backend; React 18, Next.js, Vitest — frontend

**Storage**: PostgreSQL — new `space_memberships` table via Alembic migration 0006

**Testing**: pytest (backend — unit + integration + contract), Vitest (frontend)

**Target Platform**: Linux server (Docker / Kubernetes)

**Project Type**: Web service (full-stack: FastAPI REST API + Next.js SPA)

**Performance Goals**: Role checks must add < 5ms overhead per API request; role changes must emit an audit record within 5 seconds (SC-004)

**Constraints**: No schema changes to existing tables except `space_memberships` addition; existing IDP group-based access (`role_permissions`) must continue working

**Scale/Scope**: Same user/space scale as existing features (~1k users, ~100 spaces at current stage)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Driven Architecture | ✅ PASS | `SpaceRole`, `SpaceMembership`, `MembershipService` in `packages/core` (no framework imports) |
| II. Separation of Concerns | ✅ PASS | Domain entities are pure Pydantic; SQLAlchemy models in `apps/api/adapters` |
| III. Data Locality & Consent | ✅ PASS | No client-side persistence of role data |
| IV. Test-Driven Development | ✅ REQUIRED | Unit tests for `MembershipService` and `access.py` written before implementation |
| V. Quality Gates | ✅ REQUIRED | All code must pass Ruff + Black before commit |
| PostgreSQL | ✅ PASS | `space_memberships` table via Alembic; no secondary store used |
| Audit Logging | ✅ PASS | Role changes emit `AuditRecord` entries (FR-008) |
| JWT Auth | ✅ PASS | Existing `require_user` / bearer middleware used for all new endpoints |
| UI Design System | ✅ PASS | `slate-*` + `indigo-600`; Geist fonts inherited from existing layout |

**Post-design re-check**: All gates still pass. `SpaceMembership` is a pure Pydantic model with no framework imports. Permission functions are pure functions in `access.py`.

## Project Structure

### Documentation (this feature)

```text
specs/024-user-roles/
├── plan.md              ← this file
├── research.md          ← Phase 0 research decisions
├── data-model.md        ← entities, schema, permission functions
├── quickstart.md        ← validation scenarios
├── contracts/
│   ├── members-api.md   ← REST API contract
│   └── frontend-routes.md ← new pages and components
└── tasks.md             ← Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
packages/core/tessera_core/
├── domain/
│   └── entities.py              # + SpaceRole enum, SpaceMembership entity
├── permissions/
│   └── access.py                # + SpaceRole-based permission functions
├── ports/
│   └── repositories.py          # + SpaceMembershipRepository (abstract)
└── services/
    └── membership.py            # NEW: MembershipService (invite, change role, remove)

apps/api/tessera_api/
├── adapters/
│   ├── models.py                # + SpaceMembershipModel (ORM)
│   └── repo.py                  # + SqlSpaceMembershipRepository
└── routers/
    ├── members.py               # NEW: member management endpoints
    └── admin.py                 # + PUT /users/{id}/platform-role

db/migrations/versions/
└── 0006_space_memberships.py    # NEW: Alembic migration

apps/web/
├── app/
│   └── spaces/
│       └── [id]/
│           └── members/
│               └── page.tsx     # NEW: members management page
└── components/
    └── members/
        ├── SpaceMembersPanel.tsx # NEW
        ├── InviteMemberForm.tsx  # NEW
        └── RoleBadge.tsx         # NEW

packages/core/tests/
└── test_membership.py           # NEW: unit tests for MembershipService + access checks

apps/api/tests/
├── integration/
│   └── test_members.py          # NEW: end-to-end member management flows
└── contract/
    └── test_members.py          # NEW: HTTP contract tests for all 6 endpoints

apps/web/tests/
└── members.test.tsx             # NEW: component tests for SpaceMembersPanel + forms
```

**Structure Decision**: Monorepo Option 2 (web + backend in separate apps). New code follows the established layout — domain in `packages/core`, HTTP adapters in `apps/api`, frontend in `apps/web`.

## Complexity Tracking

No constitution violations requiring justification.

## Design Details

### 1. Domain Entities (packages/core)

**New `SpaceRole` enum** added to `entities.py`:
```python
class SpaceRole(str, Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN  = "admin"
```

**New `SpaceMembership` entity** added to `entities.py`:
```python
class SpaceMembership(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    space_id: UUID
    user_id: UUID
    role: SpaceRole
    invited_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

`User.is_admin` remains the platform admin flag (see research.md Decision 1).

---

### 2. Permission Functions (packages/core)

New functions added to `permissions/access.py`:

```python
_SPACE_ROLE_ORDER = [SpaceRole.VIEWER, SpaceRole.EDITOR, SpaceRole.ADMIN]

def get_space_membership_role(user_id, space_id, memberships) -> SpaceRole | None:
    """Return the user's direct membership role, or None if not a member."""

def effective_space_role(user, space_id, memberships) -> SpaceRole | None:
    """Global admin is implicit ADMIN in every space."""

def can_write_document(user, space_id, memberships) -> bool:
    """True if effective role is EDITOR or ADMIN."""

def can_manage_members(user, space_id, memberships) -> bool:
    """True if effective role is ADMIN."""

def can_read_space_document(user, space_id, memberships) -> bool:
    """True if user is any member or global admin."""
```

These functions operate on `list[SpaceMembership]` (not ORM objects) — pure domain logic.

---

### 3. Repository Port (packages/core)

New abstract class `SpaceMembershipRepository` in `ports/repositories.py`:

```python
class SpaceMembershipRepository(ABC):
    @abstractmethod
    async def add(self, membership: SpaceMembership) -> SpaceMembership: ...

    @abstractmethod
    async def get(self, space_id: UUID, user_id: UUID) -> SpaceMembership | None: ...

    @abstractmethod
    async def list_by_space(self, space_id: UUID) -> list[SpaceMembership]: ...

    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[SpaceMembership]: ...

    @abstractmethod
    async def update_role(self, space_id: UUID, user_id: UUID, role: SpaceRole) -> SpaceMembership: ...

    @abstractmethod
    async def remove(self, space_id: UUID, user_id: UUID) -> None: ...

    @abstractmethod
    async def count_admins(self, space_id: UUID) -> int: ...
```

---

### 4. Domain Service (packages/core)

`services/membership.py` contains `MembershipService`:

```python
class MembershipService:
    def __init__(self, repo: SpaceMembershipRepository, audit: AuditRepository): ...

    async def invite(self, actor: User, space_id, user_id, role) -> SpaceMembership:
        # Guard: actor must be space ADMIN or global admin
        # Guard: user must not already be a member
        # Write membership, emit audit record action="member_invited"

    async def change_role(self, actor: User, space_id, user_id, new_role) -> SpaceMembership:
        # Guard: actor must be space ADMIN or global admin
        # Guard: if new_role != ADMIN, ensure count_admins > 1 (last-admin check)
        # Update role, emit audit record action="role_changed"

    async def remove(self, actor: User, space_id, user_id) -> None:
        # Guard: actor must be space ADMIN or global admin
        # Guard: if target is ADMIN, ensure count_admins > 1
        # Delete membership, emit audit record action="member_removed"
```

The `MembershipService` does NOT import FastAPI or SQLAlchemy — only domain types and port interfaces.

---

### 5. ORM Model (apps/api)

New `SpaceMembershipModel` in `adapters/models.py`:
```python
class SpaceMembershipModel(Base):
    __tablename__ = "space_memberships"
    __table_args__ = (
        UniqueConstraint("space_id", "user_id", name="uq_space_membership"),
        Index("ix_space_memberships_space", "space_id"),
        Index("ix_space_memberships_user", "user_id"),
    )
    id, space_id (FK→spaces), user_id (FK→users),
    invited_by_user_id (FK→users nullable),
    role VARCHAR(20), created_at, updated_at
```

---

### 6. SQL Repository (apps/api)

`SqlSpaceMembershipRepository` in `adapters/repo.py` implements `SpaceMembershipRepository` using `AsyncSession`.

`count_admins` uses:
```sql
SELECT COUNT(*) FROM space_memberships
WHERE space_id = :space_id AND role = 'admin'
```

---

### 7. Members Router (apps/api)

`routers/members.py` exposes:
- `POST   /spaces/{space_id}/members`
- `GET    /spaces/{space_id}/members`
- `GET    /spaces/{space_id}/members/me`
- `PUT    /spaces/{space_id}/members/{user_id}`
- `DELETE /spaces/{space_id}/members/{user_id}`

Each handler: resolves user via `require_user(request)`, instantiates `MembershipService`, calls the appropriate method, maps domain exceptions to HTTP status codes.

**Error mapping**:
- `PermissionError` → 403
- `ValueError("not a member")` → 404
- `ValueError("last admin")` → 409

---

### 8. Admin Router Extension (apps/api)

Add `PUT /users/{user_id}/platform-role` to `routers/admin.py`:
- Requires `user_info["is_admin"] == True`
- Updates `users.is_admin` via `UserRepository`
- Emits audit record `action="platform_role_changed"`

---

### 9. Database Migration (db/migrations)

`0006_space_memberships.py`:
```python
def upgrade():
    op.create_table("space_memberships", ...)
    op.create_index("ix_space_memberships_space", ...)
    op.create_index("ix_space_memberships_user", ...)
    op.create_unique_constraint("uq_space_membership", ...)
```

---

### 10. Frontend (apps/web)

**New page**: `app/spaces/[id]/members/page.tsx`
- Calls `GET /spaces/{id}/members/me` to determine viewer role
- Renders `SpaceMembersPanel` (list + admin controls if ADMIN)

**New components** in `components/members/`:
- `SpaceMembersPanel.tsx` — member list with role badges; conditionally shows admin controls
- `InviteMemberForm.tsx` — user_id input + role selector dropdown; calls POST members
- `RoleBadge.tsx` — `slate`/`indigo` color badges per role

**Styling** (slate + indigo palette per constitution):
- ADMIN badge: `bg-indigo-100 text-indigo-700`
- EDITOR badge: `bg-slate-100 text-slate-700`
- VIEWER badge: `bg-slate-50 text-slate-500`
- Action buttons: `bg-indigo-600 hover:bg-indigo-700`

---

### 11. Document Write Protection Update

The existing `routers/documents.py` create/edit/delete handlers currently check `is_admin` or group-based role. After this feature, they must also check `SpaceMembership.role` (EDITOR or ADMIN). Update the document permission check to call `can_write_document(user, space_id, memberships)` where `memberships` is fetched from `SpaceMembershipRepository`.

This makes US2 (editors can write, viewers cannot) enforceable.

---

## Edge Case Handling

| Edge Case | Handling |
|-----------|----------|
| Last admin demoted/removed | `MembershipService.change_role / remove` checks `count_admins > 1`; raises ValueError → 409 |
| User removed while editing | Next save attempt hits `can_write_document` check → 403 with clear error |
| Global admin + space Viewer | `effective_space_role` returns ADMIN (global overrides) |
| User viewing their own role | `GET /spaces/{id}/members/me` returns their membership or 404 |
| Account deactivated | `User.is_admin=False`; all `can_*` checks resolve memberships which still exist but the user can't auth (JWT refresh revoked) — FR-011 partial; full revocation deferred to account deactivation feature |

## Dependencies on Other Features

- JWT auth / `require_user` — already implemented (feature 023)
- `AuditRepository` / `AuditRecord` — already implemented
- `SpaceRepository.get_by_id` — already implemented
- `UserRepository.get_by_id` — already implemented
