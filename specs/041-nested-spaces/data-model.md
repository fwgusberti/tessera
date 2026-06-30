# Data Model: Nested Spaces

**Feature**: 041-nested-spaces | **Date**: 2026-06-30

---

## Entity Changes

### Space (modified)

Gains one optional self-referential FK field.

| Field | Type | Change |
|---|---|---|
| `id` | `UUID` | unchanged |
| `slug` | `str` | unchanged |
| `name` | `str` | unchanged |
| `sector` | `str` | unchanged |
| `company_id` | `UUID` | unchanged |
| `parent_space_id` | `UUID \| None` | **NEW** — FK → `spaces.id`, `ON DELETE SET NULL`, nullable, indexed |
| `taxonomy` | `dict` | unchanged |
| `retention_policy` | `dict` | unchanged |
| `confidence_threshold` | `float` | unchanged |
| `default_language` | `str` | unchanged |
| `created_at` | `datetime` | unchanged |
| `updated_at` | `datetime` | unchanged |

**Validation rules**:
- `parent_space_id` must reference a space with the same `company_id` (enforced by service, not DB FK alone)
- `parent_space_id != id` (no self-parent)
- Depth of `parent_space_id`'s ancestor chain + 1 ≤ 10
- Setting `parent_space_id` must not create a cycle

**State transitions**:
- `parent_space_id = None` → root space
- `parent_space_id = <uuid>` → child space
- `parent_space_id` is mutable: a space can be moved between parents or promoted to root

---

### SpaceMembership (unchanged)

Direct membership records are unchanged. Effective (inherited) membership is computed, not stored.

---

### SpaceAccess (new domain value object — not persisted)

Computed per request; not stored in DB.

```python
class SpaceAccess:
    space: Space
    effective_role: SpaceRole  # best role from direct or inherited membership
    is_direct: bool            # True if user has a direct SpaceMembership row
```

This is returned by `SpaceRepository.list_accessible_by_user(user_id, company_id)`.

---

## Database Migration

**File**: `db/migrations/versions/0012_space_parent.py`

```sql
-- upgrade
ALTER TABLE spaces
  ADD COLUMN parent_space_id UUID REFERENCES spaces(id) ON DELETE SET NULL;

CREATE INDEX ix_spaces_parent_space_id ON spaces (parent_space_id);
```

```sql
-- downgrade
DROP INDEX ix_spaces_parent_space_id;
ALTER TABLE spaces DROP COLUMN parent_space_id;
```

---

## Repository Port Additions

New abstract methods on `SpaceRepository`:

```python
@abstractmethod
async def get_ancestor_chain(self, space_id: UUID) -> list[Space]:
    """Ordered list from immediate parent to root (empty if root space)."""
    ...

@abstractmethod
async def set_parent(self, space_id: UUID, parent_space_id: UUID) -> Space:
    """Set parent_space_id on space_id; returns updated Space."""
    ...

@abstractmethod
async def remove_parent(self, space_id: UUID) -> Space:
    """Set parent_space_id = NULL; returns updated Space."""
    ...

@abstractmethod
async def list_accessible_by_user(
    self, user_id: UUID, company_id: UUID
) -> list[SpaceAccess]:
    """
    Returns all spaces the user can access (direct + inherited),
    with effective_role = most-permissive role from any membership path.
    Scoped strictly to company_id.
    """
    ...
```

---

## Domain Service: SpaceHierarchyService

New service in `packages/core/tessera_core/services/space_hierarchy.py`.

### Responsibilities

| Method | Validation | Mutation |
|---|---|---|
| `set_parent(actor, child_id, parent_id, company_id)` | actor is admin in child AND parent; same company; no cycle; depth ≤ 10; no self-parent | calls `repo.set_parent` |
| `remove_parent(actor, child_id, company_id)` | actor is admin in child | calls `repo.remove_parent` |
| `get_ancestor_path(space_id, company_id)` | space must exist in company | calls `repo.get_ancestor_chain` |

The service depends on `SpaceRepository` and `SpaceMembershipRepository` (injected). It emits `AuditRecord` on every successful mutation.

### Error types

| Situation | Exception |
|---|---|
| Actor lacks admin role in child or parent | `PermissionError` |
| Self-parent | `ValueError("self_parent")` |
| Cycle detected | `ValueError("cycle")` |
| Depth limit exceeded | `ValueError("depth_limit")` |
| Cross-company parent | `ValueError("cross_company")` |
| Space not found | `ValueError("not_found")` |

---

## SQLAlchemy Model Change

`SpaceModel` in `apps/api/tessera_api/adapters/models/space.py`:

```python
parent_space_id: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("spaces.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)

children: Mapped[list["SpaceModel"]] = relationship(
    "SpaceModel",
    foreign_keys=[parent_space_id],
    back_populates="parent",
)
parent: Mapped["SpaceModel | None"] = relationship(
    "SpaceModel",
    foreign_keys=[parent_space_id],
    back_populates="children",
    remote_side=[id],
)
```

---

## Frontend Type Changes

`apps/web/lib/types.ts` — `Space` interface:

```typescript
export interface Space {
  id: string;
  slug: string;
  name: string;
  sector: string;
  parent_space_id: string | null;  // NEW
  default_language: string;
  confidence_threshold: number;
  retention_policy: Record<string, unknown>;
}

export interface SpaceAccess {            // NEW
  space: Space;
  effective_role: SpaceRole;
  is_direct: boolean;
}
```
