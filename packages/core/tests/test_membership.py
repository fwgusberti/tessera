"""Unit tests for SpaceMembership permission functions and MembershipService."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from tessera_core.domain.entities import AuditRecord, SpaceMembership, SpaceRole, User
from tessera_core.permissions.access import (
    can_manage_members,
    can_read_space_document,
    can_write_document,
    effective_space_role,
    get_space_membership_role,
)
from tessera_core.services.membership import MembershipService


def _user(is_admin: bool = False) -> User:
    return User(
        id=uuid.uuid4(),
        external_subject=f"sub-{uuid.uuid4()}",
        email="u@example.com",
        display_name="Test User",
        is_admin=is_admin,
    )


def _membership(space_id: uuid.UUID, user_id: uuid.UUID, role: SpaceRole) -> SpaceMembership:
    return SpaceMembership(space_id=space_id, user_id=user_id, role=role)


# ---------------------------------------------------------------------------
# get_space_membership_role
# ---------------------------------------------------------------------------


class TestGetSpaceMembershipRole:
    def test_returns_role_for_matching_membership(self):
        space_id = uuid.uuid4()
        user = _user()
        memberships = [_membership(space_id, user.id, SpaceRole.EDITOR)]
        assert get_space_membership_role(user.id, space_id, memberships) == SpaceRole.EDITOR

    def test_returns_none_when_not_a_member(self):
        space_id = uuid.uuid4()
        user = _user()
        other = _user()
        memberships = [_membership(space_id, other.id, SpaceRole.ADMIN)]
        assert get_space_membership_role(user.id, space_id, memberships) is None

    def test_returns_none_for_different_space(self):
        space_id = uuid.uuid4()
        other_space = uuid.uuid4()
        user = _user()
        memberships = [_membership(other_space, user.id, SpaceRole.VIEWER)]
        assert get_space_membership_role(user.id, space_id, memberships) is None


# ---------------------------------------------------------------------------
# effective_space_role
# ---------------------------------------------------------------------------


class TestEffectiveSpaceRole:
    def test_global_admin_returns_admin_regardless_of_membership(self):
        space_id = uuid.uuid4()
        user = _user(is_admin=True)
        assert effective_space_role(user, space_id, []) == SpaceRole.ADMIN

    def test_non_admin_returns_direct_membership_role(self):
        space_id = uuid.uuid4()
        user = _user()
        memberships = [_membership(space_id, user.id, SpaceRole.VIEWER)]
        assert effective_space_role(user, space_id, memberships) == SpaceRole.VIEWER

    def test_non_member_returns_none(self):
        space_id = uuid.uuid4()
        user = _user()
        assert effective_space_role(user, space_id, []) is None


# ---------------------------------------------------------------------------
# can_write_document
# ---------------------------------------------------------------------------


class TestCanWriteDocument:
    def test_editor_can_write(self):
        space_id = uuid.uuid4()
        user = _user()
        memberships = [_membership(space_id, user.id, SpaceRole.EDITOR)]
        assert can_write_document(user, space_id, memberships) is True

    def test_admin_can_write(self):
        space_id = uuid.uuid4()
        user = _user()
        memberships = [_membership(space_id, user.id, SpaceRole.ADMIN)]
        assert can_write_document(user, space_id, memberships) is True

    def test_viewer_cannot_write(self):
        space_id = uuid.uuid4()
        user = _user()
        memberships = [_membership(space_id, user.id, SpaceRole.VIEWER)]
        assert can_write_document(user, space_id, memberships) is False

    def test_non_member_cannot_write(self):
        space_id = uuid.uuid4()
        user = _user()
        assert can_write_document(user, space_id, []) is False

    def test_global_admin_can_write(self):
        space_id = uuid.uuid4()
        user = _user(is_admin=True)
        assert can_write_document(user, space_id, []) is True


# ---------------------------------------------------------------------------
# can_manage_members
# ---------------------------------------------------------------------------


class TestCanManageMembers:
    def test_admin_can_manage(self):
        space_id = uuid.uuid4()
        user = _user()
        memberships = [_membership(space_id, user.id, SpaceRole.ADMIN)]
        assert can_manage_members(user, space_id, memberships) is True

    def test_editor_cannot_manage(self):
        space_id = uuid.uuid4()
        user = _user()
        memberships = [_membership(space_id, user.id, SpaceRole.EDITOR)]
        assert can_manage_members(user, space_id, memberships) is False

    def test_viewer_cannot_manage(self):
        space_id = uuid.uuid4()
        user = _user()
        memberships = [_membership(space_id, user.id, SpaceRole.VIEWER)]
        assert can_manage_members(user, space_id, memberships) is False

    def test_global_admin_can_manage(self):
        space_id = uuid.uuid4()
        user = _user(is_admin=True)
        assert can_manage_members(user, space_id, []) is True


# ---------------------------------------------------------------------------
# can_read_space_document
# ---------------------------------------------------------------------------


class TestCanReadSpaceDocument:
    def test_any_member_can_read(self):
        space_id = uuid.uuid4()
        user = _user()
        for role in SpaceRole:
            memberships = [_membership(space_id, user.id, role)]
            assert can_read_space_document(user, space_id, memberships) is True

    def test_non_member_cannot_read(self):
        space_id = uuid.uuid4()
        user = _user()
        assert can_read_space_document(user, space_id, []) is False

    def test_global_admin_can_read(self):
        space_id = uuid.uuid4()
        user = _user(is_admin=True)
        assert can_read_space_document(user, space_id, []) is True


# ---------------------------------------------------------------------------
# MembershipService
# ---------------------------------------------------------------------------


def _make_service():
    repo = AsyncMock()
    audit = AsyncMock()
    return MembershipService(repo=repo, audit=audit), repo, audit


class TestMembershipServiceInvite:
    @pytest.mark.asyncio
    async def test_invite_success_as_space_admin(self):
        svc, repo, audit = _make_service()
        space_id = uuid.uuid4()
        actor = _user()
        target_user_id = uuid.uuid4()
        expected = SpaceMembership(
            space_id=space_id, user_id=target_user_id, role=SpaceRole.EDITOR
        )

        repo.list_by_space.return_value = [
            _membership(space_id, actor.id, SpaceRole.ADMIN)
        ]
        repo.get.return_value = None
        repo.add.return_value = expected

        result = await svc.invite(actor, space_id, target_user_id, SpaceRole.EDITOR)

        assert result.role == SpaceRole.EDITOR
        repo.add.assert_called_once()
        audit.append.assert_called_once()
        record: AuditRecord = audit.append.call_args[0][0]
        assert record.action == "member_invited"

    @pytest.mark.asyncio
    async def test_invite_raises_permission_error_for_non_admin(self):
        svc, repo, _ = _make_service()
        space_id = uuid.uuid4()
        actor = _user()

        repo.list_by_space.return_value = [
            _membership(space_id, actor.id, SpaceRole.EDITOR)
        ]

        with pytest.raises(PermissionError):
            await svc.invite(actor, space_id, uuid.uuid4(), SpaceRole.VIEWER)

    @pytest.mark.asyncio
    async def test_invite_raises_value_error_for_duplicate_member(self):
        svc, repo, _ = _make_service()
        space_id = uuid.uuid4()
        actor = _user()
        target_user_id = uuid.uuid4()

        repo.list_by_space.return_value = [
            _membership(space_id, actor.id, SpaceRole.ADMIN)
        ]
        repo.get.return_value = _membership(space_id, target_user_id, SpaceRole.VIEWER)

        with pytest.raises(ValueError, match="already a member"):
            await svc.invite(actor, space_id, target_user_id, SpaceRole.EDITOR)

    @pytest.mark.asyncio
    async def test_global_admin_can_invite_without_membership(self):
        svc, repo, audit = _make_service()
        space_id = uuid.uuid4()
        actor = _user(is_admin=True)
        target_user_id = uuid.uuid4()
        expected = SpaceMembership(
            space_id=space_id, user_id=target_user_id, role=SpaceRole.VIEWER
        )

        repo.list_by_space.return_value = []
        repo.get.return_value = None
        repo.add.return_value = expected

        result = await svc.invite(actor, space_id, target_user_id, SpaceRole.VIEWER)
        assert result is not None


class TestMembershipServiceChangeRole:
    @pytest.mark.asyncio
    async def test_change_role_success(self):
        svc, repo, audit = _make_service()
        space_id = uuid.uuid4()
        actor = _user()
        target_id = uuid.uuid4()
        updated = SpaceMembership(space_id=space_id, user_id=target_id, role=SpaceRole.EDITOR)

        repo.list_by_space.return_value = [
            _membership(space_id, actor.id, SpaceRole.ADMIN),
            _membership(space_id, target_id, SpaceRole.VIEWER),
        ]
        repo.count_admins.return_value = 2
        repo.update_role.return_value = updated

        result = await svc.change_role(actor, space_id, target_id, SpaceRole.EDITOR)
        assert result.role == SpaceRole.EDITOR
        audit.append.assert_called_once()
        record: AuditRecord = audit.append.call_args[0][0]
        assert record.action == "role_changed"

    @pytest.mark.asyncio
    async def test_change_role_raises_for_non_admin_actor(self):
        svc, repo, _ = _make_service()
        space_id = uuid.uuid4()
        actor = _user()

        repo.list_by_space.return_value = [
            _membership(space_id, actor.id, SpaceRole.VIEWER)
        ]

        with pytest.raises(PermissionError):
            await svc.change_role(actor, space_id, uuid.uuid4(), SpaceRole.EDITOR)

    @pytest.mark.asyncio
    async def test_last_admin_guard_blocks_demotion(self):
        svc, repo, _ = _make_service()
        space_id = uuid.uuid4()
        actor = _user()
        target_id = uuid.uuid4()

        repo.list_by_space.return_value = [
            _membership(space_id, actor.id, SpaceRole.ADMIN),
            _membership(space_id, target_id, SpaceRole.ADMIN),
        ]
        repo.count_admins.return_value = 1

        with pytest.raises(ValueError, match="last admin"):
            await svc.change_role(actor, space_id, target_id, SpaceRole.EDITOR)

    @pytest.mark.asyncio
    async def test_demotion_allowed_when_multiple_admins(self):
        svc, repo, audit = _make_service()
        space_id = uuid.uuid4()
        actor = _user()
        target_id = uuid.uuid4()
        updated = SpaceMembership(space_id=space_id, user_id=target_id, role=SpaceRole.VIEWER)

        repo.list_by_space.return_value = [
            _membership(space_id, actor.id, SpaceRole.ADMIN),
            _membership(space_id, target_id, SpaceRole.ADMIN),
        ]
        repo.count_admins.return_value = 2
        repo.update_role.return_value = updated

        result = await svc.change_role(actor, space_id, target_id, SpaceRole.VIEWER)
        assert result.role == SpaceRole.VIEWER


class TestMembershipServiceRemove:
    @pytest.mark.asyncio
    async def test_remove_success(self):
        svc, repo, audit = _make_service()
        space_id = uuid.uuid4()
        actor = _user()
        target_id = uuid.uuid4()

        repo.list_by_space.return_value = [
            _membership(space_id, actor.id, SpaceRole.ADMIN),
            _membership(space_id, target_id, SpaceRole.EDITOR),
        ]
        repo.count_admins.return_value = 1

        await svc.remove(actor, space_id, target_id)

        repo.remove.assert_called_once_with(space_id, target_id)
        audit.append.assert_called_once()
        record: AuditRecord = audit.append.call_args[0][0]
        assert record.action == "member_removed"

    @pytest.mark.asyncio
    async def test_remove_raises_for_non_admin_actor(self):
        svc, repo, _ = _make_service()
        space_id = uuid.uuid4()
        actor = _user()

        repo.list_by_space.return_value = [
            _membership(space_id, actor.id, SpaceRole.EDITOR)
        ]

        with pytest.raises(PermissionError):
            await svc.remove(actor, space_id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_last_admin_guard_blocks_removal(self):
        svc, repo, _ = _make_service()
        space_id = uuid.uuid4()
        actor = _user()
        target_id = uuid.uuid4()

        repo.list_by_space.return_value = [
            _membership(space_id, actor.id, SpaceRole.ADMIN),
            _membership(space_id, target_id, SpaceRole.ADMIN),
        ]
        repo.count_admins.return_value = 1

        with pytest.raises(ValueError, match="last admin"):
            await svc.remove(actor, space_id, target_id)

    @pytest.mark.asyncio
    async def test_remove_non_member_raises_value_error(self):
        svc, repo, _ = _make_service()
        space_id = uuid.uuid4()
        actor = _user()
        target_id = uuid.uuid4()

        repo.list_by_space.return_value = [
            _membership(space_id, actor.id, SpaceRole.ADMIN),
        ]
        repo.count_admins.return_value = 1

        with pytest.raises(ValueError, match="not a member"):
            await svc.remove(actor, space_id, target_id)
