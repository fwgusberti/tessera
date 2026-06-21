"""Contract tests for POST /v1/auth/forgot-password."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from tessera_api.main import app

_EXPECTED_BODY = {"message": "If that email is registered, you will receive a reset link shortly."}


def _make_user(email: str = "user@example.com") -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = email
    return u


def _within_limit_patch():
    return patch(
        "tessera_api.auth.rate_limit.check_rate_limit",
        new=AsyncMock(return_value=True),
    )


class TestForgotPasswordContract:
    def test_registered_email_returns_200_with_neutral_message(self):
        user = _make_user()
        mock_get_db = MagicMock()
        mock_session = AsyncMock()
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email = AsyncMock(return_value=user)
        mock_prt_repo = AsyncMock()
        mock_prt_repo.create = AsyncMock(return_value=MagicMock())

        with (
            _within_limit_patch(),
            patch("tessera_api.routers.auth.get_db", mock_get_db),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=mock_user_repo),
            patch("tessera_api.routers.auth.SqlPasswordResetTokenRepository", return_value=mock_prt_repo),
            patch("tessera_api.adapters.email.FastMailEmailAdapter") as mock_email_cls,
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            mock_email = AsyncMock()
            mock_email.send_password_reset = AsyncMock()
            mock_email_cls.return_value = mock_email
            with TestClient(app) as client:
                resp = client.post("/v1/auth/forgot-password", json={"email": "user@example.com"})

        assert resp.status_code == 200
        assert resp.json() == _EXPECTED_BODY

    def test_unregistered_email_returns_200_with_same_body(self):
        mock_get_db = MagicMock()
        mock_session = AsyncMock()
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email = AsyncMock(return_value=None)

        with (
            _within_limit_patch(),
            patch("tessera_api.routers.auth.get_db", mock_get_db),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=mock_user_repo),
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            with TestClient(app) as client:
                resp = client.post("/v1/auth/forgot-password", json={"email": "nobody@nowhere.invalid"})

        assert resp.status_code == 200
        assert resp.json() == _EXPECTED_BODY

    def test_rate_limit_exceeded_returns_200_with_same_body(self):
        with patch(
            "tessera_api.auth.rate_limit.check_rate_limit",
            new=AsyncMock(return_value=False),
        ):
            with TestClient(app) as client:
                resp = client.post("/v1/auth/forgot-password", json={"email": "user@example.com"})

        assert resp.status_code == 200
        assert resp.json() == _EXPECTED_BODY

    def test_registered_and_unregistered_bodies_are_identical(self):
        user = _make_user()
        mock_get_db = MagicMock()
        mock_session = AsyncMock()
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_user_repo = AsyncMock()

        with (
            _within_limit_patch(),
            patch("tessera_api.routers.auth.get_db", mock_get_db),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=mock_user_repo),
            patch("tessera_api.routers.auth.SqlPasswordResetTokenRepository", return_value=AsyncMock()),
            patch("tessera_api.adapters.email.FastMailEmailAdapter") as mock_email_cls,
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            mock_email = AsyncMock()
            mock_email.send_password_reset = AsyncMock()
            mock_email_cls.return_value = mock_email

            with TestClient(app) as client:
                mock_user_repo.get_by_email = AsyncMock(return_value=user)
                r1 = client.post("/v1/auth/forgot-password", json={"email": "user@example.com"})

                mock_user_repo.get_by_email = AsyncMock(return_value=None)
                r2 = client.post("/v1/auth/forgot-password", json={"email": "nobody@nowhere.invalid"})

        assert r1.json() == r2.json()
