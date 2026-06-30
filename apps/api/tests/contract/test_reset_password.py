"""Contract tests for POST /v1/auth/reset-password."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from tessera_api.main import app
from tessera_core.domain.entities import PasswordResetToken


def _make_valid_token() -> tuple[PasswordResetToken, str]:
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    prt = PasswordResetToken(
        user_id=uuid.uuid4(),
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    return prt, raw


def _make_expired_token() -> tuple[PasswordResetToken, str]:
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    prt = PasswordResetToken(
        user_id=uuid.uuid4(),
        token_hash=token_hash,
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )
    return prt, raw


def _make_user(user_id: uuid.UUID) -> MagicMock:
    u = MagicMock()
    u.id = user_id
    u.email = "user@example.com"
    return u


@contextmanager
def _with_db(mock_session=None):
    from tessera_api.adapters.database import get_db

    if mock_session is None:
        mock_session = AsyncMock()

    async def _gen():
        yield mock_session

    app.dependency_overrides[get_db] = _gen
    try:
        yield mock_session
    finally:
        app.dependency_overrides.pop(get_db, None)


class TestResetPasswordContract:
    def test_valid_token_returns_204(self):
        prt, raw = _make_valid_token()
        user = _make_user(prt.user_id)

        mock_prt_repo = AsyncMock()
        mock_prt_repo.get_by_hash = AsyncMock(return_value=prt)
        mock_prt_repo.consume_all_for_user = AsyncMock()

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=user)
        mock_user_repo.update_password_hash = AsyncMock()

        mock_rt_repo = AsyncMock()
        mock_rt_repo.revoke_all_for_user = AsyncMock()

        with (
            _with_db(),
            patch("tessera_api.routers.auth.SqlPasswordResetTokenRepository", return_value=mock_prt_repo),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=mock_user_repo),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=mock_rt_repo),
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            with TestClient(app) as client:
                resp = client.post(
                    "/v1/auth/reset-password",
                    json={"token": raw, "new_password": "NewSecure99", "confirm_new_password": "NewSecure99"},
                )

        assert resp.status_code == 204

    def test_expired_token_returns_400(self):
        prt, raw = _make_expired_token()

        mock_prt_repo = AsyncMock()
        mock_prt_repo.get_by_hash = AsyncMock(return_value=prt)

        with (
            _with_db(),
            patch("tessera_api.routers.auth.SqlPasswordResetTokenRepository", return_value=mock_prt_repo),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=AsyncMock()),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=AsyncMock()),
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            with TestClient(app) as client:
                resp = client.post(
                    "/v1/auth/reset-password",
                    json={"token": raw, "new_password": "NewSecure99", "confirm_new_password": "NewSecure99"},
                )

        assert resp.status_code == 400

    def test_unknown_token_returns_400(self):
        mock_prt_repo = AsyncMock()
        mock_prt_repo.get_by_hash = AsyncMock(return_value=None)

        with (
            _with_db(),
            patch("tessera_api.routers.auth.SqlPasswordResetTokenRepository", return_value=mock_prt_repo),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=AsyncMock()),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=AsyncMock()),
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            with TestClient(app) as client:
                resp = client.post(
                    "/v1/auth/reset-password",
                    json={"token": "garbage", "new_password": "NewSecure99", "confirm_new_password": "NewSecure99"},
                )

        assert resp.status_code == 400

    def test_password_mismatch_returns_400(self):
        prt, raw = _make_valid_token()

        with (
            _with_db(),
            patch("tessera_api.routers.auth.SqlPasswordResetTokenRepository", return_value=AsyncMock()),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=AsyncMock()),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=AsyncMock()),
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            with TestClient(app) as client:
                resp = client.post(
                    "/v1/auth/reset-password",
                    json={"token": raw, "new_password": "NewSecure99", "confirm_new_password": "Different999"},
                )

        assert resp.status_code == 400

    def test_weak_password_returns_400(self):
        prt, raw = _make_valid_token()

        with (
            _with_db(),
            patch("tessera_api.routers.auth.SqlPasswordResetTokenRepository", return_value=AsyncMock()),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=AsyncMock()),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=AsyncMock()),
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            with TestClient(app) as client:
                resp = client.post(
                    "/v1/auth/reset-password",
                    json={"token": raw, "new_password": "password", "confirm_new_password": "password"},
                )

        assert resp.status_code == 400
