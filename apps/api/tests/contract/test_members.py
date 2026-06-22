"""Contract tests: member management endpoints invariants."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
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


@asynccontextmanager
async def _mock_db(session: AsyncMock = None):
    yield session or AsyncMock()


class TestInviteMemberContract:
    """POST /spaces/{id}/members — invite must call MembershipService.invite and return 201."""

    @pytest.mark.anyio
    async def test_invite_calls_service_invite_and_returns_201(self):
        from tessera_api.routers.members import invite_member

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        membership = _make_membership(space_id, target_id, SpaceRole.EDITOR)

        mock_svc = AsyncMock()
        mock_svc.invite.return_value = membership

        with (
            patch(
                "tessera_api.routers.members.require_user",
                new=AsyncMock(return_value={"sub": str(actor_id), "is_admin": False}),
            ),
            patch("tessera_api.routers.members.get_db") as mock_get_db,
            patch(
                "tessera_api.routers.members.SqlUserRepository"
            ) as mock_user_repo_cls,
            patch(
                "tessera_api.routers.members.SqlSpaceMembershipRepository"
            ) as mock_membership_repo_cls,
            patch(
                "tessera_api.routers.members.SqlAuditRepository"
            ) as mock_audit_repo_cls,
            patch(
                "tessera_api.routers.members.MembershipService",
                return_value=mock_svc,
            ),
        ):
            session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_user = AsyncMock()
            mock_user.get_by_id.return_value = _make_user(actor_id)
            mock_user_repo_cls.return_value = mock_user

            from tessera_api.routers.members import InviteMemberRequest

            body = InviteMemberRequest(user_id=target_id, role=SpaceRole.EDITOR)
            result = await invite_member(space_id, body, MagicMock())

        mock_svc.invite.assert_called_once()
        assert result["membership"]["role"] == SpaceRole.EDITOR.value

    @pytest.mark.anyio
    async def test_invite_returns_403_on_permission_error(self):
        from fastapi import HTTPException

        from tessera_api.routers.members import invite_member

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        mock_svc = AsyncMock()
        mock_svc.invite.side_effect = PermissionError("not admin")

        with (
            patch(
                "tessera_api.routers.members.require_user",
                new=AsyncMock(return_value={"sub": str(actor_id), "is_admin": False}),
            ),
            patch("tessera_api.routers.members.get_db") as mock_get_db,
            patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
            patch("tessera_api.routers.members.SqlSpaceMembershipRepository"),
            patch("tessera_api.routers.members.SqlAuditRepository"),
            patch("tessera_api.routers.members.MembershipService", return_value=mock_svc),
        ):
            session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_user = AsyncMock()
            mock_user.get_by_id.return_value = _make_user(actor_id)
            mock_user_repo_cls.return_value = mock_user

            from tessera_api.routers.members import InviteMemberRequest

            body = InviteMemberRequest(user_id=uuid.uuid4(), role=SpaceRole.VIEWER)
            with pytest.raises(HTTPException) as exc_info:
                await invite_member(space_id, body, MagicMock())
            assert exc_info.value.status_code == 403


class TestListMembersContract:
    """GET /spaces/{id}/members — must return member list."""

    @pytest.mark.anyio
    async def test_list_returns_members(self):
        from tessera_api.routers.members import list_members

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        memberships = [_make_membership(space_id, actor_id, SpaceRole.ADMIN)]

        with (
            patch(
                "tessera_api.routers.members.require_company_context",
                new=AsyncMock(return_value=({"sub": str(actor_id), "id": str(actor_id), "is_admin": False}, uuid.uuid4())),
            ),
            patch(
                "tessera_api.routers.members.validate_space_for_company",
                new=AsyncMock(return_value=None),
            ),
            patch("tessera_api.routers.members.get_db") as mock_get_db,
            patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
            patch(
                "tessera_api.routers.members.SqlSpaceMembershipRepository"
            ) as mock_membership_repo_cls,
        ):
            session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            actor = _make_user(actor_id)
            mock_user = AsyncMock()
            mock_user.get_by_id.return_value = actor
            mock_user_repo_cls.return_value = mock_user

            mock_membership_repo = AsyncMock()
            mock_membership_repo.list_by_space.return_value = memberships
            mock_membership_repo_cls.return_value = mock_membership_repo

            result = await list_members(space_id, MagicMock())

        assert "members" in result
        assert len(result["members"]) == 1


class TestGetMyMembershipContract:
    """GET /spaces/{id}/members/me — must return caller's membership or 404."""

    @pytest.mark.anyio
    async def test_returns_membership_for_member(self):
        from tessera_api.routers.members import get_my_membership

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        membership = _make_membership(space_id, actor_id, SpaceRole.VIEWER)

        with (
            patch(
                "tessera_api.routers.members.require_user",
                new=AsyncMock(return_value={"sub": str(actor_id), "is_admin": False}),
            ),
            patch("tessera_api.routers.members.get_db") as mock_get_db,
            patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
            patch(
                "tessera_api.routers.members.SqlSpaceMembershipRepository"
            ) as mock_membership_repo_cls,
        ):
            session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_user = AsyncMock()
            mock_user.get_by_id.return_value = _make_user(actor_id)
            mock_user_repo_cls.return_value = mock_user

            mock_membership_repo = AsyncMock()
            mock_membership_repo.get.return_value = membership
            mock_membership_repo_cls.return_value = mock_membership_repo

            result = await get_my_membership(space_id, MagicMock())

        assert result["membership"]["role"] == SpaceRole.VIEWER.value

    @pytest.mark.anyio
    async def test_returns_404_for_non_member(self):
        from fastapi import HTTPException

        from tessera_api.routers.members import get_my_membership

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        with (
            patch(
                "tessera_api.routers.members.require_user",
                new=AsyncMock(return_value={"sub": str(actor_id), "is_admin": False}),
            ),
            patch("tessera_api.routers.members.get_db") as mock_get_db,
            patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
            patch(
                "tessera_api.routers.members.SqlSpaceMembershipRepository"
            ) as mock_membership_repo_cls,
        ):
            session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_user = AsyncMock()
            mock_user.get_by_id.return_value = _make_user(actor_id)
            mock_user_repo_cls.return_value = mock_user

            mock_membership_repo = AsyncMock()
            mock_membership_repo.get.return_value = None
            mock_membership_repo_cls.return_value = mock_membership_repo

            with pytest.raises(HTTPException) as exc_info:
                await get_my_membership(space_id, MagicMock())
            assert exc_info.value.status_code == 404


