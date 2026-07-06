"""Integration tests for domain-match join + isolation (US1).

Locks in the existing (unchanged) suggestions/join code paths that US3 activates:
a same-domain user sees the auto-associated company and can request to join
(landing in ``pending`` with no membership and no duplicate request), while a
different-domain or public-domain user can neither see nor join it.

Router-level tests with mocked repositories, matching ``test_companies.py`` style.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from tessera_core.domain.entities import (
    Company,
    DomainJoinPolicy,
    DomainPolicy,
    JoinRequest,
    JoinRequestStatus,
)

COMPANY_DOMAIN = "acme.example"


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


def _company(company_id: uuid.UUID, admin_id: uuid.UUID) -> Company:
    now = datetime.now(UTC)
    return Company(
        id=company_id, name="Acme Corp", admin_user_id=admin_id, created_at=now, updated_at=now
    )


def _verified_policy(company_id: uuid.UUID, domain: str = COMPANY_DOMAIN) -> DomainJoinPolicy:
    return DomainJoinPolicy(
        id=uuid.uuid4(),
        company_id=company_id,
        domain=domain,
        policy=DomainPolicy.REQUEST_APPROVAL,
        verified=True,
    )


class TestSuggestions:
    def test_same_domain_user_sees_match(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()

        mock_inv = AsyncMock()
        mock_inv.get_pending_for_email = AsyncMock(return_value=[])
        mock_domain = AsyncMock()
        mock_domain.get_by_domain = AsyncMock(return_value=_verified_policy(company_id))
        mock_company = AsyncMock()
        mock_company.get_by_id = AsyncMock(return_value=_company(company_id, uuid.uuid4()))

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlInvitationRepository", return_value=mock_inv),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company),
            patch(
                "tessera_api.routers.companies.SqlDomainPolicyRepository", return_value=mock_domain
            ),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=AsyncMock()),
        ):
            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.get(
                    "/v1/companies/suggestions",
                    headers=_make_jwt_header(user_id, f"teammate@{COMPANY_DOMAIN}"),
                )

        assert response.status_code == 200
        matches = response.json()["domain_matches"]
        assert len(matches) == 1
        assert matches[0]["company_id"] == str(company_id)
        assert matches[0]["domain"] == COMPANY_DOMAIN
        assert matches[0]["policy"] == "request_approval"

    def test_other_domain_user_sees_no_match(self):
        user_id = uuid.uuid4()

        mock_inv = AsyncMock()
        mock_inv.get_pending_for_email = AsyncMock(return_value=[])
        mock_domain = AsyncMock()
        # No policy owns @other.example — the caller's own domain never matches X.
        mock_domain.get_by_domain = AsyncMock(return_value=None)

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlInvitationRepository", return_value=mock_inv),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=AsyncMock()),
            patch(
                "tessera_api.routers.companies.SqlDomainPolicyRepository", return_value=mock_domain
            ),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=AsyncMock()),
        ):
            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.get(
                    "/v1/companies/suggestions",
                    headers=_make_jwt_header(user_id, "someone@other.example"),
                )

        assert response.status_code == 200
        assert response.json()["domain_matches"] == []


class TestDomainMatchJoin:
    def _run_join(self, *, user_id, email, company_id, mock_company, mock_domain, mock_jr):
        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(
            return_value=MagicMock(email="admin@acme.example", display_name="Admin")
        )
        mock_adapter = MagicMock()
        mock_adapter.send_join_request_notification = AsyncMock()

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company),
            patch(
                "tessera_api.routers.companies.SqlDomainPolicyRepository", return_value=mock_domain
            ),
            patch("tessera_api.routers.companies.SqlJoinRequestRepository", return_value=mock_jr),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=mock_user_repo),
            patch("tessera_api.adapters.email.FastMailEmailAdapter", return_value=mock_adapter),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    f"/v1/companies/{company_id}/join",
                    json={"method": "domain_match"},
                    headers=_make_jwt_header(user_id, email),
                )
        return response, mock_adapter

    def test_request_approval_returns_pending_no_membership_and_notifies(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()

        mock_company = AsyncMock()
        mock_company.get_by_id = AsyncMock(return_value=_company(company_id, uuid.uuid4()))
        mock_company.get_membership = AsyncMock(return_value=None)
        mock_domain = AsyncMock()
        mock_domain.get_by_domain = AsyncMock(return_value=_verified_policy(company_id))
        mock_jr = AsyncMock()
        mock_jr.get_by_user_and_company = AsyncMock(return_value=None)
        mock_jr.create = AsyncMock(
            return_value=JoinRequest(
                id=uuid.uuid4(),
                user_id=user_id,
                company_id=company_id,
                status=JoinRequestStatus.PENDING,
                requested_at=datetime.now(UTC),
            )
        )

        response, mock_adapter = self._run_join(
            user_id=user_id,
            email=f"teammate@{COMPANY_DOMAIN}",
            company_id=company_id,
            mock_company=mock_company,
            mock_domain=mock_domain,
            mock_jr=mock_jr,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "pending"
        mock_jr.create.assert_awaited_once()
        mock_company.add_membership.assert_not_called()
        mock_adapter.send_join_request_notification.assert_awaited_once()

    def test_re_request_while_pending_does_not_duplicate(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()

        existing = JoinRequest(
            id=uuid.uuid4(),
            user_id=user_id,
            company_id=company_id,
            status=JoinRequestStatus.PENDING,
            requested_at=datetime.now(UTC),
        )
        mock_company = AsyncMock()
        mock_company.get_by_id = AsyncMock(return_value=_company(company_id, uuid.uuid4()))
        mock_company.get_membership = AsyncMock(return_value=None)
        mock_domain = AsyncMock()
        mock_domain.get_by_domain = AsyncMock(return_value=_verified_policy(company_id))
        mock_jr = AsyncMock()
        mock_jr.get_by_user_and_company = AsyncMock(return_value=existing)

        response, _ = self._run_join(
            user_id=user_id,
            email=f"teammate@{COMPANY_DOMAIN}",
            company_id=company_id,
            mock_company=mock_company,
            mock_domain=mock_domain,
            mock_jr=mock_jr,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "pending"
        mock_jr.create.assert_not_called()

    def test_other_domain_user_cannot_join_returns_404(self):
        """Isolation: a @other.example user joining company X (which owns
        @acme.example) is rejected — no policy owns the caller's own domain."""
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()

        mock_company = AsyncMock()
        mock_company.get_by_id = AsyncMock(return_value=_company(company_id, uuid.uuid4()))
        mock_company.get_membership = AsyncMock(return_value=None)
        mock_domain = AsyncMock()
        # get_by_domain is keyed on the CALLER's own domain (@other.example) → None.
        mock_domain.get_by_domain = AsyncMock(return_value=None)
        mock_jr = AsyncMock()

        response, _ = self._run_join(
            user_id=user_id,
            email="intruder@other.example",
            company_id=company_id,
            mock_company=mock_company,
            mock_domain=mock_domain,
            mock_jr=mock_jr,
        )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "no_domain_policy"
        mock_jr.create.assert_not_called()
        mock_company.add_membership.assert_not_called()
