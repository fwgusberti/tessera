"""Unit tests for SpaceHierarchyService — inheritance, isolation, and mutation guards.

TDD: all tests in this file were written before implementation.
Run: cd packages/core && uv run pytest tests/test_space_hierarchy.py -v
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from tessera_core.domain.space import Space
from tessera_core.domain.space_access import SpaceAccess
from tessera_core.domain.space_membership import SpaceMembership
from tessera_core.domain.space_role import SpaceRole
from tessera_core.services.space_hierarchy import SpaceHierarchyService


def _space(company_id: uuid.UUID, parent_id: uuid.UUID | None = None) -> Space:
    return Space(
        id=uuid.uuid4(),
        slug=f"sp-{uuid.uuid4().hex[:6]}",
        name="A Space",
        sector="tech",
        company_id=company_id,
        parent_space_id=parent_id,
    )


def _membership(space_id: uuid.UUID, user_id: uuid.UUID, role: SpaceRole) -> SpaceMembership:
    return SpaceMembership(space_id=space_id, user_id=user_id, role=role)


def _access(space: Space, role: SpaceRole, is_direct: bool) -> SpaceAccess:
    return SpaceAccess(space=space, effective_role=role, is_direct=is_direct)


# ---------------------------------------------------------------------------
# US1 — Downward access inheritance (T006)
# ---------------------------------------------------------------------------


class TestDownwardInheritance:
    """A user with direct membership in an ancestor gains access to all descendants."""

    @pytest.mark.asyncio
    async def test_direct_membership_grants_access_to_child(self):
        """Single-level: admin of parent can access child (inherited, not direct)."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        parent = _space(company_id)
        child = _space(company_id, parent_id=parent.id)

        accessible = [
            _access(parent, SpaceRole.ADMIN, is_direct=True),
            _access(child, SpaceRole.ADMIN, is_direct=False),
        ]

        space_repo = AsyncMock()
        space_repo.list_accessible_by_user = AsyncMock(return_value=accessible)
        membership_repo = AsyncMock()

        svc = SpaceHierarchyService(space_repo, membership_repo)
        result = await svc.list_accessible(user_id, company_id)

        assert len(result) == 2
        child_access = next(a for a in result if a.space.id == child.id)
        assert child_access.effective_role == SpaceRole.ADMIN
        assert child_access.is_direct is False

    @pytest.mark.asyncio
    async def test_multi_level_chain_inheritance(self):
        """Multi-level: grandparent membership propagates to grandchild."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        grandparent = _space(company_id)
        parent = _space(company_id, parent_id=grandparent.id)
        child = _space(company_id, parent_id=parent.id)

        accessible = [
            _access(grandparent, SpaceRole.EDITOR, is_direct=True),
            _access(parent, SpaceRole.EDITOR, is_direct=False),
            _access(child, SpaceRole.EDITOR, is_direct=False),
        ]

        space_repo = AsyncMock()
        space_repo.list_accessible_by_user = AsyncMock(return_value=accessible)
        membership_repo = AsyncMock()

        svc = SpaceHierarchyService(space_repo, membership_repo)
        result = await svc.list_accessible(user_id, company_id)

        assert len(result) == 3
        for access in result:
            assert access.effective_role == SpaceRole.EDITOR

    @pytest.mark.asyncio
    async def test_no_membership_returns_empty(self):
        """User with no memberships receives an empty list."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()

        space_repo = AsyncMock()
        space_repo.list_accessible_by_user = AsyncMock(return_value=[])
        membership_repo = AsyncMock()

        svc = SpaceHierarchyService(space_repo, membership_repo)
        result = await svc.list_accessible(user_id, company_id)

        assert result == []


# ---------------------------------------------------------------------------
# US2 — Upward isolation (T012)
# ---------------------------------------------------------------------------


