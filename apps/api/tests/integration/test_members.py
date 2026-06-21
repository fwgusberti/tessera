"""Integration tests: member management flows — invite, change-role, remove."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from tessera_core.domain.entities import (
    SpaceMembership,
    SpaceRole,
    User,
)


def _make_jwt_header(user_id: uuid.UUID, is_admin: bool = False) -> dict:
    from tessera_api.auth.jwt_auth import create_access_token

    token = create_access_token(user_id, "actor@example.com", is_admin)
    return {"Authorization": f"Bearer {token}"}


def _make_user(user_id: uuid.UUID | None = None, is_admin: bool = False) -> User:
    uid = user_id or uuid.uuid4()
    return User(
        id=uid,
        external_subject=f"sub-{uid}",
        email="actor@example.com",
        display_name="Actor",
        is_admin=is_admin,
    )


def _membership(space_id: uuid.UUID, user_id: uuid.UUID, role: SpaceRole) -> SpaceMembership:
    return SpaceMembership(space_id=space_id, user_id=user_id, role=role)


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


class TestInviteMemberIntegration:
    def test_admin_can_invite_member(self):
        from fastapi.testclient import TestClient

        from tessera_api.main import app

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        actor = _make_user(actor_id)
        invited_membership = _membership(space_id, target_id, SpaceRole.EDITOR).model_copy(
            update={"invited_by_user_id": actor_id}
        )

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.members.get_db") as mock_get_db,
                patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
                patch(
                    "tessera_api.routers.members.SqlSpaceMembershipRepository"
                ) as mock_membership_repo_cls,
                patch("tessera_api.routers.members.SqlAuditRepository") as mock_audit_cls,
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_user_repo = AsyncMock()
                mock_user_repo.get_by_id.return_value = actor
                mock_user_repo_cls.return_value = mock_user_repo

                mock_membership_repo = AsyncMock()
                mock_membership_repo.list_by_space.return_value = [
                    _membership(space_id, actor_id, SpaceRole.ADMIN)
                ]
                mock_membership_repo.get.return_value = None
                mock_membership_repo.add.return_value = invited_membership
                mock_membership_repo_cls.return_value = mock_membership_repo

                mock_audit_cls.return_value = AsyncMock()

                with TestClient(app) as client:
                    resp = client.post(
                        f"/v1/spaces/{space_id}/members",
                        json={"user_id": str(target_id), "role": "editor"},
                        headers=_make_jwt_header(actor_id),
                    )

        assert resp.status_code == 201
        data = resp.json()
        assert data["membership"]["role"] == "editor"

    def test_non_admin_cannot_invite(self):
        from fastapi.testclient import TestClient

        from tessera_api.main import app

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        actor = _make_user(actor_id)

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.members.get_db") as mock_get_db,
                patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
                patch(
                    "tessera_api.routers.members.SqlSpaceMembershipRepository"
                ) as mock_membership_repo_cls,
                patch("tessera_api.routers.members.SqlAuditRepository"),
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_user_repo = AsyncMock()
                mock_user_repo.get_by_id.return_value = actor
                mock_user_repo_cls.return_value = mock_user_repo

                mock_membership_repo = AsyncMock()
                mock_membership_repo.list_by_space.return_value = [
                    _membership(space_id, actor_id, SpaceRole.EDITOR)
                ]
                mock_membership_repo_cls.return_value = mock_membership_repo

                with TestClient(app) as client:
                    resp = client.post(
                        f"/v1/spaces/{space_id}/members",
                        json={"user_id": str(uuid.uuid4()), "role": "viewer"},
                        headers=_make_jwt_header(actor_id),
                    )

        assert resp.status_code == 403


class TestChangeRoleIntegration:
    def test_admin_can_change_role(self):
        from fastapi.testclient import TestClient

        from tessera_api.main import app

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        actor = _make_user(actor_id)
        updated = _membership(space_id, target_id, SpaceRole.EDITOR)

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.members.get_db") as mock_get_db,
                patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
                patch(
                    "tessera_api.routers.members.SqlSpaceMembershipRepository"
                ) as mock_membership_repo_cls,
                patch("tessera_api.routers.members.SqlAuditRepository") as mock_audit_cls,
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_user_repo = AsyncMock()
                mock_user_repo.get_by_id.return_value = actor
                mock_user_repo_cls.return_value = mock_user_repo

                mock_membership_repo = AsyncMock()
                mock_membership_repo.list_by_space.return_value = [
                    _membership(space_id, actor_id, SpaceRole.ADMIN),
                    _membership(space_id, target_id, SpaceRole.VIEWER),
                ]
                mock_membership_repo.count_admins.return_value = 2
                mock_membership_repo.update_role.return_value = updated
                mock_membership_repo_cls.return_value = mock_membership_repo

                mock_audit_cls.return_value = AsyncMock()

                with TestClient(app) as client:
                    resp = client.put(
                        f"/v1/spaces/{space_id}/members/{target_id}",
                        json={"role": "editor"},
                        headers=_make_jwt_header(actor_id),
                    )

        assert resp.status_code == 200
        assert resp.json()["membership"]["role"] == "editor"

    def test_last_admin_guard_returns_409(self):
        from fastapi.testclient import TestClient

        from tessera_api.main import app

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        actor = _make_user(actor_id)

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.members.get_db") as mock_get_db,
                patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
                patch(
                    "tessera_api.routers.members.SqlSpaceMembershipRepository"
                ) as mock_membership_repo_cls,
                patch("tessera_api.routers.members.SqlAuditRepository"),
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_user_repo = AsyncMock()
                mock_user_repo.get_by_id.return_value = actor
                mock_user_repo_cls.return_value = mock_user_repo

                mock_membership_repo = AsyncMock()
                mock_membership_repo.list_by_space.return_value = [
                    _membership(space_id, actor_id, SpaceRole.ADMIN),
                    _membership(space_id, target_id, SpaceRole.ADMIN),
                ]
                mock_membership_repo.count_admins.return_value = 1
                mock_membership_repo_cls.return_value = mock_membership_repo

                with TestClient(app) as client:
                    resp = client.put(
                        f"/v1/spaces/{space_id}/members/{target_id}",
                        json={"role": "viewer"},
                        headers=_make_jwt_header(actor_id),
                    )

        assert resp.status_code == 409


class TestRemoveMemberIntegration:
    def test_admin_can_remove_member(self):
        from fastapi.testclient import TestClient

        from tessera_api.main import app

        space_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        target_id = uuid.uuid4()
        actor = _make_user(actor_id)

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.members.get_db") as mock_get_db,
                patch("tessera_api.routers.members.SqlUserRepository") as mock_user_repo_cls,
                patch(
                    "tessera_api.routers.members.SqlSpaceMembershipRepository"
                ) as mock_membership_repo_cls,
                patch("tessera_api.routers.members.SqlAuditRepository") as mock_audit_cls,
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_user_repo = AsyncMock()
                mock_user_repo.get_by_id.return_value = actor
                mock_user_repo_cls.return_value = mock_user_repo

                mock_membership_repo = AsyncMock()
                mock_membership_repo.list_by_space.return_value = [
                    _membership(space_id, actor_id, SpaceRole.ADMIN),
                    _membership(space_id, target_id, SpaceRole.EDITOR),
                ]
                mock_membership_repo.count_admins.return_value = 1
                mock_membership_repo.remove.return_value = None
                mock_membership_repo_cls.return_value = mock_membership_repo

                mock_audit_cls.return_value = AsyncMock()

                with TestClient(app) as client:
                    resp = client.delete(
                        f"/v1/spaces/{space_id}/members/{target_id}",
                        headers=_make_jwt_header(actor_id),
                    )

        assert resp.status_code == 204
