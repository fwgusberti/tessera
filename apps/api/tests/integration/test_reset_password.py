"""Integration tests for POST /v1/auth/reset-password."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from tessera_api.main import app
from tessera_core.domain.entities import PasswordResetToken


def _make_valid_prt() -> tuple[PasswordResetToken, str]:
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    prt = PasswordResetToken(
        user_id=uuid.uuid4(),
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    return prt, raw


def _make_user(user_id: uuid.UUID) -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.email = "user@example.com"
    return u


def _patch_db():
    mock_get_db = MagicMock()
    mock_session = AsyncMock()
    mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_get_db


class TestResetPasswordIntegration:
    def test_token_lookup_uses_sha256_hash(self):
        prt, raw = _make_valid_prt()
        user = _make_user(prt.user_id)
        mock_get_db = _patch_db()
        mock_prt_repo = AsyncMock()
        mock_prt_repo.get_by_hash = AsyncMock(return_value=prt)
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=user)
        mock_rt_repo = AsyncMock()
        mock_rt_repo.revoke_all_for_user = AsyncMock()

        with (
            patch("tessera_api.routers.auth.get_db", mock_get_db),
            patch("tessera_api.routers.auth.SqlPasswordResetTokenRepository", return_value=mock_prt_repo),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=mock_user_repo),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=mock_rt_repo),
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            with TestClient(app) as client:
                client.post(
                    "/v1/auth/reset-password",
                    json={"token": raw, "new_password": "NewSecure99", "confirm_new_password": "NewSecure99"},
                )

        expected_hash = hashlib.sha256(raw.encode()).hexdigest()
        mock_prt_repo.get_by_hash.assert_called_once_with(expected_hash)

    def test_all_sessions_revoked_on_success(self):
        prt, raw = _make_valid_prt()
        user = _make_user(prt.user_id)
        mock_get_db = _patch_db()
        mock_prt_repo = AsyncMock()
        mock_prt_repo.get_by_hash = AsyncMock(return_value=prt)
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=user)
        mock_rt_repo = AsyncMock()
        mock_rt_repo.revoke_all_for_user = AsyncMock()

        with (
            patch("tessera_api.routers.auth.get_db", mock_get_db),
            patch("tessera_api.routers.auth.SqlPasswordResetTokenRepository", return_value=mock_prt_repo),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=mock_user_repo),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=mock_rt_repo),
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            with TestClient(app) as client:
                client.post(
                    "/v1/auth/reset-password",
                    json={"token": raw, "new_password": "NewSecure99", "confirm_new_password": "NewSecure99"},
                )

        mock_rt_repo.revoke_all_for_user.assert_called_once_with(prt.user_id)

    def test_audit_record_written_on_success(self):
        prt, raw = _make_valid_prt()
        user = _make_user(prt.user_id)
        mock_get_db = _patch_db()
        mock_prt_repo = AsyncMock()
        mock_prt_repo.get_by_hash = AsyncMock(return_value=prt)
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=user)
        mock_rt_repo = AsyncMock()
        mock_rt_repo.revoke_all_for_user = AsyncMock()
        write_audit_mock = AsyncMock()

        with (
            patch("tessera_api.routers.auth.get_db", mock_get_db),
            patch("tessera_api.routers.auth.SqlPasswordResetTokenRepository", return_value=mock_prt_repo),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=mock_user_repo),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=mock_rt_repo),
            patch("tessera_api.routers.auth.write_audit", write_audit_mock),
        ):
            with TestClient(app) as client:
                client.post(
                    "/v1/auth/reset-password",
                    json={"token": raw, "new_password": "NewSecure99", "confirm_new_password": "NewSecure99"},
                )

        write_audit_mock.assert_called_once()
        assert write_audit_mock.call_args.kwargs["action"] == "auth.password.reset_completed"
