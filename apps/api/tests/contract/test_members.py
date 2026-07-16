"""Contract tests: member management endpoints invariants."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

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


def _company_membership(user_id: uuid.UUID, role: "CompanyRole | None" = None) -> "CompanyMembership":
    from datetime import UTC, datetime

    from tessera_core.domain.entities import CompanyMembership, CompanyRole

    return CompanyMembership(
        id=uuid.uuid4(),
        user_id=user_id,
        company_id=uuid.uuid4(),
        role=role or CompanyRole.MEMBER,
        joined_at=datetime.now(UTC),
    )


def _ctx(actor_id: uuid.UUID) -> tuple:
    return (
        {"sub": str(actor_id), "id": str(actor_id), "is_admin": False},
        uuid.uuid4(),
        _company_membership(actor_id),
    )


class TestInviteMemberContract:
    """POST /spaces/{id}/members — invite must call MembershipService.invite and return 201."""

    @pytest.mark.anyio
    async def test_invite_calls_service_invite_and_returns_201(self):
        from tessera_api.routers.members import invite_member, InviteMemberRequest

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        session = AsyncMock()
        membership = _make_membership(space_id, target_id, SpaceRole.EDITOR)

        mock_svc = AsyncMock()
        mock_svc.invite.return_value = membership

        mock_user = AsyncMock()
        mock_user.get_by_id.return_value = _make_user(actor_id)

        with (
            patch("tessera_api.routers.members._require_space_in_company", new=AsyncMock(return_value=None)),
            patch("tessera_api.routers.members.SqlUserRepository", return_value=mock_user),
            patch("tessera_api.routers.members.SqlSpaceMembershipRepository"),
            patch("tessera_api.routers.members.SqlAuditRepository"),
            patch("tessera_api.routers.members.MembershipService", return_value=mock_svc),
        ):
            body = InviteMemberRequest(user_id=target_id, role=SpaceRole.EDITOR)
            result = await invite_member(space_id, body, _ctx(actor_id), session)

        mock_svc.invite.assert_called_once()
        assert result["membership"]["role"] == SpaceRole.EDITOR.value

    @pytest.mark.anyio
    async def test_invite_returns_403_on_permission_error(self):
        from fastapi import HTTPException

        from tessera_api.routers.members import invite_member, InviteMemberRequest

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()

        mock_svc = AsyncMock()
        mock_svc.invite.side_effect = PermissionError("not admin")

        mock_user = AsyncMock()
        mock_user.get_by_id.return_value = _make_user(actor_id)

        with (
            patch("tessera_api.routers.members._require_space_in_company", new=AsyncMock(return_value=None)),
            patch("tessera_api.routers.members.SqlUserRepository", return_value=mock_user),
            patch("tessera_api.routers.members.SqlSpaceMembershipRepository"),
            patch("tessera_api.routers.members.SqlAuditRepository"),
            patch("tessera_api.routers.members.MembershipService", return_value=mock_svc),
        ):
            body = InviteMemberRequest(user_id=uuid.uuid4(), role=SpaceRole.VIEWER)
            with pytest.raises(HTTPException) as exc_info:
                await invite_member(space_id, body, _ctx(actor_id), session)
            assert exc_info.value.status_code == 403


def _make_listing(
    space_id: uuid.UUID,
    user_id: uuid.UUID,
    role: SpaceRole,
    display_name: str = "Actor",
    email: str = "actor@example.com",
):
    from datetime import UTC, datetime

    from tessera_core.domain.entities import SpaceMemberListing

    now = datetime.now(UTC)
    return SpaceMemberListing(
        id=uuid.uuid4(),
        space_id=space_id,
        user_id=user_id,
        display_name=display_name,
        email=email,
        role=role,
        invited_by_user_id=None,
        created_at=now,
        updated_at=now,
    )


class TestListMembersContract:
    """GET /spaces/{id}/members — must return the identity-enriched member list."""

    @pytest.mark.anyio
    async def test_list_returns_members(self):
        from tessera_api.routers.members import list_members

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        listings = [_make_listing(space_id, actor_id, SpaceRole.ADMIN)]

        actor = _make_user(actor_id)
        mock_user = AsyncMock()
        mock_user.get_by_id.return_value = actor

        mock_membership_repo = AsyncMock()
        mock_membership_repo.list_by_space_with_identity.return_value = listings

        with (
            patch("tessera_api.routers.members.validate_space_for_company", new=AsyncMock(return_value=None)),
            patch("tessera_api.routers.members.SqlUserRepository", return_value=mock_user),
            patch("tessera_api.routers.members.SqlSpaceMembershipRepository", return_value=mock_membership_repo),
        ):
            result = await list_members(space_id, _ctx(actor_id), session)

        assert "members" in result
        assert len(result["members"]) == 1

    @pytest.mark.anyio
    async def test_enriched_row_carries_full_shape(self):
        """Each row: {id, space_id, user_id, display_name, email, role,
        invited_by_user_id, created_at, updated_at} — additive over the old shape."""
        from tessera_api.routers.members import list_members

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        listings = [
            _make_listing(
                space_id, actor_id, SpaceRole.ADMIN,
                display_name="Ada Lovelace", email="ada@acme.example",
            )
        ]

        mock_user = AsyncMock()
        mock_user.get_by_id.return_value = _make_user(actor_id)

        mock_membership_repo = AsyncMock()
        mock_membership_repo.list_by_space_with_identity.return_value = listings

        with (
            patch("tessera_api.routers.members.validate_space_for_company", new=AsyncMock(return_value=None)),
            patch("tessera_api.routers.members.SqlUserRepository", return_value=mock_user),
            patch("tessera_api.routers.members.SqlSpaceMembershipRepository", return_value=mock_membership_repo),
        ):
            result = await list_members(space_id, _ctx(actor_id), session)

        (row,) = result["members"]
        assert set(row) == {
            "id",
            "space_id",
            "user_id",
            "display_name",
            "email",
            "role",
            "invited_by_user_id",
            "created_at",
            "updated_at",
        }
        assert row["display_name"] == "Ada Lovelace"
        assert row["email"] == "ada@acme.example"
        assert row["role"] == SpaceRole.ADMIN.value
        assert row["user_id"] == actor_id
        assert row["invited_by_user_id"] is None

    @pytest.mark.anyio
    async def test_blank_display_name_is_empty_string_never_null(self):
        from tessera_api.routers.members import list_members

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        listings = [
            _make_listing(
                space_id, actor_id, SpaceRole.VIEWER,
                display_name="", email="blank@acme.example",
            )
        ]

        mock_user = AsyncMock()
        mock_user.get_by_id.return_value = _make_user(actor_id)

        mock_membership_repo = AsyncMock()
        mock_membership_repo.list_by_space_with_identity.return_value = listings

        with (
            patch("tessera_api.routers.members.validate_space_for_company", new=AsyncMock(return_value=None)),
            patch("tessera_api.routers.members.SqlUserRepository", return_value=mock_user),
            patch("tessera_api.routers.members.SqlSpaceMembershipRepository", return_value=mock_membership_repo),
        ):
            result = await list_members(space_id, _ctx(actor_id), session)

        (row,) = result["members"]
        assert row["display_name"] == ""
        assert row["display_name"] is not None
        assert row["email"] == "blank@acme.example"


class TestGetMyMembershipContract:
    """GET /spaces/{id}/members/me — must return caller's membership or 404."""

    @pytest.mark.anyio
    async def test_returns_membership_for_member(self):
        from tessera_api.routers.members import get_my_membership

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        membership = _make_membership(space_id, actor_id, SpaceRole.VIEWER)

        mock_user = AsyncMock()
        mock_user.get_by_id.return_value = _make_user(actor_id)

        mock_membership_repo = AsyncMock()
        mock_membership_repo.get.return_value = membership

        with (
            patch("tessera_api.routers.members._require_space_in_company", new=AsyncMock(return_value=None)),
            patch("tessera_api.routers.members.SqlUserRepository", return_value=mock_user),
            patch("tessera_api.routers.members.SqlSpaceMembershipRepository", return_value=mock_membership_repo),
        ):
            result = await get_my_membership(space_id, _ctx(actor_id), session)

        assert result["membership"]["role"] == SpaceRole.VIEWER.value

    @pytest.mark.anyio
    async def test_returns_404_for_non_member(self):
        from fastapi import HTTPException

        from tessera_api.routers.members import get_my_membership

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()

        mock_user = AsyncMock()
        mock_user.get_by_id.return_value = _make_user(actor_id)

        mock_membership_repo = AsyncMock()
        mock_membership_repo.get.return_value = None

        with (
            patch("tessera_api.routers.members._require_space_in_company", new=AsyncMock(return_value=None)),
            patch("tessera_api.routers.members.SqlUserRepository", return_value=mock_user),
            patch("tessera_api.routers.members.SqlSpaceMembershipRepository", return_value=mock_membership_repo),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_my_membership(space_id, _ctx(actor_id), session)
            assert exc_info.value.status_code == 404


class TestChangeRoleContract:
    """PUT /spaces/{id}/members/{user_id} — must call change_role and return 200."""

    @pytest.mark.anyio
    async def test_change_role_returns_updated_membership(self):
        from tessera_api.routers.members import change_member_role, ChangeRoleRequest

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        session = AsyncMock()
        updated = _make_membership(space_id, target_id, SpaceRole.EDITOR)

        mock_svc = AsyncMock()
        mock_svc.change_role.return_value = updated

        mock_user = AsyncMock()
        mock_user.get_by_id.return_value = _make_user(actor_id)

        with (
            patch("tessera_api.routers.members._require_space_in_company", new=AsyncMock(return_value=None)),
            patch("tessera_api.routers.members.SqlUserRepository", return_value=mock_user),
            patch("tessera_api.routers.members.SqlSpaceMembershipRepository"),
            patch("tessera_api.routers.members.SqlAuditRepository"),
            patch("tessera_api.routers.members.MembershipService", return_value=mock_svc),
        ):
            body = ChangeRoleRequest(role=SpaceRole.EDITOR)
            result = await change_member_role(space_id, target_id, body, _ctx(actor_id), session)

        mock_svc.change_role.assert_called_once()
        assert result["membership"]["role"] == SpaceRole.EDITOR.value

    @pytest.mark.anyio
    async def test_change_role_returns_409_on_last_admin(self):
        from fastapi import HTTPException

        from tessera_api.routers.members import change_member_role, ChangeRoleRequest

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        session = AsyncMock()

        mock_svc = AsyncMock()
        mock_svc.change_role.side_effect = ValueError("last admin")

        mock_user = AsyncMock()
        mock_user.get_by_id.return_value = _make_user(actor_id)

        with (
            patch("tessera_api.routers.members._require_space_in_company", new=AsyncMock(return_value=None)),
            patch("tessera_api.routers.members.SqlUserRepository", return_value=mock_user),
            patch("tessera_api.routers.members.SqlSpaceMembershipRepository"),
            patch("tessera_api.routers.members.SqlAuditRepository"),
            patch("tessera_api.routers.members.MembershipService", return_value=mock_svc),
        ):
            body = ChangeRoleRequest(role=SpaceRole.VIEWER)
            with pytest.raises(HTTPException) as exc_info:
                await change_member_role(space_id, target_id, body, _ctx(actor_id), session)
            assert exc_info.value.status_code == 409


class TestRemoveMemberContract:
    """DELETE /spaces/{id}/members/{user_id} — must call remove and return 204."""

    @pytest.mark.anyio
    async def test_remove_calls_service_and_returns_no_content(self):
        from fastapi.responses import Response

        from tessera_api.routers.members import remove_member

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        session = AsyncMock()

        mock_svc = AsyncMock()
        mock_svc.remove.return_value = None

        mock_user = AsyncMock()
        mock_user.get_by_id.return_value = _make_user(actor_id)

        with (
            patch("tessera_api.routers.members._require_space_in_company", new=AsyncMock(return_value=None)),
            patch("tessera_api.routers.members.SqlUserRepository", return_value=mock_user),
            patch("tessera_api.routers.members.SqlSpaceMembershipRepository"),
            patch("tessera_api.routers.members.SqlAuditRepository"),
            patch("tessera_api.routers.members.MembershipService", return_value=mock_svc),
        ):
            result = await remove_member(space_id, target_id, _ctx(actor_id), session)

        mock_svc.remove.assert_called_once()
        assert isinstance(result, Response)
        assert result.status_code == 204
