"""Integration tests for company management endpoints."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from tessera_core.domain.entities import (
    Company,
    CompanyMembership,
    CompanyRole,
    DomainJoinPolicy,
    DomainPolicy,
    Invitation,
    InvitationStatus,
    JoinRequest,
    JoinRequestStatus,
    OnboardingProgress,
)


@contextmanager
def _bypass_onboarding_guard():
    """Override require_onboarding_complete to bypass DB check in tests."""
    from tessera_api.auth.bearer import require_onboarding_complete
    from tessera_api.main import app

    async def _noop():
        return None

    app.dependency_overrides[require_onboarding_complete] = _noop
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_onboarding_complete, None)


def _make_jwt_header(user_id: uuid.UUID | None = None, email: str = "user@acme.com") -> dict:
    from tessera_api.auth.jwt_auth import create_access_token

    uid = user_id or uuid.uuid4()
    token = create_access_token(uid, email, False)
    return {"Authorization": f"Bearer {token}"}


def _make_progress(user_id: uuid.UUID) -> OnboardingProgress:
    return OnboardingProgress(
        id=uuid.uuid4(),
        user_id=user_id,
        completed_steps=["profile"],
        current_step="company",
        company_join_method=None,
        completed_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _db_mock(mock_session: AsyncMock):
    mock_get_db = MagicMock()
    mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_get_db


class TestCreateCompany:
    def test_create_company_returns_201(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)

        company = Company(
            id=company_id, name="Acme Corp", admin_user_id=user_id,
            created_at=now, updated_at=now,
        )
        membership = CompanyMembership(
            id=uuid.uuid4(), user_id=user_id, company_id=company_id,
            role=CompanyRole.ADMIN, joined_at=now,
        )
        progress = _make_progress(user_id)

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.companies.get_db") as mock_get_db,
                patch("tessera_api.routers.companies.SqlCompanyRepository") as mock_company_cls,
                patch("tessera_api.routers.companies.SqlOnboardingRepository") as mock_ob_cls,
                patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_company = AsyncMock()
                mock_company.create = AsyncMock(return_value=company)
                mock_company.add_membership = AsyncMock(return_value=membership)
                mock_company_cls.return_value = mock_company

                mock_ob = AsyncMock()
                mock_ob.advance_step = AsyncMock(return_value=progress)
                mock_ob_cls.return_value = mock_ob

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        "/v1/companies",
                        json={"name": "Acme Corp", "industry": "Technology", "team_size": "11-50"},
                        headers=_make_jwt_header(user_id),
                    )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Acme Corp"
        assert body["role"] == "admin"

    def test_create_company_name_required(self):
        user_id = uuid.uuid4()

        with _bypass_onboarding_guard():
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/companies",
                    json={"industry": "Tech"},
                    headers=_make_jwt_header(user_id),
                )
        assert response.status_code == 422

    def test_create_company_requires_auth(self):
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.post("/v1/companies", json={"name": "Test"})
        assert response.status_code == 401


class TestGetSuggestions:
    def test_returns_empty_when_no_matches(self):
        user_id = uuid.uuid4()

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.companies.get_db") as mock_get_db,
                patch("tessera_api.routers.companies.SqlInvitationRepository") as mock_inv_cls,
                patch("tessera_api.routers.companies.SqlCompanyRepository") as mock_company_cls,
                patch("tessera_api.routers.companies.SqlDomainPolicyRepository") as mock_domain_cls,
                patch("tessera_api.routers.companies.SqlUserRepository") as mock_user_cls,
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_inv = AsyncMock()
                mock_inv.get_pending_for_email = AsyncMock(return_value=[])
                mock_inv_cls.return_value = mock_inv

                mock_domain = AsyncMock()
                mock_domain.get_by_domain = AsyncMock(return_value=None)
                mock_domain_cls.return_value = mock_domain

                mock_company_cls.return_value = AsyncMock()
                mock_user_cls.return_value = AsyncMock()

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.get(
                        "/v1/companies/suggestions",
                        headers=_make_jwt_header(user_id),
                    )

        assert response.status_code == 200
        body = response.json()
        assert body["invitations"] == []
        assert body["domain_matches"] == []


class TestJoinCompany:
    def test_join_via_invitation_returns_joined(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        invitation_id = uuid.uuid4()
        now = datetime.now(UTC)

        company = Company(
            id=company_id, name="Acme Corp", admin_user_id=uuid.uuid4(),
            created_at=now, updated_at=now,
        )
        invitation = Invitation(
            id=invitation_id,
            company_id=company_id,
            email="user@acme.com",
            token_hash="somehash",
            status=InvitationStatus.PENDING,
            expires_at=now + timedelta(days=7),
            created_at=now,
        )
        membership = CompanyMembership(
            id=uuid.uuid4(), user_id=user_id, company_id=company_id,
            role=CompanyRole.MEMBER, joined_at=now,
        )
        progress = _make_progress(user_id)

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.companies.get_db") as mock_get_db,
                patch("tessera_api.routers.companies.SqlCompanyRepository") as mock_company_cls,
                patch("tessera_api.routers.companies.SqlInvitationRepository") as mock_inv_cls,
                patch("tessera_api.routers.companies.SqlOnboardingRepository") as mock_ob_cls,
                patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_company = AsyncMock()
                mock_company.get_by_id = AsyncMock(return_value=company)
                mock_company.get_membership = AsyncMock(return_value=None)
                mock_company.add_membership = AsyncMock(return_value=membership)
                mock_company_cls.return_value = mock_company

                mock_inv = AsyncMock()
                mock_inv.get_by_id = AsyncMock(return_value=invitation)
                mock_inv.update_status = AsyncMock(return_value=invitation)
                mock_inv_cls.return_value = mock_inv

                mock_ob = AsyncMock()
                mock_ob.advance_step = AsyncMock(return_value=progress)
                mock_ob_cls.return_value = mock_ob

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        f"/v1/companies/{company_id}/join",
                        json={"method": "invitation", "invitation_id": str(invitation_id)},
                        headers=_make_jwt_header(user_id),
                    )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "joined"
        assert body["company_name"] == "Acme Corp"

    def test_company_not_found_returns_404(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.companies.get_db") as mock_get_db,
                patch("tessera_api.routers.companies.SqlCompanyRepository") as mock_company_cls,
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_company = AsyncMock()
                mock_company.get_by_id = AsyncMock(return_value=None)
                mock_company_cls.return_value = mock_company

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        f"/v1/companies/{company_id}/join",
                        json={"method": "invitation", "invitation_id": str(uuid.uuid4())},
                        headers=_make_jwt_header(user_id),
                    )

        assert response.status_code == 404


class TestJoinStatus:
    def test_returns_pending_status(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)

        company = Company(
            id=company_id, name="Acme Corp", admin_user_id=uuid.uuid4(),
            created_at=now, updated_at=now,
        )
        join_req = JoinRequest(
            id=uuid.uuid4(), user_id=user_id, company_id=company_id,
            status=JoinRequestStatus.PENDING, requested_at=now,
        )

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.companies.get_db") as mock_get_db,
                patch("tessera_api.routers.companies.SqlJoinRequestRepository") as mock_jr_cls,
                patch("tessera_api.routers.companies.SqlCompanyRepository") as mock_company_cls,
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_company = AsyncMock()
                mock_company.get_by_id = AsyncMock(return_value=company)
                mock_company_cls.return_value = mock_company

                mock_jr = AsyncMock()
                mock_jr.get_by_user_and_company = AsyncMock(return_value=join_req)
                mock_jr_cls.return_value = mock_jr

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.get(
                        f"/v1/companies/{company_id}/join-status",
                        headers=_make_jwt_header(user_id),
                    )

        assert response.status_code == 200
        assert response.json()["status"] == "pending"


class TestCORSPreflight:
    def test_options_preflight_returns_explicit_origin(self):
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            # Allowed origin should get credentials header
            allowed = client.options(
                "/v1/companies",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type,authorization",
                },
            )
            # Unauthorized origin must NOT receive access-control-allow-origin
            disallowed = client.options(
                "/v1/companies",
                headers={
                    "Origin": "http://evil.com",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type,authorization",
                },
            )

        assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert allowed.headers.get("access-control-allow-credentials") == "true"
        assert disallowed.headers.get("access-control-allow-origin") is None


class TestCancelJoinRequest:
    def test_cancel_returns_204(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()

        join_req = JoinRequest(
            id=uuid.uuid4(), user_id=user_id, company_id=company_id,
            status=JoinRequestStatus.PENDING,
        )

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.companies.get_db") as mock_get_db,
                patch("tessera_api.routers.companies.SqlJoinRequestRepository") as mock_jr_cls,
                patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_jr = AsyncMock()
                mock_jr.get_by_user_and_company = AsyncMock(return_value=join_req)
                mock_jr.cancel = AsyncMock(return_value=None)
                mock_jr_cls.return_value = mock_jr

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.delete(
                        f"/v1/companies/{company_id}/join-request",
                        headers=_make_jwt_header(user_id),
                    )

        assert response.status_code == 204


class TestGetMyCompaniesContract:
    def test_returns_200_with_company_list_shape(self):
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)

        company = Company(id=company_id, name="Acme Corp", admin_user_id=user_id, created_at=now)
        membership = CompanyMembership(
            id=uuid.uuid4(), user_id=user_id, company_id=company_id, role=CompanyRole.ADMIN
        )

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.companies.get_db") as mock_get_db,
                patch("tessera_api.routers.companies.SqlCompanyRepository") as mock_repo_cls,
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_repo = AsyncMock()
                mock_repo.list_memberships_for_user = AsyncMock(return_value=[membership])
                mock_repo.get_by_id = AsyncMock(return_value=company)
                mock_repo_cls.return_value = mock_repo

                with TestClient(app) as client:
                    response = client.get("/v1/companies/me", headers=_make_jwt_header(user_id))

        assert response.status_code == 200
        body = response.json()
        assert "companies" in body
        assert isinstance(body["companies"], list)
        entry = body["companies"][0]
        assert "id" in entry
        assert "name" in entry
        assert "role" in entry
        assert entry["role"] in ("admin", "member")

    def test_returns_401_for_unauthenticated(self):
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.get("/v1/companies/me")

        assert response.status_code == 401
