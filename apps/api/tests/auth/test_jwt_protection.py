"""Integration tests: JWT bearer token grants/denies access to protected endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_valid_token(user_id: uuid.UUID | None = None) -> str:
    from tessera_api.auth.jwt_auth import create_access_token
    uid = user_id or uuid.uuid4()
    return create_access_token(uid, "test@example.com", is_admin=False)


class TestJwtProtection:
    def test_valid_jwt_grants_access(self):
        """GET /v1/spaces with valid JWT is authenticated (require_user succeeds)."""
        token = _make_valid_token()
        user_claims = {"sub": str(uuid.uuid4()), "email": "test@example.com", "is_admin": False}

        with patch("tessera_api.auth.oidc.require_user", new_callable=AsyncMock, return_value=user_claims):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                # HEAD request just checks auth, not the DB
                response = client.get(
                    "/v1/spaces",
                    headers={"Authorization": f"Bearer {token}"},
                )

        # Should not be 401 — auth passed
        assert response.status_code != 401

    def test_no_credentials_returns_401(self):
        """GET /v1/spaces with no credentials returns 401."""
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.get("/v1/spaces")

        assert response.status_code == 401

    def test_tampered_token_returns_401(self):
        """A tampered JWT token is rejected with 401."""
        token = _make_valid_token()
        bad_token = token[:-5] + "XXXXX"

        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.get(
                "/v1/spaces",
                headers={"Authorization": f"Bearer {bad_token}"},
            )

        assert response.status_code == 401

    def test_expired_token_returns_401(self):
        """An expired JWT access token is rejected with 401."""
        from unittest.mock import patch as mp

        user_id = uuid.uuid4()
        with mp("tessera_api.auth.jwt_auth.get_settings") as mock_settings:
            mock_settings.return_value.jwt_access_token_expire_minutes = -1
            mock_settings.return_value.jwt_algorithm = "HS256"
            mock_settings.return_value.secret_key = "dev-secret-key-change-in-production"
            from tessera_api.auth.jwt_auth import create_access_token
            token = create_access_token(user_id, "test@example.com", is_admin=False)

        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.get(
                "/v1/spaces",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 401
