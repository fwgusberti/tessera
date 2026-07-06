"""Integration tests for domain auto-association on company creation (US3).

TDD: written before the ``create_company`` side effect and the
``create_domain_policy`` public-domain guard exist (Constitution Principle IV).

These are router-level tests with mocked repositories, matching the style of
``test_companies.py``. They assert:
  (a) a non-public founder email creates exactly one request_approval/verified
      DomainJoinPolicy and emits a ``company.domain_auto_associated`` audit;
  (b) a public founder email creates no policy;
  (c) a founder email whose domain is already claimed returns 201 with no new
      policy;
  (d) POST .../domain-policies with a public domain returns 422
      ``public_domain_not_allowed`` and writes nothing.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.exc import IntegrityError

from tessera_core.domain.entities import (
    Company,
    CompanyMembership,
    CompanyRole,
    DomainJoinPolicy,
    DomainPolicy,
    OnboardingProgress,
)


@contextmanager
def _bypass_onboarding_guard():
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
        # begin_nested() must behave as an async context manager (savepoint used
        # by create_company's race-tolerant domain auto-association).
        mock_session.begin_nested = MagicMock(return_value=AsyncMock())

    async def _gen():
        yield mock_session

    app.dependency_overrides[get_db] = _gen
    try:
        yield mock_session
    finally:
        app.dependency_overrides.pop(get_db, None)


def _make_jwt_header(user_id: uuid.UUID, email: str) -> dict:
    from tessera_api.auth.jwt_auth import create_access_token

    token = create_access_token(user_id, email, False)
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


def _company_repo_mock(user_id: uuid.UUID, company_id: uuid.UUID, now: datetime) -> AsyncMock:
    company = Company(
        id=company_id, name="Acme Corp", admin_user_id=user_id, created_at=now, updated_at=now
    )
    membership = CompanyMembership(
        id=uuid.uuid4(),
        user_id=user_id,
        company_id=company_id,
        role=CompanyRole.ADMIN,
        joined_at=now,
    )
    repo = AsyncMock()
    repo.create = AsyncMock(return_value=company)
    repo.add_membership = AsyncMock(return_value=membership)
    return repo


def _created_policies(mock_domain: AsyncMock) -> list[DomainJoinPolicy]:
    return [call.args[0] for call in mock_domain.create.call_args_list]


def _audit_actions(mock_audit: AsyncMock) -> list[str]:
    return [call.kwargs.get("action") for call in mock_audit.call_args_list]


class TestCreateCompanyAutoAssociation:
    def test_non_public_email_creates_verified_request_approval_policy(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)

        mock_company = _company_repo_mock(user_id, company_id, now)
        mock_ob = AsyncMock()
        mock_ob.advance_step = AsyncMock(return_value=_make_progress(user_id))
        mock_domain = AsyncMock()
        mock_domain.get_by_domain = AsyncMock(return_value=None)
        mock_domain.create = AsyncMock(
            side_effect=lambda p: p.model_copy(update={"created_at": now})
        )

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company),
            patch("tessera_api.routers.companies.SqlOnboardingRepository", return_value=mock_ob),
            patch(
                "tessera_api.routers.companies.SqlDomainPolicyRepository",
                return_value=mock_domain,
            ),
            patch(
                "tessera_api.routers.companies.write_audit", new_callable=AsyncMock
            ) as mock_audit,
        ):
            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/companies",
                    json={"name": "Acme Corp"},
                    headers=_make_jwt_header(user_id, "founder@acme.example"),
                )

        assert response.status_code == 201
        policies = _created_policies(mock_domain)
        assert len(policies) == 1
        policy = policies[0]
        assert policy.domain == "acme.example"
        assert policy.policy == DomainPolicy.REQUEST_APPROVAL
        assert policy.verified is True
        assert policy.company_id == company_id
        assert "company.domain_auto_associated" in _audit_actions(mock_audit)

    def test_public_email_creates_no_policy(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)

        mock_company = _company_repo_mock(user_id, company_id, now)
        mock_ob = AsyncMock()
        mock_ob.advance_step = AsyncMock(return_value=_make_progress(user_id))
        mock_domain = AsyncMock()
        mock_domain.get_by_domain = AsyncMock(return_value=None)

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company),
            patch("tessera_api.routers.companies.SqlOnboardingRepository", return_value=mock_ob),
            patch(
                "tessera_api.routers.companies.SqlDomainPolicyRepository",
                return_value=mock_domain,
            ),
            patch(
                "tessera_api.routers.companies.write_audit", new_callable=AsyncMock
            ) as mock_audit,
        ):
            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/companies",
                    json={"name": "Acme Corp"},
                    headers=_make_jwt_header(user_id, "founder@gmail.com"),
                )

        assert response.status_code == 201
        mock_domain.create.assert_not_called()
        assert "company.domain_auto_associated" not in _audit_actions(mock_audit)

    def test_already_claimed_domain_creates_no_new_policy(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        other_company_id = uuid.uuid4()
        now = datetime.now(UTC)

        mock_company = _company_repo_mock(user_id, company_id, now)
        mock_ob = AsyncMock()
        mock_ob.advance_step = AsyncMock(return_value=_make_progress(user_id))
        mock_domain = AsyncMock()
        mock_domain.get_by_domain = AsyncMock(
            return_value=DomainJoinPolicy(
                id=uuid.uuid4(),
                company_id=other_company_id,
                domain="acme.example",
                policy=DomainPolicy.REQUEST_APPROVAL,
                verified=True,
            )
        )

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company),
            patch("tessera_api.routers.companies.SqlOnboardingRepository", return_value=mock_ob),
            patch(
                "tessera_api.routers.companies.SqlDomainPolicyRepository",
                return_value=mock_domain,
            ),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/companies",
                    json={"name": "Acme Corp"},
                    headers=_make_jwt_header(user_id, "founder@acme.example"),
                )

        assert response.status_code == 201
        mock_domain.create.assert_not_called()

    def test_race_integrity_error_does_not_fail_creation(self):
        """A concurrent claim (IntegrityError on the policy insert) is swallowed
        by the savepoint; company creation still returns 201."""
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)

        mock_company = _company_repo_mock(user_id, company_id, now)
        mock_ob = AsyncMock()
        mock_ob.advance_step = AsyncMock(return_value=_make_progress(user_id))
        mock_domain = AsyncMock()
        mock_domain.get_by_domain = AsyncMock(return_value=None)  # pre-check passes
        mock_domain.create = AsyncMock(
            side_effect=IntegrityError("dup", None, Exception("unique"))
        )

        # A savepoint whose __aexit__ does NOT suppress — the IntegrityError must
        # reach create_company's except handler.
        savepoint = AsyncMock()
        savepoint.__aexit__ = AsyncMock(return_value=False)
        mock_session = AsyncMock()
        mock_session.begin_nested = MagicMock(return_value=savepoint)

        with (
            _bypass_onboarding_guard(),
            _with_db(mock_session),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company),
            patch("tessera_api.routers.companies.SqlOnboardingRepository", return_value=mock_ob),
            patch(
                "tessera_api.routers.companies.SqlDomainPolicyRepository",
                return_value=mock_domain,
            ),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/companies",
                    json={"name": "Acme Corp"},
                    headers=_make_jwt_header(user_id, "founder@acme.example"),
                )

        assert response.status_code == 201
        mock_domain.create.assert_awaited_once()


class TestCreateDomainPolicyPublicGuard:
    def test_public_domain_rejected_422_and_writes_nothing(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)

        company = Company(
            id=company_id, name="Acme Corp", admin_user_id=user_id, created_at=now, updated_at=now
        )
        admin_membership = CompanyMembership(
            id=uuid.uuid4(),
            user_id=user_id,
            company_id=company_id,
            role=CompanyRole.ADMIN,
            joined_at=now,
        )
        mock_company = AsyncMock()
        mock_company.get_membership = AsyncMock(return_value=admin_membership)
        mock_company.get_by_id = AsyncMock(return_value=company)

        mock_domain = AsyncMock()
        mock_domain.get_by_domain = AsyncMock(return_value=None)

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company),
            patch(
                "tessera_api.routers.companies.SqlDomainPolicyRepository",
                return_value=mock_domain,
            ),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    f"/v1/companies/{company_id}/domain-policies",
                    json={"domain": "gmail.com", "policy": "request_approval"},
                    headers=_make_jwt_header(user_id, "admin@acme.example"),
                )

        assert response.status_code == 422
        # A custom exception handler flattens HTTPException.detail, so the body is
        # the contract's {"error": {...}} shape directly.
        assert response.json()["error"]["code"] == "public_domain_not_allowed"
        mock_domain.create.assert_not_called()
