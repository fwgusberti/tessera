"""Integration tests for POST /v1/auth/register."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestRegister:
    def _make_request(self, email: str, password: str, display_name: str = "Test User") -> dict:
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            return client.post(
                "/v1/auth/register",
                json={"email": email, "password": password, "display_name": display_name},
            )

    def test_register_success_returns_201(self):
        """Valid registration returns 201 with user object."""
        import uuid
        from unittest.mock import AsyncMock, patch

        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.email = "alice@example.com"
        mock_user.display_name = "Alice"
        mock_user.is_admin = False
        mock_user.created_at = None

        with (
            patch("tessera_api.routers.auth.get_db") as mock_get_db,
            patch("tessera_api.routers.auth.SqlUserRepository") as mock_repo_cls,
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_repo = AsyncMock()
            mock_repo.get_by_email = AsyncMock(return_value=None)
            mock_repo.create = AsyncMock(return_value=mock_user)
            mock_repo_cls.return_value = mock_repo

            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/auth/register",
                    json={"email": "alice@example.com", "password": "S3cur3Pass", "display_name": "Alice"},
                )

        assert response.status_code == 201
        body = response.json()
        assert "user" in body
        assert body["user"]["email"] == "alice@example.com"

    def test_register_duplicate_email_returns_409(self):
        """Duplicate email returns 409 with email_already_registered code."""
        import uuid
        from unittest.mock import AsyncMock, patch, MagicMock

        existing_user = MagicMock()
        existing_user.id = uuid.uuid4()
        existing_user.email = "alice@example.com"

        with (
            patch("tessera_api.routers.auth.get_db") as mock_get_db,
            patch("tessera_api.routers.auth.SqlUserRepository") as mock_repo_cls,
        ):
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_repo = AsyncMock()
            mock_repo.get_by_email = AsyncMock(return_value=existing_user)
            mock_repo_cls.return_value = mock_repo

            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/auth/register",
                    json={"email": "alice@example.com", "password": "S3cur3Pass", "display_name": "Alice"},
                )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "email_already_registered"

    def test_register_short_password_returns_422(self):
        """Password shorter than 8 characters returns 422."""
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.post(
                "/v1/auth/register",
                json={"email": "bob@example.com", "password": "short", "display_name": "Bob"},
            )

        assert response.status_code == 422

    def test_register_invalid_email_returns_422(self):
        """Invalid email format returns 422."""
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.post(
                "/v1/auth/register",
                json={"email": "not-an-email", "password": "S3cur3Pass", "display_name": "Bob"},
            )

        assert response.status_code == 422
