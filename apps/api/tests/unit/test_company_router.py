"""Unit tests for GET /v1/companies/me endpoint."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from tessera_core.domain.entities import Company, CompanyMembership, CompanyRole


def _make_jwt_header(user_id: uuid.UUID | None = None, email: str = "user@acme.com") -> dict:
    from tessera_api.auth.jwt_auth import create_access_token

    uid = user_id or uuid.uuid4()
    token = create_access_token(uid, email, False)
    return {"Authorization": f"Bearer {token}"}


@contextmanager
def _bypass_onboarding():
    from tessera_api.auth.bearer import require_onboarding_complete
    from tessera_api.main import app

    async def _noop():
        return None

    app.dependency_overrides[require_onboarding_complete] = _noop
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_onboarding_complete, None)


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


class TestGetMyCompanies:
    def test_authenticated_user_gets_their_companies(self):
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)

        company = Company(id=company_id, name="Acme Corp", admin_user_id=user_id, created_at=now)
        membership = CompanyMembership(
            id=uuid.uuid4(),
            user_id=user_id,
            company_id=company_id,
            role=CompanyRole.ADMIN,
        )

        mock_repo = AsyncMock()
        mock_repo.list_memberships_for_user = AsyncMock(return_value=[membership])
        mock_repo.get_by_id = AsyncMock(return_value=company)

        with (
            _bypass_onboarding(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_repo),
        ):
            with TestClient(app) as client:
                response = client.get("/v1/companies/me", headers=_make_jwt_header(user_id))

        assert response.status_code == 200
        body = response.json()
        assert "companies" in body
        assert len(body["companies"]) == 1
        assert body["companies"][0]["id"] == str(company_id)
        assert body["companies"][0]["name"] == "Acme Corp"
        assert body["companies"][0]["role"] == "admin"

    def test_unauthenticated_request_returns_401(self):
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.get("/v1/companies/me")
        assert response.status_code == 401

    def test_empty_membership_returns_empty_list(self):
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        user_id = uuid.uuid4()

        mock_repo = AsyncMock()
        mock_repo.list_memberships_for_user = AsyncMock(return_value=[])

        with (
            _bypass_onboarding(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_repo),
        ):
            with TestClient(app) as client:
                response = client.get("/v1/companies/me", headers=_make_jwt_header(user_id))

        assert response.status_code == 200
        assert response.json()["companies"] == []

    def test_companies_sorted_by_name(self):
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        user_id = uuid.uuid4()
        now = datetime.now(UTC)
        id_z = uuid.uuid4()
        id_a = uuid.uuid4()

        company_z = Company(id=id_z, name="Zebra Inc", admin_user_id=user_id, created_at=now)
        company_a = Company(id=id_a, name="Acme Corp", admin_user_id=user_id, created_at=now)
        membership_z = CompanyMembership(
            id=uuid.uuid4(), user_id=user_id, company_id=id_z, role=CompanyRole.MEMBER
        )
        membership_a = CompanyMembership(
            id=uuid.uuid4(), user_id=user_id, company_id=id_a, role=CompanyRole.ADMIN
        )

        mock_repo = AsyncMock()
        mock_repo.list_memberships_for_user = AsyncMock(
            return_value=[membership_z, membership_a]
        )
        mock_repo.get_by_id = AsyncMock(
            side_effect=lambda cid: company_z if cid == id_z else company_a
        )

        with (
            _bypass_onboarding(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_repo),
        ):
            with TestClient(app) as client:
                response = client.get("/v1/companies/me", headers=_make_jwt_header(user_id))

        assert response.status_code == 200
        names = [c["name"] for c in response.json()["companies"]]
        assert names == sorted(names)
