"""Integration tests for POST /v1/auth/logout."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch


@contextmanager
def _with_db(mock_session=None):
    from tessera_api.adapters.database import get_db
    from tessera_api.main import app
    if mock_session is None:
        mock_session = AsyncMock()
    async def _gen():
        yield mock_session
    app.dependency_overrides[get_db] = _gen
    try:
        yield mock_session
    finally:
        app.dependency_overrides.pop(get_db, None)


def _make_valid_token(user_id: uuid.UUID | None = None) -> str:
    from tessera_api.auth.jwt_auth import create_access_token
    uid = user_id or uuid.uuid4()
    return create_access_token(uid, "test@example.com", is_admin=False)


class TestLogout:
    def test_logout_success_returns_204(self):
        """Authenticated logout with valid refresh token returns 204."""
        from tessera_api.auth.jwt_auth import create_refresh_token

        user_id = uuid.uuid4()
        access_token = _make_valid_token(user_id)
        raw_refresh = create_refresh_token()

        mock_rt = AsyncMock()
        mock_rt.delete_by_hash = AsyncMock()

        with (
            _with_db(),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=mock_rt),
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/auth/logout",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={"refresh_token": raw_refresh},
                )

        assert response.status_code == 204

    def test_logout_deletes_refresh_token(self):
        """Logout calls delete_by_hash on the provided refresh token."""
        from tessera_api.auth.jwt_auth import create_refresh_token, hash_refresh_token

        user_id = uuid.uuid4()
        access_token = _make_valid_token(user_id)
        raw_refresh = create_refresh_token()
        expected_hash = hash_refresh_token(raw_refresh)

        mock_rt = AsyncMock()
        mock_rt.delete_by_hash = AsyncMock()

        with (
            _with_db(),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=mock_rt),
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                client.post(
                    "/v1/auth/logout",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={"refresh_token": raw_refresh},
                )

            mock_rt.delete_by_hash.assert_called_once_with(expected_hash)

    def test_logout_without_token_returns_401(self):
        """Logout without an Authorization header returns 401."""
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.post(
                "/v1/auth/logout",
                json={"refresh_token": "some-token"},
            )

        assert response.status_code == 401

    def test_logout_with_invalid_token_returns_401(self):
        """Logout with a tampered access token returns 401."""
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.post(
                "/v1/auth/logout",
                headers={"Authorization": "Bearer invalidtokenXXX"},
                json={"refresh_token": "some-token"},
            )

        assert response.status_code == 401
