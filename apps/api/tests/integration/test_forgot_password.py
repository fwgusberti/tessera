"""Integration tests for POST /v1/auth/forgot-password."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from tessera_api.main import app


def _make_user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = "carol@example.com"
    return u


def _within_limit():
    return patch(
        "tessera_api.auth.rate_limit.check_rate_limit",
        new=AsyncMock(return_value=True),
    )


class TestForgotPasswordIntegration:
    def _common_patches(self, user: MagicMock):
        mock_get_db = MagicMock()
        mock_session = AsyncMock()
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email = AsyncMock(return_value=user)

        mock_prt_repo = AsyncMock()
        mock_prt_repo.create = AsyncMock(return_value=MagicMock())

        return mock_get_db, mock_user_repo, mock_prt_repo

    def test_new_token_created_for_registered_email(self):
        user = _make_user()
        mock_get_db, mock_user_repo, mock_prt_repo = self._common_patches(user)

        with (
            _within_limit(),
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
                client.post("/v1/auth/forgot-password", json={"email": "carol@example.com"})

        mock_prt_repo.create.assert_called_once()

    def test_email_sent_for_registered_email(self):
        user = _make_user()
        mock_get_db, mock_user_repo, mock_prt_repo = self._common_patches(user)

        with (
            _within_limit(),
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
                client.post("/v1/auth/forgot-password", json={"email": "carol@example.com"})

        mock_email.send_password_reset.assert_called_once()
        call_kwargs = mock_email.send_password_reset.call_args.kwargs
        assert call_kwargs["to"] == user.email
        assert "/reset-password?token=" in call_kwargs["reset_url"]

    def test_no_email_sent_for_unregistered(self):
        mock_get_db = MagicMock()
        mock_session = AsyncMock()
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email = AsyncMock(return_value=None)

        with (
            _within_limit(),
            patch("tessera_api.routers.auth.get_db", mock_get_db),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=mock_user_repo),
            patch("tessera_api.adapters.email.FastMailEmailAdapter") as mock_email_cls,
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            mock_email = AsyncMock()
            mock_email.send_password_reset = AsyncMock()
            mock_email_cls.return_value = mock_email

            with TestClient(app) as client:
                client.post("/v1/auth/forgot-password", json={"email": "nobody@nowhere.invalid"})

        mock_email.send_password_reset.assert_not_called()

    def test_audit_record_written_for_registered_email(self):
        user = _make_user()
        mock_get_db, mock_user_repo, mock_prt_repo = self._common_patches(user)
        write_audit_mock = AsyncMock()

        with (
            _within_limit(),
            patch("tessera_api.routers.auth.get_db", mock_get_db),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=mock_user_repo),
            patch("tessera_api.routers.auth.SqlPasswordResetTokenRepository", return_value=mock_prt_repo),
            patch("tessera_api.adapters.email.FastMailEmailAdapter") as mock_email_cls,
            patch("tessera_api.routers.auth.write_audit", write_audit_mock),
        ):
            mock_email = AsyncMock()
            mock_email.send_password_reset = AsyncMock()
            mock_email_cls.return_value = mock_email

            with TestClient(app) as client:
                client.post("/v1/auth/forgot-password", json={"email": "carol@example.com"})

        write_audit_mock.assert_called_once()
        assert write_audit_mock.call_args.kwargs["action"] == "auth.password.reset_requested"
