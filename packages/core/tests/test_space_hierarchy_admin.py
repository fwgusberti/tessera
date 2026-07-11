"""Unit tests for the company-admin visibility branch in SpaceHierarchyService (058, US2).

TDD: all tests in this file were written before implementation.
Run: cd packages/core && python -m pytest tests/test_space_hierarchy_admin.py -v
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from tessera_core.domain.space import Space
from tessera_core.domain.space_access import SpaceAccess
from tessera_core.domain.space_role import SpaceRole
from tessera_core.services.space_hierarchy import SpaceHierarchyService


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


def _access(space: Space, role: SpaceRole, is_direct: bool) -> SpaceAccess:
    return SpaceAccess(space=space, effective_role=role, is_direct=is_direct)


def _service(
    accesses: list[SpaceAccess], company_spaces: list[Space]
) -> tuple[SpaceHierarchyService, AsyncMock]:
    space_repo = AsyncMock()
    space_repo.list_accessible_by_user = AsyncMock(return_value=accesses)
    space_repo.list_by_company = AsyncMock(return_value=company_spaces)
    return SpaceHierarchyService(space_repo, AsyncMock()), space_repo


class TestAdminWideListing:
    @pytest.mark.asyncio
    async def test_admin_gets_membership_accesses_union_remaining_company_spaces(self):
        """Membership-derived values unchanged; the rest appear as implicit admin."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        member_space = _space(company_id, name="Mine")
        other_space = _space(company_id, name="Not mine")

        svc, _repo = _service(
            [_access(member_space, SpaceRole.VIEWER, is_direct=True)],
            [member_space, other_space],
        )
        result = await svc.list_accessible(user_id, company_id, is_company_admin=True)

        by_id = {a.space.id: a for a in result}
        assert set(by_id) == {member_space.id, other_space.id}

        # membership-derived access is passed through unchanged
        assert by_id[member_space.id].effective_role == SpaceRole.VIEWER
        assert by_id[member_space.id].is_direct is True

        # non-member company space appears as implicit admin, not direct
        assert by_id[other_space.id].effective_role == SpaceRole.ADMIN
        assert by_id[other_space.id].is_direct is False

    @pytest.mark.asyncio
    async def test_non_admin_set_unchanged(self):
        """Without the flag the result is exactly the membership-derived set."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        member_space = _space(company_id)
        other_space = _space(company_id)

        svc, repo = _service(
            [_access(member_space, SpaceRole.EDITOR, is_direct=True)],
            [member_space, other_space],
        )
        result = await svc.list_accessible(user_id, company_id)

        assert [a.space.id for a in result] == [member_space.id]
        # the admin-wide query is never issued for non-admins
        repo.list_by_company.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_admin_listing_scoped_to_company_query(self):
        """The union draws only from list_by_company(company_id) — nothing else."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        company_space = _space(company_id)

        svc, repo = _service([], [company_space])
        result = await svc.list_accessible(user_id, company_id, is_company_admin=True)

        repo.list_by_company.assert_awaited_once_with(company_id)
        assert [a.space.id for a in result] == [company_space.id]


class TestSingleSpaceAccessCheck:
    @pytest.mark.asyncio
    async def test_admin_can_access_non_member_space(self):
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        other_space = _space(company_id)

        svc, _repo = _service([], [other_space])
        access = await svc.get_access(user_id, other_space.id, company_id, is_company_admin=True)

        assert access is not None
        assert access.effective_role == SpaceRole.ADMIN
        assert access.is_direct is False

    @pytest.mark.asyncio
    async def test_non_admin_cannot_access_non_member_space(self):
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        other_space = _space(company_id)

        svc, _repo = _service([], [other_space])
        access = await svc.get_access(user_id, other_space.id, company_id)

        assert access is None

    @pytest.mark.asyncio
    async def test_admin_access_check_never_reaches_foreign_space(self):
        """A space outside the company (absent from both scoped queries) stays invisible."""
        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        foreign_space = _space(uuid.uuid4())  # another company

        svc, _repo = _service([], [])
        access = await svc.get_access(user_id, foreign_space.id, company_id, is_company_admin=True)

        assert access is None
