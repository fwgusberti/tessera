"""Contract tests for POST /v1/auth/change-password."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from tessera_api.main import app


def _make_user(password: str = "OldPass99!") -> MagicMock:
    from tessera_api.auth.jwt_auth import hash_password

    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "alice@example.com"
    user.is_admin = False
    user.password_hash = hash_password(password)
    return user


def _access_token(user: MagicMock) -> str:
    from tessera_api.auth.jwt_auth import create_access_token

    return create_access_token(user.id, user.email, user.is_admin)


def _patch_db(user: MagicMock, rt_hash: str = "deadbeef"):
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

    return mock_get_db, mock_session, mock_user_repo, mock_rt_repo


class TestChangePasswordContract:
    def test_success_returns_200_with_new_tokens(self):
        user = _make_user()
        access_token = _access_token(user)
        mock_get_db, mock_session, mock_user_repo, mock_rt_repo = _patch_db(user)

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
                        "refresh_token": "raw_refresh_token",
                    },
                )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    def test_wrong_current_password_returns_401(self):
        user = _make_user("OldPass99!")
        access_token = _access_token(user)
        mock_get_db, mock_session, mock_user_repo, mock_rt_repo = _patch_db(user)

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
                        "current_password": "WrongPass!",
                        "new_password": "NewPass88!",
                        "confirm_new_password": "NewPass88!",
                        "refresh_token": "raw_refresh_token",
                    },
                )

        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "invalid_credentials"

    def test_password_mismatch_returns_400(self):
        user = _make_user()
        access_token = _access_token(user)
        mock_get_db, _, mock_user_repo, mock_rt_repo = _patch_db(user)

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
                        "confirm_new_password": "DifferentPass!",
                        "refresh_token": "raw_refresh_token",
                    },
                )

        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "password_mismatch"

    def test_weak_new_password_returns_400(self):
        user = _make_user()
        access_token = _access_token(user)
        mock_get_db, _, mock_user_repo, mock_rt_repo = _patch_db(user)

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
                        "new_password": "password",
                        "confirm_new_password": "password",
                        "refresh_token": "raw_refresh_token",
                    },
                )

        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "password_too_weak"

    def test_missing_auth_returns_401(self):
        with TestClient(app) as client:
            resp = client.post(
                "/v1/auth/change-password",
                json={
                    "current_password": "OldPass99!",
                    "new_password": "NewPass88!",
                    "confirm_new_password": "NewPass88!",
                    "refresh_token": "raw_refresh_token",
                },
            )
        assert resp.status_code == 401
