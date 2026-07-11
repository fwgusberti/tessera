"""Unit tests for MemberAccessService — member-centric space access read model (058).

TDD: all tests in this file were written before implementation.
Run: cd packages/core && python -m pytest tests/test_member_access_service.py -v
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from tessera_core.domain.space import Space
from tessera_core.domain.space_access import SpaceAccess
from tessera_core.domain.space_membership import SpaceMembership
from tessera_core.domain.space_role import SpaceRole
from tessera_core.services.member_access import MemberAccessService


def _space(
    company_id: uuid.UUID, parent_id: uuid.UUID | None = None, name: str = "A Space"
) -> Space:
    return Space(
        id=uuid.uuid4(),
        slug=f"sp-{uuid.uuid4().hex[:6]}",
        name=name,
        sector="tech",
        company_id=company_id,
        parent_space_id=parent_id,
    )


def _membership(space_id: uuid.UUID, user_id: uuid.UUID, role: SpaceRole) -> SpaceMembership:
    return SpaceMembership(space_id=space_id, user_id=user_id, role=role)


def _access(space: Space, role: SpaceRole, is_direct: bool) -> SpaceAccess:
    return SpaceAccess(space=space, effective_role=role, is_direct=is_direct)


def _service(
    company_spaces: list[Space],
    accesses: list[SpaceAccess],
    memberships: list[SpaceMembership],
) -> MemberAccessService:
    space_repo = AsyncMock()
    space_repo.list_by_company = AsyncMock(return_value=company_spaces)
    space_repo.list_accessible_by_user = AsyncMock(return_value=accesses)
    membership_repo = AsyncMock()
    membership_repo.list_by_user = AsyncMock(return_value=memberships)
    return MemberAccessService(space_repo, membership_repo)


class TestSpaceAccessForMember:
    @pytest.mark.asyncio
    async def test_every_company_space_appears_exactly_once(self):
        company_id = uuid.uuid4()
        member_id = uuid.uuid4()
        spaces = [_space(company_id, name=f"S{i}") for i in range(3)]

        svc = _service(spaces, [], [])
        rows = await svc.space_access_for_member(member_id, company_id)

        assert [r.space.id for r in rows] == [s.id for s in spaces]
        assert len({r.space.id for r in rows}) == 3

    @pytest.mark.asyncio
    async def test_direct_membership_row(self):
        """A direct space_memberships row yields direct_role == effective_role, is_direct=True."""
        company_id = uuid.uuid4()
        member_id = uuid.uuid4()
        space = _space(company_id)

        svc = _service(
            [space],
            [_access(space, SpaceRole.VIEWER, is_direct=True)],
            [_membership(space.id, member_id, SpaceRole.VIEWER)],
        )
        rows = await svc.space_access_for_member(member_id, company_id)

        assert len(rows) == 1
        row = rows[0]
        assert row.direct_role == SpaceRole.VIEWER
        assert row.effective_role == SpaceRole.VIEWER
        assert row.is_direct is True

    @pytest.mark.asyncio
    async def test_inherited_only_row(self):
        """Access inherited from an ancestor: direct_role=None, effective_role set, is_direct=False."""
        company_id = uuid.uuid4()
        member_id = uuid.uuid4()
        parent = _space(company_id)
        child = _space(company_id, parent_id=parent.id)

        svc = _service(
            [parent, child],
            [
                _access(parent, SpaceRole.EDITOR, is_direct=True),
                _access(child, SpaceRole.EDITOR, is_direct=False),
            ],
            [_membership(parent.id, member_id, SpaceRole.EDITOR)],
        )
        rows = await svc.space_access_for_member(member_id, company_id)

        child_row = next(r for r in rows if r.space.id == child.id)
        assert child_row.direct_role is None
        assert child_row.effective_role == SpaceRole.EDITOR
        assert child_row.is_direct is False

    @pytest.mark.asyncio
    async def test_no_access_row(self):
        """A space the member cannot reach: both roles None, is_direct=False."""
        company_id = uuid.uuid4()
        member_id = uuid.uuid4()
        space = _space(company_id)

        svc = _service([space], [], [])
        rows = await svc.space_access_for_member(member_id, company_id)

        assert len(rows) == 1
        assert rows[0].direct_role is None
        assert rows[0].effective_role is None
        assert rows[0].is_direct is False

    @pytest.mark.asyncio
    async def test_other_company_spaces_never_appear(self):
        """Memberships in another company's spaces produce no rows."""
        company_id = uuid.uuid4()
        other_company_id = uuid.uuid4()
        member_id = uuid.uuid4()
        own_space = _space(company_id)
        foreign_space = _space(other_company_id)

        svc = _service(
            [own_space],
            [],
            [_membership(foreign_space.id, member_id, SpaceRole.ADMIN)],
        )
        rows = await svc.space_access_for_member(member_id, company_id)

        ids = [r.space.id for r in rows]
        assert foreign_space.id not in ids
        assert ids == [own_space.id]
        # the foreign membership must not leak a direct_role onto any row
        assert all(r.direct_role is None for r in rows)

    @pytest.mark.asyncio
    async def test_is_direct_invariant_holds_on_every_row(self):
        """is_direct == (direct_role is not None) across mixed access states."""
        company_id = uuid.uuid4()
        member_id = uuid.uuid4()
        direct = _space(company_id)
        child = _space(company_id, parent_id=direct.id)
        untouched = _space(company_id)

        svc = _service(
            [direct, child, untouched],
            [
                _access(direct, SpaceRole.ADMIN, is_direct=True),
                _access(child, SpaceRole.ADMIN, is_direct=False),
            ],
            [_membership(direct.id, member_id, SpaceRole.ADMIN)],
        )
        rows = await svc.space_access_for_member(member_id, company_id)

        assert len(rows) == 3
        for row in rows:
            assert row.is_direct == (row.direct_role is not None)
