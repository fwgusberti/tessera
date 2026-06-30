"""Unit/contract tests for GET /spaces/{id}/members/search."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from tessera_core.domain.entities import SpaceMembership, SpaceRole, User


def _make_user(user_id: uuid.UUID | None = None, is_admin: bool = False) -> User:
    uid = user_id or uuid.uuid4()
    return User(
        id=uid,
        external_subject=f"sub-{uid}",
        email="actor@example.com",
        display_name="Actor",
        is_admin=is_admin,
    )


def _make_membership(space_id: uuid.UUID, user_id: uuid.UUID, role: SpaceRole) -> SpaceMembership:
    return SpaceMembership(space_id=space_id, user_id=user_id, role=role)


def _company_membership(
    user_id: uuid.UUID, role: "CompanyRole | None" = None
) -> "CompanyMembership":
    from datetime import UTC, datetime

    from tessera_core.domain.entities import CompanyMembership, CompanyRole

    return CompanyMembership(
        id=uuid.uuid4(),
        user_id=user_id,
        company_id=uuid.uuid4(),
        role=role or CompanyRole.MEMBER,
        joined_at=datetime.now(UTC),
    )


def _ctx(actor_id: uuid.UUID, company_admin: bool = False) -> tuple:
    from tessera_core.domain.entities import CompanyRole

    return (
        {"sub": str(actor_id), "id": str(actor_id), "is_admin": False},
        uuid.uuid4(),
        _company_membership(
            actor_id, role=CompanyRole.ADMIN if company_admin else CompanyRole.MEMBER
        ),
    )


class TestSearchMembersContract:
    """GET /spaces/{id}/members/search — search company members eligible for this space."""

    @pytest.mark.anyio
    async def test_returns_matches_for_space_admin(self):
        from tessera_api.routers.members import search_members
        from tessera_core.domain.company_member_match import CompanyMemberMatch

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id)
        _, company_id, _ = ctx

        mock_user = AsyncMock()
        mock_user.get_by_id.return_value = _make_user(actor_id)

        mock_membership_repo = AsyncMock()
        mock_membership_repo.list_by_space.return_value = [
            _make_membership(space_id, actor_id, SpaceRole.ADMIN)
        ]

        match_user_id = uuid.uuid4()
        mock_company_repo = AsyncMock()
        mock_company_repo.search_members_for_space.return_value = [
            CompanyMemberMatch(
                user_id=match_user_id, display_name="Bob Builder", email="bob@acme.com"
            )
        ]

        with (
            patch(
                "tessera_api.routers.members._require_space_in_company",
                new=AsyncMock(return_value=None),
            ),
            patch("tessera_api.routers.members.SqlUserRepository", return_value=mock_user),
            patch(
                "tessera_api.routers.members.SqlSpaceMembershipRepository",
                return_value=mock_membership_repo,
            ),
            patch(
                "tessera_api.routers.members.SqlCompanyRepository", return_value=mock_company_repo
            ),
        ):
            result = await search_members(space_id, "bo", ctx, session)

        assert result == {
            "members": [
                {
                    "user_id": str(match_user_id),
                    "display_name": "Bob Builder",
                    "email": "bob@acme.com",
                }
            ]
        }
        mock_company_repo.search_members_for_space.assert_awaited_once_with(
            company_id, space_id, "bo"
        )

    @pytest.mark.anyio
    async def test_returns_empty_list_when_no_matches(self):
        from tessera_api.routers.members import search_members

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id)

        mock_user = AsyncMock()
        mock_user.get_by_id.return_value = _make_user(actor_id)

        mock_membership_repo = AsyncMock()
        mock_membership_repo.list_by_space.return_value = [
            _make_membership(space_id, actor_id, SpaceRole.ADMIN)
        ]

        mock_company_repo = AsyncMock()
        mock_company_repo.search_members_for_space.return_value = []

        with (
            patch(
                "tessera_api.routers.members._require_space_in_company",
                new=AsyncMock(return_value=None),
            ),
            patch("tessera_api.routers.members.SqlUserRepository", return_value=mock_user),
            patch(
                "tessera_api.routers.members.SqlSpaceMembershipRepository",
                return_value=mock_membership_repo,
            ),
            patch(
                "tessera_api.routers.members.SqlCompanyRepository", return_value=mock_company_repo
            ),
        ):
            result = await search_members(space_id, "zzz", ctx, session)

        assert result == {"members": []}

    @pytest.mark.anyio
    async def test_returns_403_when_caller_not_space_or_company_admin(self):
        from fastapi import HTTPException

        from tessera_api.routers.members import search_members

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id, company_admin=False)

        mock_user = AsyncMock()
        mock_user.get_by_id.return_value = _make_user(actor_id)

        mock_membership_repo = AsyncMock()
        mock_membership_repo.list_by_space.return_value = [
            _make_membership(space_id, actor_id, SpaceRole.VIEWER)
        ]

        with (
            patch(
                "tessera_api.routers.members._require_space_in_company",
                new=AsyncMock(return_value=None),
            ),
            patch("tessera_api.routers.members.SqlUserRepository", return_value=mock_user),
            patch(
                "tessera_api.routers.members.SqlSpaceMembershipRepository",
                return_value=mock_membership_repo,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await search_members(space_id, "bo", ctx, session)

        assert exc_info.value.status_code == 403

    @pytest.mark.anyio
    async def test_returns_404_when_space_not_in_company(self):
        from fastapi import HTTPException

        from tessera_api.routers.members import search_members

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id)

        not_found = HTTPException(
            status_code=404, detail={"error": {"code": "not_found", "message": "Not found"}}
        )

        with (
            patch(
                "tessera_api.routers.members._require_space_in_company",
                new=AsyncMock(side_effect=not_found),
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await search_members(space_id, "bo", ctx, session)

        assert exc_info.value.status_code == 404
