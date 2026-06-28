"""Integration tests: PUT /users/{id}/platform-role (US3 — Global Admin governance)."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager, contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tessera_core.domain.entities import AuditRecord, SpaceMembership, SpaceRole, User


def _make_jwt_header(user_id: uuid.UUID, is_admin: bool = False) -> dict:
    from tessera_api.auth.jwt_auth import create_access_token

    token = create_access_token(user_id, "admin@example.com", is_admin)
    return {"Authorization": f"Bearer {token}"}


def _make_user(user_id: uuid.UUID | None = None, is_admin: bool = False) -> User:
    uid = user_id or uuid.uuid4()
    return User(
        id=uid,
        external_subject=f"sub-{uid}",
        email="user@example.com",
        display_name="User",
        is_admin=is_admin,
    )


def _membership(space_id: uuid.UUID, user_id: uuid.UUID, role: SpaceRole) -> SpaceMembership:
    return SpaceMembership(space_id=space_id, user_id=user_id, role=role)


@asynccontextmanager
async def _mock_db():
    yield MagicMock()


@contextmanager
def _bypass_onboarding_guard():
    from tessera_api.auth.bearer import require_onboarding_complete
    from tessera_api.main import app

    async def _noop():
        return None

    app.dependency_overrides[require_onboarding_complete] = _noop
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_onboarding_complete, None)


class TestPlatformRoleEndpoint:
    @pytest.mark.anyio
    async def test_global_admin_can_promote_user(self):
        from tessera_api.routers.admin import set_platform_role, PlatformRoleRequest

        global_admin_id = uuid.uuid4()
        target_id = uuid.uuid4()
        global_admin = _make_user(global_admin_id, is_admin=True)
        target = _make_user(target_id, is_admin=False)
        updated_target = target.model_copy(update={"is_admin": True})

        get_by_id_calls = {
            global_admin_id: global_admin,
            target_id: target,
        }

        async def _get_by_id(uid: uuid.UUID):
            return get_by_id_calls.get(uid)

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = _get_by_id
        mock_user_repo.set_admin = AsyncMock(return_value=updated_target)

        mock_audit_repo = AsyncMock()

        with (
            patch("tessera_api.routers.admin.get_db", _mock_db),
            patch("tessera_api.routers.admin.SqlUserRepository", return_value=mock_user_repo),
            patch("tessera_api.routers.admin.SqlAuditRepository", return_value=mock_audit_repo),
            patch(
                "tessera_api.routers.admin.require_user",
                new=AsyncMock(
                    return_value={
                        "id": str(global_admin_id),
                        "sub": str(global_admin_id),
                        "is_admin": True,
                    }
                ),
            ),
        ):
            body = PlatformRoleRequest(is_admin=True)
            result = await set_platform_role(target_id, body, MagicMock())

        assert result["user"]["is_admin"] is True
        mock_audit_repo.append.assert_called_once()
        record: AuditRecord = mock_audit_repo.append.call_args[0][0]
        assert record.action == "platform_role_changed"

    @pytest.mark.anyio
    async def test_non_global_admin_gets_403(self):
        from fastapi import HTTPException

        from tessera_api.routers.admin import set_platform_role, PlatformRoleRequest

        regular_user_id = uuid.uuid4()
        target_id = uuid.uuid4()
        regular_user = _make_user(regular_user_id, is_admin=False)

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=regular_user)

        with (
            patch("tessera_api.routers.admin.get_db", _mock_db),
            patch("tessera_api.routers.admin.SqlUserRepository", return_value=mock_user_repo),
            patch(
                "tessera_api.routers.admin.require_user",
                new=AsyncMock(
                    return_value={
                        "id": str(regular_user_id),
                        "sub": str(regular_user_id),
                        "is_admin": False,
                    }
                ),
            ),
        ):
            body = PlatformRoleRequest(is_admin=True)
            with pytest.raises(HTTPException) as exc_info:
                await set_platform_role(target_id, body, MagicMock())

        assert exc_info.value.status_code == 403

    @pytest.mark.anyio
    async def test_company_admin_can_access_space_members_without_membership(self):
        """A company admin (not a space member) can list members of a space in their
        own company — authority comes from the per-company admin role, not the legacy
        global flag (feature 036)."""
        from datetime import UTC, datetime

        from tessera_core.domain.entities import CompanyMembership, CompanyRole
        from tessera_api.routers.members import list_members

        company_admin_id = uuid.uuid4()
        space_id = uuid.uuid4()
        company_admin = _make_user(company_admin_id, is_admin=False)
        memberships = [_membership(space_id, uuid.uuid4(), SpaceRole.VIEWER)]

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id.return_value = company_admin

        mock_membership_repo = AsyncMock()
        mock_membership_repo.list_by_space.return_value = memberships

        caller_membership = CompanyMembership(
            id=uuid.uuid4(), user_id=company_admin_id, company_id=uuid.uuid4(),
            role=CompanyRole.ADMIN, joined_at=datetime.now(UTC),
        )

        with (
            patch("tessera_api.routers.members.get_db") as mock_get_db,
            patch("tessera_api.routers.members.SqlUserRepository") as mock_user_cls,
            patch(
                "tessera_api.routers.members.SqlSpaceMembershipRepository"
            ) as mock_membership_cls,
            patch(
                "tessera_api.routers.members.require_company_member",
                new=AsyncMock(
                    return_value=(
                        {"id": str(company_admin_id), "sub": str(company_admin_id), "is_admin": False},
                        uuid.uuid4(),
                        caller_membership,
                    )
                ),
            ),
            patch(
                "tessera_api.routers.members.validate_space_for_company",
                new=AsyncMock(return_value=None),
            ),
        ):
            session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_user_cls.return_value = mock_user_repo
            mock_membership_cls.return_value = mock_membership_repo

            result = await list_members(space_id, MagicMock())

        assert "members" in result
        assert len(result["members"]) == 1
