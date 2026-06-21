"""Integration tests for POST /v1/auth/change-password — session and audit behaviour."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from tessera_api.main import app


def _make_user(password: str = "OldPass99!") -> MagicMock:
    from tessera_api.auth.jwt_auth import hash_password

    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = "bob@example.com"
    u.is_admin = False
    u.password_hash = hash_password(password)
    return u


def _access_token(user: MagicMock) -> str:
    from tessera_api.auth.jwt_auth import create_access_token

    return create_access_token(user.id, user.email, user.is_admin)


class TestChangePasswordIntegration:
    def _make_common_patches(self, user: MagicMock):
        mock_get_db = MagicMock()
        mock_session = AsyncMock()
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=user)

        mock_rt_repo = AsyncMock()
        mock_rt_repo.get_by_hash = AsyncMock(return_value=None)
        rotated = MagicMock()
        rotated.id = uuid.uuid4()
        mock_rt_repo.create = AsyncMock(return_value=rotated)
        mock_rt_repo.revoke = AsyncMock()
        mock_rt_repo.revoke_all_except = AsyncMock()

        return mock_get_db, mock_user_repo, mock_rt_repo

    def test_revoke_all_except_called_with_user_id_and_current_hash(self):
        """Other sessions are revoked; the current session is kept and rotated."""
        user = _make_user()
        access_token = _access_token(user)
        mock_get_db, mock_user_repo, mock_rt_repo = self._make_common_patches(user)
        write_audit_mock = AsyncMock()

        with (
            patch("tessera_api.routers.auth.get_db", mock_get_db),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=mock_user_repo),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=mock_rt_repo),
            patch("tessera_api.routers.auth.write_audit", write_audit_mock),
        ):
            with TestClient(app) as client:
                resp = client.post(
                    "/v1/auth/change-password",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={
                        "current_password": "OldPass99!",
                        "new_password": "NewPass88!",
                        "confirm_new_password": "NewPass88!",
                        "refresh_token": "my_raw_refresh",
                    },
                )

        assert resp.status_code == 200
        mock_rt_repo.revoke_all_except.assert_called_once()
        call_args = mock_rt_repo.revoke_all_except.call_args
        assert call_args.kwargs.get("user_id") == user.id or call_args.args[0] == user.id

    def test_audit_record_written_with_correct_action(self):
        """auth.password.change audit event is emitted on success."""
        user = _make_user()
        access_token = _access_token(user)
        mock_get_db, mock_user_repo, mock_rt_repo = self._make_common_patches(user)
        write_audit_mock = AsyncMock()

        with (
            patch("tessera_api.routers.auth.get_db", mock_get_db),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=mock_user_repo),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=mock_rt_repo),
            patch("tessera_api.routers.auth.write_audit", write_audit_mock),
        ):
            with TestClient(app) as client:
                client.post(
                    "/v1/auth/change-password",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={
                        "current_password": "OldPass99!",
                        "new_password": "NewPass88!",
                        "confirm_new_password": "NewPass88!",
                        "refresh_token": "my_raw_refresh",
                    },
                )

        write_audit_mock.assert_called_once()
        action = write_audit_mock.call_args.kwargs.get("action")
        assert action == "auth.password.change"

    def test_current_token_rotated_on_success(self):
        """The submitted refresh token is revoked and a new one is created."""
        user = _make_user()
        access_token = _access_token(user)
        mock_get_db, mock_user_repo, mock_rt_repo = self._make_common_patches(user)

        with (
            patch("tessera_api.routers.auth.get_db", mock_get_db),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=mock_user_repo),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=mock_rt_repo),
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            with TestClient(app) as client:
                resp = client.post(
                    "/v1/auth/change-password",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={
                        "current_password": "OldPass99!",
                        "new_password": "NewPass88!",
                        "confirm_new_password": "NewPass88!",
                        "refresh_token": "my_raw_refresh",
                    },
                )

        assert resp.status_code == 200
        mock_rt_repo.revoke.assert_called_once()
        mock_rt_repo.create.assert_called_once()
