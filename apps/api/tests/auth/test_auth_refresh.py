"""Integration tests for POST /v1/auth/refresh."""

from __future__ import annotations

import base64
import json
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
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


def _decode_jwt_claims(token: str) -> dict:
    parts = token.split(".")
    padded = parts[1] + "=="
    return json.loads(base64.b64decode(padded))


def _make_stored_token(
    raw: str,
    user_id: uuid.UUID,
    expired: bool = False,
    company_id: uuid.UUID | None = None,
    token_kind: str = "full",
) -> MagicMock:
    from tessera_api.auth.jwt_auth import hash_refresh_token

    token = MagicMock()
    token.id = uuid.uuid4()
    token.user_id = user_id
    token.token_hash = hash_refresh_token(raw)
    token.is_revoked = False
    token.company_id = company_id
    token.token_kind = token_kind
    if expired:
        token.expires_at = datetime(2000, 1, 1, tzinfo=UTC)
    else:
        token.expires_at = datetime.now(UTC) + timedelta(days=7)
    return token


def _make_user(user_id: uuid.UUID) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.email = "alice@example.com"
    user.is_admin = False
    return user


class TestRefresh:
    def _call_refresh(self, refresh_token: str):
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            return client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})

    def test_valid_refresh_returns_new_tokens(self):
        """Valid refresh token returns new access_token and new refresh_token."""
        from tessera_api.auth.jwt_auth import create_refresh_token

        raw = create_refresh_token()
        user_id = uuid.uuid4()
        stored = _make_stored_token(raw, user_id)
        user = _make_user(user_id)
        new_token = MagicMock()
        new_token.id = uuid.uuid4()

        mock_rt = AsyncMock()
        mock_rt.get_by_hash = AsyncMock(return_value=stored)
        mock_rt.revoke = AsyncMock()
        mock_rt.create = AsyncMock(return_value=new_token)

        mock_user = AsyncMock()
        mock_user.get_by_id = AsyncMock(return_value=user)

        with (
            _with_db(),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=mock_rt),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=mock_user),
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post("/v1/auth/refresh", json={"refresh_token": raw})

        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["refresh_token"] != raw

    def test_old_token_revoked_after_refresh(self):
        """After refresh, the old refresh token's revoke method is called."""
        from tessera_api.auth.jwt_auth import create_refresh_token, hash_refresh_token

        raw = create_refresh_token()
        user_id = uuid.uuid4()
        stored = _make_stored_token(raw, user_id)
        user = _make_user(user_id)
        new_token = MagicMock()
        new_token.id = uuid.uuid4()

        mock_rt = AsyncMock()
        mock_rt.get_by_hash = AsyncMock(return_value=stored)
        mock_rt.revoke = AsyncMock()
        mock_rt.create = AsyncMock(return_value=new_token)

        mock_user = AsyncMock()
        mock_user.get_by_id = AsyncMock(return_value=user)

        with (
            _with_db(),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=mock_rt),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=mock_user),
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                client.post("/v1/auth/refresh", json={"refresh_token": raw})

            expected_hash = hash_refresh_token(raw)
            mock_rt.revoke.assert_called_once_with(expected_hash)

    def test_revoked_token_returns_401(self):
        """Already-revoked refresh token returns 401."""
        from tessera_api.auth.jwt_auth import create_refresh_token

        raw = create_refresh_token()
        user_id = uuid.uuid4()
        stored = _make_stored_token(raw, user_id)
        stored.is_revoked = True

        mock_rt = AsyncMock()
        mock_rt.get_by_hash = AsyncMock(return_value=stored)

        with (
            _with_db(),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=mock_rt),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post("/v1/auth/refresh", json={"refresh_token": raw})

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_refresh_token"

    def test_unknown_token_returns_401(self):
        """Token not found in database returns 401."""
        from tessera_api.auth.jwt_auth import create_refresh_token

        raw = create_refresh_token()

        mock_rt = AsyncMock()
        mock_rt.get_by_hash = AsyncMock(return_value=None)

        with (
            _with_db(),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=mock_rt),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post("/v1/auth/refresh", json={"refresh_token": raw})

        assert response.status_code == 401

    def test_expired_token_returns_401(self):
        """Expired refresh token returns 401."""
        from tessera_api.auth.jwt_auth import create_refresh_token

        raw = create_refresh_token()
        user_id = uuid.uuid4()
        stored = _make_stored_token(raw, user_id, expired=True)

        mock_rt = AsyncMock()
        mock_rt.get_by_hash = AsyncMock(return_value=stored)

        with (
            _with_db(),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=mock_rt),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post("/v1/auth/refresh", json={"refresh_token": raw})

        assert response.status_code == 401


class TestRefreshScopePreservation:
    def _call_refresh(self, raw: str, stored_token: MagicMock, user: MagicMock) -> dict:
        new_token = MagicMock()
        new_token.id = uuid.uuid4()

        mock_rt = AsyncMock()
        mock_rt.get_by_hash = AsyncMock(return_value=stored_token)
        mock_rt.revoke = AsyncMock()
        mock_rt.create = AsyncMock(return_value=new_token)

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=user)

        with (
            _with_db(),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=mock_rt),
            patch("tessera_api.routers.auth.SqlUserRepository", return_value=mock_user_repo),
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post("/v1/auth/refresh", json={"refresh_token": raw})

        return response

    def test_refresh_full_token_preserves_company_id(self):
        """Refreshing a full-scoped token issues a new access token with same company_id."""
        from tessera_api.auth.jwt_auth import create_refresh_token

        raw = create_refresh_token()
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        stored = _make_stored_token(raw, user_id, company_id=company_id, token_kind="full")
        user = _make_user(user_id)

        response = self._call_refresh(raw, stored, user)

        assert response.status_code == 200
        claims = _decode_jwt_claims(response.json()["access_token"])
        assert claims["token_kind"] == "full"
        assert claims.get("company_id") == str(company_id)

    def test_refresh_select_token_preserves_select_kind(self):
        """Refreshing a select token issues a new access token with token_kind=select and no company_id."""
        from tessera_api.auth.jwt_auth import create_refresh_token

        raw = create_refresh_token()
        user_id = uuid.uuid4()
        stored = _make_stored_token(raw, user_id, company_id=None, token_kind="select")
        user = _make_user(user_id)

        response = self._call_refresh(raw, stored, user)

        assert response.status_code == 200
        claims = _decode_jwt_claims(response.json()["access_token"])
        assert claims["token_kind"] == "select"
        assert "company_id" not in claims

    def test_refresh_onboarding_token_preserves_onboarding_kind(self):
        """Refreshing an onboarding token preserves the onboarding kind and no company_id."""
        from tessera_api.auth.jwt_auth import create_refresh_token

        raw = create_refresh_token()
        user_id = uuid.uuid4()
        stored = _make_stored_token(raw, user_id, company_id=None, token_kind="onboarding")
        user = _make_user(user_id)

        response = self._call_refresh(raw, stored, user)

        assert response.status_code == 200
        claims = _decode_jwt_claims(response.json()["access_token"])
        assert claims["token_kind"] == "onboarding"
        assert "company_id" not in claims
