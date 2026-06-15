"""Integration tests for POST /v1/auth/login."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch


class TestLogin:
    def _make_login(self, email: str, password: str):
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            return client.post(
                "/v1/auth/login",
                json={"email": email, "password": password},
            )

    def _make_user_mock(self, email: str, password: str = "S3cur3Pass") -> MagicMock:
        from tessera_api.auth.jwt_auth import hash_password

        user = MagicMock()
        user.id = uuid.uuid4()
        user.email = email
        user.display_name = "Test User"
        user.is_admin = False
        user.password_hash = hash_password(password)
        return user

    def test_login_success_returns_tokens(self):
        """Valid credentials return access_token, refresh_token, token_type, expires_in."""
        user = self._make_user_mock("alice@example.com")

        with (
            patch("tessera_api.routers.auth.get_db") as mock_get_db,
            patch("tessera_api.routers.auth.SqlUserRepository") as mock_user_repo_cls,
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository") as mock_rt_repo_cls,
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_email = AsyncMock(return_value=user)
            mock_user_repo_cls.return_value = mock_user_repo

            stored_token = MagicMock()
            stored_token.id = uuid.uuid4()
            mock_rt_repo = AsyncMock()
            mock_rt_repo.create = AsyncMock(return_value=stored_token)
            mock_rt_repo_cls.return_value = mock_rt_repo

            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/auth/login",
                    json={"email": "alice@example.com", "password": "S3cur3Pass"},
                )

        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == 900

    def test_login_wrong_password_returns_401(self):
        """Wrong password returns 401 with invalid_credentials code."""
        user = self._make_user_mock("alice@example.com", password="correctpassword")

        with (
            patch("tessera_api.routers.auth.get_db") as mock_get_db,
            patch("tessera_api.routers.auth.SqlUserRepository") as mock_user_repo_cls,
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_email = AsyncMock(return_value=user)
            mock_user_repo_cls.return_value = mock_user_repo

            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/auth/login",
                    json={"email": "alice@example.com", "password": "wrongpassword"},
                )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_credentials"

    def test_login_unknown_email_returns_401(self):
        """Unknown email returns 401 with same code as wrong password (no disclosure)."""
        with (
            patch("tessera_api.routers.auth.get_db") as mock_get_db,
            patch("tessera_api.routers.auth.SqlUserRepository") as mock_user_repo_cls,
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_email = AsyncMock(return_value=None)
            mock_user_repo_cls.return_value = mock_user_repo

            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/auth/login",
                    json={"email": "ghost@example.com", "password": "anypassword"},
                )

        assert response.status_code == 401
        body = response.json()
        assert body["error"]["code"] == "invalid_credentials"

    def test_login_error_message_same_for_wrong_email_and_wrong_password(self):
        """Non-disclosure: error code is identical for wrong email vs wrong password."""
        user = self._make_user_mock("alice@example.com", password="correctpassword")

        def make_db_mock(return_user):
            mock_get_db = MagicMock()
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
            return mock_get_db, mock_session

        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with (
            patch("tessera_api.routers.auth.get_db") as mock_get_db,
            patch("tessera_api.routers.auth.SqlUserRepository") as mock_repo_cls,
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_repo = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            with TestClient(app) as client:
                mock_repo.get_by_email = AsyncMock(return_value=None)
                r1 = client.post("/v1/auth/login", json={"email": "ghost@example.com", "password": "pass"})

                mock_repo.get_by_email = AsyncMock(return_value=user)
                r2 = client.post("/v1/auth/login", json={"email": "alice@example.com", "password": "wrong"})

        assert r1.json()["error"]["code"] == r2.json()["error"]["code"]

    def test_login_user_without_password_hash_returns_401(self):
        """User created via OIDC (no password_hash) cannot log in with password."""
        user = MagicMock()
        user.id = uuid.uuid4()
        user.email = "oidc@example.com"
        user.password_hash = None

        with (
            patch("tessera_api.routers.auth.get_db") as mock_get_db,
            patch("tessera_api.routers.auth.SqlUserRepository") as mock_user_repo_cls,
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_user_repo = AsyncMock()
            mock_user_repo.get_by_email = AsyncMock(return_value=user)
            mock_user_repo_cls.return_value = mock_user_repo

            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/auth/login",
                    json={"email": "oidc@example.com", "password": "anypassword"},
                )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_credentials"
