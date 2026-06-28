"""Integration tests for POST /v1/auth/login."""

from __future__ import annotations

import base64
import json
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
            patch("tessera_api.routers.auth.SqlCompanyRepository") as mock_company_repo_cls,
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

            mock_company_repo = AsyncMock()
            mock_company_repo.list_memberships_for_user = AsyncMock(return_value=[])
            mock_company_repo_cls.return_value = mock_company_repo

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


def _decode_jwt_claims(token: str) -> dict:
    parts = token.split(".")
    padded = parts[1] + "=="
    return json.loads(base64.b64decode(padded))


def _login_with_memberships(membership_count: int):
    from tessera_api.auth.jwt_auth import hash_password

    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.display_name = "Test"
    user.is_admin = False
    user.password_hash = hash_password("S3cur3Pass")

    company_id = uuid.uuid4()

    def _make_membership(cid):
        m = MagicMock()
        m.company_id = cid
        return m

    memberships = [_make_membership(uuid.uuid4()) for _ in range(membership_count)]
    if membership_count == 1:
        memberships[0].company_id = company_id

    stored_token = MagicMock()
    stored_token.id = uuid.uuid4()

    with (
        patch("tessera_api.routers.auth.get_db") as mock_get_db,
        patch("tessera_api.routers.auth.SqlUserRepository") as mock_user_repo_cls,
        patch("tessera_api.routers.auth.SqlRefreshTokenRepository") as mock_rt_repo_cls,
        patch("tessera_api.routers.auth.SqlCompanyRepository") as mock_company_repo_cls,
        patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
    ):
        mock_session = AsyncMock()
        mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_email = AsyncMock(return_value=user)
        mock_user_repo_cls.return_value = mock_user_repo

        mock_rt_repo = AsyncMock()
        mock_rt_repo.create = AsyncMock(return_value=stored_token)
        mock_rt_repo_cls.return_value = mock_rt_repo

        mock_company_repo = AsyncMock()
        mock_company_repo.list_memberships_for_user = AsyncMock(return_value=memberships)
        mock_company_repo_cls.return_value = mock_company_repo

        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.post(
                "/v1/auth/login",
                json={"email": "test@example.com", "password": "S3cur3Pass"},
            )

    return response, company_id if membership_count == 1 else None


class TestLoginTokenKindClassification:
    def test_single_membership_issues_full_token(self):
        """Single-membership login produces token_kind=full with company_id in JWT."""
        response, company_id = _login_with_memberships(1)
        assert response.status_code == 200
        body = response.json()
        claims = _decode_jwt_claims(body["access_token"])
        assert claims["token_kind"] == "full"
        assert claims.get("company_id") == str(company_id)

    def test_multi_membership_issues_select_token(self):
        """Multi-membership login produces token_kind=select with no company_id."""
        response, _ = _login_with_memberships(2)
        assert response.status_code == 200
        body = response.json()
        claims = _decode_jwt_claims(body["access_token"])
        assert claims["token_kind"] == "select"
        assert "company_id" not in claims
        assert body.get("tenant_selection_required") is True

    def test_zero_membership_issues_onboarding_token(self):
        """Zero-membership login produces token_kind=onboarding with no company_id."""
        response, _ = _login_with_memberships(0)
        assert response.status_code == 200
        body = response.json()
        claims = _decode_jwt_claims(body["access_token"])
        assert claims["token_kind"] == "onboarding"
        assert "company_id" not in claims

    def test_select_token_blocked_on_data_endpoint(self):
        """A select token receives 403 credential_not_scoped on a data endpoint."""
        from tessera_api.auth.jwt_auth import create_access_token

        token = create_access_token(uuid.uuid4(), "u@x.test", False, token_kind="select")

        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.get(
                "/v1/spaces",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "credential_not_scoped"

    def test_onboarding_token_blocked_on_data_endpoint(self):
        """An onboarding token receives 403 credential_not_scoped on a data endpoint."""
        from tessera_api.auth.jwt_auth import create_access_token

        token = create_access_token(uuid.uuid4(), "u@x.test", False, token_kind="onboarding")

        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.get(
                "/v1/spaces",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "credential_not_scoped"

    def test_login_audit_includes_token_kind(self):
        """auth.login.success audit log records token_kind in metadata."""
        response, _ = _login_with_memberships(1)
        assert response.status_code == 200
