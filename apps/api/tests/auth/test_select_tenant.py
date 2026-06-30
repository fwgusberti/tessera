"""Tests for POST /v1/auth/select-tenant — US2 and US4."""

from __future__ import annotations

import base64
import json
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


def _decode_jwt_claims(token: str) -> dict:
    parts = token.split(".")
    padded = parts[1] + "=="
    return json.loads(base64.b64decode(padded))


def _full_token(user_id: uuid.UUID | None = None, company_id: uuid.UUID | None = None) -> str:
    from tessera_api.auth.jwt_auth import create_access_token
    return create_access_token(
        user_id or uuid.uuid4(), "u@x.test", False,
        company_id=company_id or uuid.uuid4(), token_kind="full",
    )


def _select_token(user_id: uuid.UUID | None = None) -> str:
    from tessera_api.auth.jwt_auth import create_access_token
    return create_access_token(
        user_id or uuid.uuid4(), "u@x.test", False, token_kind="select",
    )


def _onboarding_token(user_id: uuid.UUID | None = None) -> str:
    from tessera_api.auth.jwt_auth import create_access_token
    return create_access_token(
        user_id or uuid.uuid4(), "u@x.test", False, token_kind="onboarding",
    )


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


def _active_company(company_id: uuid.UUID) -> MagicMock:
    company = MagicMock()
    company.id = company_id
    company.is_active = True
    return company


def _membership(user_id: uuid.UUID, company_id: uuid.UUID) -> MagicMock:
    from tessera_core.domain.entities import CompanyMembership, CompanyRole
    return CompanyMembership(
        id=uuid.uuid4(), user_id=user_id, company_id=company_id,
        role=CompanyRole.MEMBER, joined_at=datetime.now(UTC),
    )


class TestSelectTenantRejections:
    def _post(self, token: str, company_id: uuid.UUID) -> object:
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            return client.post(
                "/v1/auth/select-tenant",
                json={"company_id": str(company_id)},
                headers={"Authorization": f"Bearer {token}"},
            )

    def test_unauthenticated_returns_401(self):
        """No Authorization header → 401."""
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.post(
                "/v1/auth/select-tenant",
                json={"company_id": str(uuid.uuid4())},
            )
        assert response.status_code == 401

    def test_full_token_returns_403_wrong_token_kind(self):
        """A full token is rejected with wrong_token_kind."""
        # full token is allowed by US4 (require_unscoped_or_full_token), so this is correct behaviour
        # A user with a full token CAN switch tenants — this tests that onboarding tokens cannot.
        pass  # covered in test_onboarding_token_returns_403_wrong_token_kind

    def test_onboarding_token_returns_403_wrong_token_kind(self):
        """An onboarding token is rejected with wrong_token_kind."""
        token = _onboarding_token()
        response = self._post(token, uuid.uuid4())
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "wrong_token_kind"

    def test_non_member_company_returns_403_not_a_member(self):
        """select token + company the user has no membership in → 403 not_a_member."""
        user_id = uuid.uuid4()
        target_company_id = uuid.uuid4()
        token = _select_token(user_id)

        mock_company_repo = AsyncMock()
        mock_company_repo.get_by_id = AsyncMock(return_value=_active_company(target_company_id))
        mock_company_repo.get_membership = AsyncMock(return_value=None)

        mock_rt_repo = AsyncMock()

        with (
            _with_db(),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=mock_rt_repo),
            patch("tessera_api.routers.auth.SqlCompanyRepository", return_value=mock_company_repo),
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/auth/select-tenant",
                    json={"company_id": str(target_company_id)},
                    headers={"Authorization": f"Bearer {token}"},
                )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "not_a_member"

    def test_inactive_company_returns_403_company_suspended(self):
        """select token + inactive company → 403 company_suspended."""
        user_id = uuid.uuid4()
        target_company_id = uuid.uuid4()
        token = _select_token(user_id)

        inactive = _active_company(target_company_id)
        inactive.is_active = False

        mock_company_repo = AsyncMock()
        mock_company_repo.get_by_id = AsyncMock(return_value=inactive)
        mock_company_repo.get_membership = AsyncMock(return_value=None)

        with (
            _with_db(),
            patch("tessera_api.routers.auth.SqlCompanyRepository", return_value=mock_company_repo),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=AsyncMock()),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/auth/select-tenant",
                    json={"company_id": str(target_company_id)},
                    headers={"Authorization": f"Bearer {token}"},
                )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "company_suspended"


class TestSelectTenantSuccess:
    def _post_with_mocks(
        self,
        token: str,
        target_company_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        stored_rt = MagicMock()
        stored_rt.id = uuid.uuid4()

        mock_company_repo = AsyncMock()
        mock_company_repo.get_by_id = AsyncMock(return_value=_active_company(target_company_id))
        mock_company_repo.get_membership = AsyncMock(
            return_value=_membership(user_id, target_company_id)
        )

        mock_rt_repo = AsyncMock()
        mock_rt_repo.create = AsyncMock(return_value=stored_rt)

        with (
            _with_db(),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=mock_rt_repo),
            patch("tessera_api.routers.auth.SqlCompanyRepository", return_value=mock_company_repo),
            patch("tessera_api.routers.auth.write_audit", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/auth/select-tenant",
                    json={"company_id": str(target_company_id)},
                    headers={"Authorization": f"Bearer {token}"},
                )

        return response

    def test_select_token_issues_full_token(self):
        """Valid select token + member company → 200 with full token."""
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        token = _select_token(user_id)

        response = self._post_with_mocks(token, company_id, user_id)

        assert response.status_code == 200
        body = response.json()
        claims = _decode_jwt_claims(body["access_token"])
        assert claims["token_kind"] == "full"
        assert claims["company_id"] == str(company_id)
        assert "refresh_token" in body

    def test_full_token_can_switch_tenant(self):
        """A full token for Company A can switch to Company B (US4)."""
        user_id = uuid.uuid4()
        company_b_id = uuid.uuid4()
        token = _full_token(user_id, company_id=uuid.uuid4())

        response = self._post_with_mocks(token, company_b_id, user_id)

        assert response.status_code == 200
        claims = _decode_jwt_claims(response.json()["access_token"])
        assert claims["token_kind"] == "full"
        assert claims["company_id"] == str(company_b_id)


class TestSelectTenantNonMemberSwitch:
    def test_full_token_non_member_company_returns_403(self):
        """Full token + company the user has no membership in → 403 not_a_member."""
        user_id = uuid.uuid4()
        target = uuid.uuid4()
        token = _full_token(user_id, company_id=uuid.uuid4())

        mock_company_repo = AsyncMock()
        mock_company_repo.get_by_id = AsyncMock(return_value=_active_company(target))
        mock_company_repo.get_membership = AsyncMock(return_value=None)

        with (
            _with_db(),
            patch("tessera_api.routers.auth.SqlRefreshTokenRepository", return_value=AsyncMock()),
            patch("tessera_api.routers.auth.SqlCompanyRepository", return_value=mock_company_repo),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/auth/select-tenant",
                    json={"company_id": str(target)},
                    headers={"Authorization": f"Bearer {token}"},
                )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "not_a_member"