class TestUpwardIsolation:
    """Child-space membership MUST NOT propagate upward."""

    @pytest.mark.asyncio
    async def test_child_member_cannot_see_parent(self):
        """User with child membership gets only the child, not the parent."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        parent = _space(company_id)
        child = _space(company_id, parent_id=parent.id)

        # Only child is accessible — upward propagation would be wrong
        accessible = [
            _access(child, SpaceRole.VIEWER, is_direct=True),
        ]

        space_repo = AsyncMock()
        space_repo.list_accessible_by_user = AsyncMock(return_value=accessible)
        membership_repo = AsyncMock()

        svc = SpaceHierarchyService(space_repo, membership_repo)
        result = await svc.list_accessible(user_id, company_id)

        ids = {a.space.id for a in result}
        assert parent.id not in ids
        assert child.id in ids

    @pytest.mark.asyncio
    async def test_sibling_access_is_denied(self):
        """Child membership does not grant access to sibling spaces."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        parent = _space(company_id)
        child_a = _space(company_id, parent_id=parent.id)
        child_b = _space(company_id, parent_id=parent.id)

        accessible = [
            _access(child_a, SpaceRole.EDITOR, is_direct=True),
        ]

        space_repo = AsyncMock()
        space_repo.list_accessible_by_user = AsyncMock(return_value=accessible)
        membership_repo = AsyncMock()

        svc = SpaceHierarchyService(space_repo, membership_repo)
        result = await svc.list_accessible(user_id, company_id)

        ids = {a.space.id for a in result}
        assert child_b.id not in ids
        assert parent.id not in ids

    @pytest.mark.asyncio
    async def test_space_list_contains_only_accessible_spaces(self):
        """list_accessible returns exactly the set from the repository."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        space = _space(company_id)

        accessible = [_access(space, SpaceRole.VIEWER, is_direct=True)]

        space_repo = AsyncMock()
        space_repo.list_accessible_by_user = AsyncMock(return_value=accessible)
        membership_repo = AsyncMock()

        svc = SpaceHierarchyService(space_repo, membership_repo)
        result = await svc.list_accessible(user_id, company_id)

        assert len(result) == 1
        assert result[0].space.id == space.id


# ---------------------------------------------------------------------------
# US3 — set_parent validations (T016)
# ---------------------------------------------------------------------------


class TestSetParentValidations:
    @pytest.mark.asyncio
    async def test_self_parent_raises_value_error(self):
        """Cannot set a space as its own parent."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        space = _space(company_id)

        space_repo = AsyncMock()
        membership_repo = AsyncMock()
        membership_repo.get = AsyncMock(
            return_value=_membership(space.id, user_id, SpaceRole.ADMIN)
        )
        space_repo.get_by_id_for_company = AsyncMock(return_value=space)

        svc = SpaceHierarchyService(space_repo, membership_repo)
        with pytest.raises(ValueError, match="self_parent"):
            await svc.set_parent(
                actor_id=user_id,
                child_id=space.id,
                parent_id=space.id,
                company_id=company_id,
            )

    @pytest.mark.asyncio
    async def test_cycle_detection_raises_value_error(self):
        """Cycle: A→B and attempting B→A is rejected."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        space_a = _space(company_id)
        space_b = _space(company_id, parent_id=space_a.id)

        space_repo = AsyncMock()
        membership_repo = AsyncMock()

        # Actor is admin in both
        membership_repo.get = AsyncMock(
            side_effect=lambda sid, uid: _membership(sid, uid, SpaceRole.ADMIN)
        )
        # Both spaces exist in company
        space_repo.get_by_id_for_company = AsyncMock(
            side_effect=lambda sid, cid: space_a if sid == space_a.id else space_b
        )
        # Ancestor chain of proposed parent (space_b) includes space_a
        space_repo.get_ancestor_chain = AsyncMock(return_value=[space_a])

        svc = SpaceHierarchyService(space_repo, membership_repo)
        with pytest.raises(ValueError, match="cycle"):
            await svc.set_parent(
                actor_id=user_id,
                child_id=space_a.id,
                parent_id=space_b.id,
                company_id=company_id,
            )

    @pytest.mark.asyncio
    async def test_depth_limit_raises_value_error(self):
        """Exceeding depth 10 is rejected."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        child = _space(company_id)
        proposed_parent = _space(company_id)

        space_repo = AsyncMock()
        membership_repo = AsyncMock()
        membership_repo.get = AsyncMock(
            side_effect=lambda sid, uid: _membership(sid, uid, SpaceRole.ADMIN)
        )
        space_repo.get_by_id_for_company = AsyncMock(
            side_effect=lambda sid, cid: (child if sid == child.id else proposed_parent)
        )
        # Ancestor chain of proposed parent has 10 entries → depth would be 11
        space_repo.get_ancestor_chain = AsyncMock(
            return_value=[_space(company_id) for _ in range(10)]
        )

        svc = SpaceHierarchyService(space_repo, membership_repo)
        with pytest.raises(ValueError, match="depth_limit"):
            await svc.set_parent(
                actor_id=user_id,
                child_id=child.id,
                parent_id=proposed_parent.id,
                company_id=company_id,
            )

    @pytest.mark.asyncio
    async def test_cross_company_parent_raises_value_error(self):
        """Parent from a different company (invisible) raises cross_company."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        child = _space(company_id)
        cross_company_parent_id = uuid.uuid4()

        space_repo = AsyncMock()
        membership_repo = AsyncMock()
        membership_repo.get = AsyncMock(
            return_value=_membership(child.id, user_id, SpaceRole.ADMIN)
        )
        # get_by_id_for_company returns child but None for the cross-company parent
        space_repo.get_by_id_for_company = AsyncMock(
            side_effect=lambda sid, cid: child if sid == child.id else None
        )

        svc = SpaceHierarchyService(space_repo, membership_repo)
        with pytest.raises(ValueError, match="cross_company"):
            await svc.set_parent(
                actor_id=user_id,
                child_id=child.id,
                parent_id=cross_company_parent_id,
                company_id=company_id,
            )

    @pytest.mark.asyncio
    async def test_missing_admin_on_child_raises_permission_error(self):
        """Actor without admin role in child is denied."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        child = _space(company_id)
        parent = _space(company_id)

        space_repo = AsyncMock()
        membership_repo = AsyncMock()
        # Actor is only a viewer in child
        membership_repo.get = AsyncMock(
            side_effect=lambda sid, uid: _membership(sid, uid, SpaceRole.VIEWER)
        )
        space_repo.get_by_id_for_company = AsyncMock(
            side_effect=lambda sid, cid: child if sid == child.id else parent
        )

        svc = SpaceHierarchyService(space_repo, membership_repo)
        with pytest.raises(PermissionError):
            await svc.set_parent(
                actor_id=user_id,
                child_id=child.id,
                parent_id=parent.id,
                company_id=company_id,
            )

    @pytest.mark.asyncio
    async def test_missing_admin_on_parent_raises_permission_error(self):
        """Actor must be admin in both child and parent."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        child = _space(company_id)
        parent = _space(company_id)

        space_repo = AsyncMock()
        membership_repo = AsyncMock()
        # Admin in child, viewer in parent
        membership_repo.get = AsyncMock(
            side_effect=lambda sid, uid: _membership(
                sid, uid, SpaceRole.ADMIN if sid == child.id else SpaceRole.VIEWER
            )
        )
        space_repo.get_by_id_for_company = AsyncMock(
            side_effect=lambda sid, cid: child if sid == child.id else parent
        )
        space_repo.get_ancestor_chain = AsyncMock(return_value=[])

        svc = SpaceHierarchyService(space_repo, membership_repo)
        with pytest.raises(PermissionError):
            await svc.set_parent(
                actor_id=user_id,
                child_id=child.id,
                parent_id=parent.id,
                company_id=company_id,
            )


class TestRenameValidations:
    @pytest.mark.asyncio
    async def test_missing_space_raises_value_error(self):
        """A space that doesn't resolve in the company is not_found."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        space_id = uuid.uuid4()

        space_repo = AsyncMock()
        membership_repo = AsyncMock()
        space_repo.get_by_id_for_company = AsyncMock(return_value=None)

        svc = SpaceHierarchyService(space_repo, membership_repo)
        with pytest.raises(ValueError, match="not_found"):
            await svc.rename(
                actor_id=user_id,
                space_id=space_id,
                name="New Name",
                company_id=company_id,
            )

    @pytest.mark.asyncio
    async def test_missing_admin_raises_permission_error(self):
        """Actor without admin role in the space is denied."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        space = _space(company_id)

        space_repo = AsyncMock()
        membership_repo = AsyncMock()
        space_repo.get_by_id_for_company = AsyncMock(return_value=space)
        membership_repo.get = AsyncMock(
            return_value=_membership(space.id, user_id, SpaceRole.VIEWER)
        )

        svc = SpaceHierarchyService(space_repo, membership_repo)
        with pytest.raises(PermissionError):
            await svc.rename(
                actor_id=user_id,
                space_id=space.id,
                name="New Name",
                company_id=company_id,
            )

    @pytest.mark.asyncio
    async def test_editor_role_raises_permission_error(self):
        """Editor (non-admin) role in the space is denied, same as viewer."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        space = _space(company_id)

        space_repo = AsyncMock()
        membership_repo = AsyncMock()
        space_repo.get_by_id_for_company = AsyncMock(return_value=space)
        membership_repo.get = AsyncMock(
            return_value=_membership(space.id, user_id, SpaceRole.EDITOR)
        )

        svc = SpaceHierarchyService(space_repo, membership_repo)
        with pytest.raises(PermissionError):
            await svc.rename(
                actor_id=user_id,
                space_id=space.id,
                name="New Name",
                company_id=company_id,
            )

    @pytest.mark.asyncio
    async def test_empty_name_raises_value_error(self):
        """Whitespace-only name is rejected."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        space = _space(company_id)

        space_repo = AsyncMock()
        membership_repo = AsyncMock()
        space_repo.get_by_id_for_company = AsyncMock(return_value=space)
        membership_repo.get = AsyncMock(
            return_value=_membership(space.id, user_id, SpaceRole.ADMIN)
        )

        svc = SpaceHierarchyService(space_repo, membership_repo)
        with pytest.raises(ValueError, match="empty_name"):
            await svc.rename(
                actor_id=user_id,
                space_id=space.id,
                name="   ",
                company_id=company_id,
            )

    @pytest.mark.asyncio
    async def test_name_too_long_raises_value_error(self):
        """Name over 255 chars is rejected."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        space = _space(company_id)

        space_repo = AsyncMock()
        membership_repo = AsyncMock()
        space_repo.get_by_id_for_company = AsyncMock(return_value=space)
        membership_repo.get = AsyncMock(
            return_value=_membership(space.id, user_id, SpaceRole.ADMIN)
        )

        svc = SpaceHierarchyService(space_repo, membership_repo)
        with pytest.raises(ValueError, match="name_too_long"):
            await svc.rename(
                actor_id=user_id,
                space_id=space.id,
                name="x" * 256,
                company_id=company_id,
            )

    @pytest.mark.asyncio
    async def test_admin_can_rename_returns_updated_space(self):
        """A valid rename by an admin persists via the repository and returns the result."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        space = _space(company_id)
        renamed = space.model_copy(update={"name": "New Name"})

        space_repo = AsyncMock()
        membership_repo = AsyncMock()
        space_repo.get_by_id_for_company = AsyncMock(return_value=space)
        membership_repo.get = AsyncMock(
            return_value=_membership(space.id, user_id, SpaceRole.ADMIN)
        )
        space_repo.rename = AsyncMock(return_value=renamed)

        svc = SpaceHierarchyService(space_repo, membership_repo)
        result = await svc.rename(
            actor_id=user_id,
            space_id=space.id,
            name="New Name",
            company_id=company_id,
        )

        space_repo.rename.assert_awaited_once_with(space.id, "New Name")
        assert result == renamed