class TestChangeRoleContract:
    """PUT /spaces/{id}/members/{user_id} — must call change_role and return 200."""

    @pytest.mark.anyio
    async def test_change_role_returns_updated_membership(self):
        from tessera_api.routers.members import change_member_role

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        updated = _make_membership(space_id, target_id, SpaceRole.EDITOR)

        mock_svc = AsyncMock()
        mock_svc.change_role.return_value = updated

        with (
            patch(
                "tessera_api.routers.members.require_user",
                new=AsyncMock(return_value={"sub": str(actor_id), "is_admin": False}),
            ),
            patch("tessera_api.routers.members.get_db") as mock_get_db,
            patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
            patch("tessera_api.routers.members.SqlSpaceMembershipRepository"),
            patch("tessera_api.routers.members.SqlAuditRepository"),
            patch("tessera_api.routers.members.MembershipService", return_value=mock_svc),
        ):
            session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_user = AsyncMock()
            mock_user.get_by_id.return_value = _make_user(actor_id)
            mock_user_repo_cls.return_value = mock_user

            from tessera_api.routers.members import ChangeRoleRequest

            body = ChangeRoleRequest(role=SpaceRole.EDITOR)
            result = await change_member_role(space_id, target_id, body, MagicMock())

        mock_svc.change_role.assert_called_once()
        assert result["membership"]["role"] == SpaceRole.EDITOR.value

    @pytest.mark.anyio
    async def test_change_role_returns_409_on_last_admin(self):
        from fastapi import HTTPException

        from tessera_api.routers.members import change_member_role

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()

        mock_svc = AsyncMock()
        mock_svc.change_role.side_effect = ValueError("last admin")

        with (
            patch(
                "tessera_api.routers.members.require_user",
                new=AsyncMock(return_value={"sub": str(actor_id), "is_admin": False}),
            ),
            patch("tessera_api.routers.members.get_db") as mock_get_db,
            patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
            patch("tessera_api.routers.members.SqlSpaceMembershipRepository"),
            patch("tessera_api.routers.members.SqlAuditRepository"),
            patch("tessera_api.routers.members.MembershipService", return_value=mock_svc),
        ):
            session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_user = AsyncMock()
            mock_user.get_by_id.return_value = _make_user(actor_id)
            mock_user_repo_cls.return_value = mock_user

            from tessera_api.routers.members import ChangeRoleRequest

            body = ChangeRoleRequest(role=SpaceRole.VIEWER)
            with pytest.raises(HTTPException) as exc_info:
                await change_member_role(space_id, target_id, body, MagicMock())
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

        mock_svc = AsyncMock()
        mock_svc.remove.return_value = None

        with (
            patch(
                "tessera_api.routers.members.require_user",
                new=AsyncMock(return_value={"sub": str(actor_id), "is_admin": False}),
            ),
            patch("tessera_api.routers.members.get_db") as mock_get_db,
            patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
            patch("tessera_api.routers.members.SqlSpaceMembershipRepository"),
            patch("tessera_api.routers.members.SqlAuditRepository"),
            patch("tessera_api.routers.members.MembershipService", return_value=mock_svc),
        ):
            session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_user = AsyncMock()
            mock_user.get_by_id.return_value = _make_user(actor_id)
            mock_user_repo_cls.return_value = mock_user

            result = await remove_member(space_id, target_id, MagicMock())

        mock_svc.remove.assert_called_once()
        assert isinstance(result, Response)
        assert result.status_code == 204
