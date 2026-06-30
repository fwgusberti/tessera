# Research: Nested Spaces

**Feature**: 041-nested-spaces | **Date**: 2026-06-30

---

## 1. Ancestor/Descendant Traversal Strategy

**Decision**: PostgreSQL `WITH RECURSIVE` CTE

**Rationale**: The `spaces` table already lives in PostgreSQL. A recursive CTE is native, zero-dependency, and executes the full traversal in one round-trip. At depth ≤ 10 the planner bounds the recursion constant; no additional indexing beyond `spaces.parent_space_id` (indexed) is needed. Python-side BFS/DFS alternatives would require multiple round-trips (O(depth)).

**Alternatives considered**:
- **Nested Sets / Materialized Path**: adds write complexity and additional columns; overkill for bounded depth 10.
- **Closure Table**: a separate `space_ancestors` table that records all ancestor pairs. Eliminates recursive queries but doubles write cost and adds a second table to keep consistent. Deferred to future if depth > 10 or query performance degrades.
- **Python BFS on cached graph**: requires loading the full company graph into memory on every request — not suitable for per-request access checks in a shared API process.

---

## 2. Effective Membership Computation

**Decision**: Single-query recursive CTE from direct memberships → descendants

**Query shape**:
```sql
WITH RECURSIVE accessible AS (
  -- base: spaces the user has a direct membership in
  SELECT s.id, s.parent_space_id, sm.role::text AS effective_role, TRUE AS is_direct
  FROM spaces s
  JOIN space_memberships sm ON sm.space_id = s.id AND sm.user_id = :user_id
  WHERE s.company_id = :company_id

  UNION ALL

  -- recursive: children of already-accessible spaces (role propagates down)
  SELECT s.id, s.parent_space_id, a.effective_role, FALSE AS is_direct
  FROM spaces s
  JOIN accessible a ON s.parent_space_id = a.id
  WHERE s.company_id = :company_id
)
-- If user has both direct and inherited membership, pick most-permissive role
SELECT id, MAX(effective_role) FILTER (... ordering) AS effective_role, bool_or(is_direct) AS is_direct
FROM accessible
GROUP BY id
```

Role ordering for MAX (most permissive first): admin > editor > viewer.
Implemented as `CASE` inside `MAX(CASE role WHEN 'admin' THEN 3 WHEN 'editor' THEN 2 ELSE 1 END)`.

**Rationale**: One DB round-trip per listing request. The domain layer sees a flat list of `SpaceAccess(space, effective_role, is_direct)` objects; hierarchy reconstruction for the UI happens in Python and TypeScript from the `parent_space_id` field.

---

## 3. Cycle Detection Strategy

**Decision**: Check that the proposed parent's ancestor chain does not contain the child space

**Algorithm** (runs before setting parent):
1. Fetch the ancestor chain of `proposed_parent_id` (recursive CTE walking `parent_space_id` upward).
2. If `child_space_id` appears anywhere in that chain → circular reference → reject.
3. Check depth: if `len(ancestor_chain_of_proposed_parent) + 1 >= 10` → depth limit exceeded → reject.

**Rationale**: By checking the parent's ancestry (not doing a two-pass DFS on the whole tree), we handle all cases (self-parent is a degenerate cycle; A→B→A is caught because B's ancestor chain includes A when we attempt to set A's parent to B).

**Self-parent shortcut**: `child_space_id == proposed_parent_id` is checked before the DB query (FR-005).

---

## 4. Parent Assignment Permission Check

**Decision**: Require `SpaceRole.ADMIN` in both child and parent spaces; removing parent requires only admin in child

**Implementation**: The `SpaceHierarchyService.set_parent` method:
1. Verifies actor has `SpaceRole.ADMIN` in child space (via `SpaceMembershipRepository.get`).
2. Verifies actor has `SpaceRole.ADMIN` in parent space (same repo method).
3. Both checked in the domain service before any structural mutation.

Removing parent (promote to root): only admin check on child space.

**Rationale**: Spec clarification from 2026-06-30 session: "Admin in both — must hold admin role in the child space AND the intended parent space."

---

## 5. Parent Deletion Cascade Behavior

**Decision**: `ON DELETE SET NULL` on `spaces.parent_space_id` FK

**Rationale**: FR-008 — when a parent space is deleted, child spaces become root-level (not cascade-deleted). `SET NULL` on the FK implements this automatically at the DB level without any application-layer trigger. The existing `ON DELETE CASCADE` on `company_id` FK continues to handle company deletion (all spaces deleted together).

---

## 6. Cross-Company Parent Assignment Prevention

**Decision**: Service-layer validation using `get_by_id_for_company` — FK alone is insufficient

**Rationale**: The `parent_space_id` FK references `spaces.id` globally (no composite FK with `company_id`). DB-level cross-company prevention via composite FK would require a composite unique key on `(id, company_id)` and a composite FK — unnecessarily complex. Instead, the service calls `repo.get_by_id_for_company(proposed_parent_id, company_id)` and if it returns None, rejects the assignment. This is consistent with the existing pattern (feature 037).

---

## 7. Space Listing: User-Level Filtering

**Decision**: `GET /v1/spaces` becomes user-aware — returns only spaces the authenticated user can access (direct + inherited)

**Rationale**: Spec US2 AC3: "When the user views their space list, Then only 'Frontend' appears — not 'Engineering' or other spaces they were not added to." This is a behavior change from the current "all company spaces" listing. Company admins who hold admin role on every space continue to see all spaces (their memberships cover the full set). Users without any membership see an empty list.

**Note**: This is a breaking behavior change. Current code returns all company spaces; after this feature, only accessible spaces are returned per user. This will affect tests in `test_space_visibility.py` that mock `list_by_company` — those tests will need to be updated or separated from the new user-filtered path.

---

## 8. Frontend Hierarchy Rendering

**Decision**: Build tree from flat list client-side; orphaned child spaces render at root level with breadcrumb

**Algorithm**:
1. Receive flat `SpaceAccess[]` from API (each item has `parent_space_id`).
2. Build an id→SpaceAccess map.
3. Items whose `parent_space_id` is null OR whose parent is not in the user's accessible set → root level.
4. Items whose parent IS in the accessible set → nested under parent.
5. For items at root level that have a `parent_space_id` → fetch ancestor names separately for breadcrumb display (FR-012). A dedicated `GET /v1/spaces/{id}/ancestors` endpoint returns the ancestor name path without granting access.

**Rationale**: Tree construction is O(n) client-side and avoids a server-side tree serialization format. The `parent_space_id` field on each space is sufficient to reconstruct the tree.
