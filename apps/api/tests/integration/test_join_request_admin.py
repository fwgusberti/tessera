"""Integration tests for admin join-request decisions (US2).

Locks in the existing (unchanged) admin list/approve/deny loop that US1 depends
on: an admin can see a pending request, approve it into a member membership or
deny it, decided requests are not re-actionable (409), and non-admins are
blocked (403).

Router-level tests with mocked repositories, matching ``test_companies.py`` style.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from tessera_core.domain.entities import (
    Company,
    CompanyMembership,
    CompanyRole,
    JoinRequest,
    JoinRequestStatus,
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

    async def _gen():
        yield mock_session

    app.dependency_overrides[get_db] = _gen
    try:
        yield mock_session
    finally:
        app.dependency_overrides.pop(get_db, None)


def _make_jwt_header(user_id: uuid.UUID, email: str = "admin@acme.example") -> dict:
    from tessera_api.auth.jwt_auth import create_access_token

    token = create_access_token(user_id, email, False)
    return {"Authorization": f"Bearer {token}"}


def _company(company_id, admin_id):
    now = datetime.now(UTC)
    return Company(
        id=company_id, name="Acme Corp", admin_user_id=admin_id, created_at=now, updated_at=now
    )


def _admin_membership(user_id, company_id):
    return CompanyMembership(
        id=uuid.uuid4(),
        user_id=user_id,
        company_id=company_id,
        role=CompanyRole.ADMIN,
        joined_at=datetime.now(UTC),
    )


def _pending_request(user_id, company_id):
    return JoinRequest(
        id=uuid.uuid4(),
        user_id=user_id,
        company_id=company_id,
        status=JoinRequestStatus.PENDING,
        requested_at=datetime.now(UTC),
    )


def _audit_actions(mock_audit: AsyncMock) -> list[str]:
    return [c.kwargs.get("action") for c in mock_audit.call_args_list]


class TestListJoinRequests:
    def test_admin_sees_pending_request_with_identity(self):
        admin_id = uuid.uuid4()
        requester_id = uuid.uuid4()
        company_id = uuid.uuid4()

        jr = _pending_request(requester_id, company_id)
        mock_company = AsyncMock()
        mock_company.get_membership = AsyncMock(
            return_value=_admin_membership(admin_id, company_id)
        )
        mock_jr = AsyncMock()
        mock_jr.list_pending_for_company = AsyncMock(return_value=[jr])
        mock_user = AsyncMock()
        mock_user.get_by_id = AsyncMock(
            return_value=MagicMock(display_name="Req Uester", email="req@acme.example")
        )

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company),
            patch("tessera_api.routers.companies.SqlJoinRequestRepository", return_value=mock_jr),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=mock_user),
        ):
            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.get(
                    f"/v1/companies/{company_id}/join-requests",
                    headers=_make_jwt_header(admin_id),
                )

        assert response.status_code == 200
        items = response.json()["join_requests"]
        assert len(items) == 1
        assert items[0]["user_name"] == "Req Uester"
        assert items[0]["user_email"] == "req@acme.example"

    def test_non_admin_gets_403(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()

        mock_company = AsyncMock()
        mock_company.get_membership = AsyncMock(return_value=None)  # no admin membership

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company),
            patch(
                "tessera_api.routers.companies.SqlJoinRequestRepository", return_value=AsyncMock()
            ),
        ):
            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.get(
                    f"/v1/companies/{company_id}/join-requests",
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 403


class TestApproveJoinRequest:
    def _run(self, *, admin_id, company_id, join_req, membership_side=None):
        mock_company = AsyncMock()
        mock_company.get_membership = AsyncMock(
            return_value=_admin_membership(admin_id, company_id)
        )
        mock_company.get_by_id = AsyncMock(return_value=_company(company_id, admin_id))
        if membership_side is not None:
            mock_company.get_membership = AsyncMock(side_effect=membership_side)
        mock_company.add_membership = AsyncMock(return_value=None)

        mock_jr = AsyncMock()
        mock_jr.get_by_id = AsyncMock(return_value=join_req)
        mock_jr.decide = AsyncMock(return_value=None)

        mock_ob = AsyncMock()
        mock_ob.advance_step = AsyncMock(return_value=None)

        mock_user = AsyncMock()
        mock_user.get_by_id = AsyncMock(
            return_value=MagicMock(email="req@acme.example", display_name="Req")
        )
        mock_adapter = MagicMock()
        mock_adapter.send_join_request_decision = AsyncMock()

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company),
            patch("tessera_api.routers.companies.SqlJoinRequestRepository", return_value=mock_jr),
            patch("tessera_api.routers.companies.SqlOnboardingRepository", return_value=mock_ob),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=mock_user),
            patch("tessera_api.adapters.email.FastMailEmailAdapter", return_value=mock_adapter),
            patch(
                "tessera_api.routers.companies.write_audit", new_callable=AsyncMock
            ) as mock_audit,
        ):
            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    f"/v1/companies/{company_id}/join-requests/{join_req.id}/approve",
                    headers=_make_jwt_header(admin_id),
                )
        return response, mock_company, mock_jr, mock_adapter, mock_audit

    def test_approve_creates_member_notifies_and_audits(self):
        admin_id = uuid.uuid4()
        company_id = uuid.uuid4()
        requester_id = uuid.uuid4()
        jr = _pending_request(requester_id, company_id)

        response, mock_company, mock_jr, mock_adapter, mock_audit = self._run(
            admin_id=admin_id, company_id=company_id, join_req=jr
        )

        assert response.status_code == 200
        assert response.json()["status"] == "approved"
        mock_jr.decide.assert_awaited_once()
        assert mock_jr.decide.await_args.args[1] == JoinRequestStatus.APPROVED
        mock_company.add_membership.assert_awaited_once()
        membership_arg = mock_company.add_membership.await_args.args[0]
        assert membership_arg.user_id == requester_id
        assert membership_arg.role == CompanyRole.MEMBER
        assert mock_adapter.send_join_request_decision.await_args.kwargs["approved"] is True
        assert "company.join_request_approved" in _audit_actions(mock_audit)

    def test_approve_already_decided_returns_409(self):
        admin_id = uuid.uuid4()
        company_id = uuid.uuid4()
        jr = _pending_request(uuid.uuid4(), company_id)
        jr.status = JoinRequestStatus.APPROVED  # already decided

        response, mock_company, mock_jr, _, _ = self._run(
            admin_id=admin_id, company_id=company_id, join_req=jr
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "already_decided"
        mock_company.add_membership.assert_not_called()


class TestDenyJoinRequest:
    def test_deny_marks_denied_and_notifies(self):
        admin_id = uuid.uuid4()
        company_id = uuid.uuid4()
        jr = _pending_request(uuid.uuid4(), company_id)

        mock_company = AsyncMock()
        mock_company.get_membership = AsyncMock(
            return_value=_admin_membership(admin_id, company_id)
        )
        mock_company.get_by_id = AsyncMock(return_value=_company(company_id, admin_id))
        mock_jr = AsyncMock()
        mock_jr.get_by_id = AsyncMock(return_value=jr)
        mock_jr.decide = AsyncMock(return_value=None)
        mock_user = AsyncMock()
        mock_user.get_by_id = AsyncMock(
            return_value=MagicMock(email="req@acme.example", display_name="Req")
        )
        mock_adapter = MagicMock()
        mock_adapter.send_join_request_decision = AsyncMock()

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company),
            patch("tessera_api.routers.companies.SqlJoinRequestRepository", return_value=mock_jr),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=mock_user),
            patch("tessera_api.adapters.email.FastMailEmailAdapter", return_value=mock_adapter),
            patch(
                "tessera_api.routers.companies.write_audit", new_callable=AsyncMock
            ) as mock_audit,
        ):
            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    f"/v1/companies/{company_id}/join-requests/{jr.id}/deny",
                    headers=_make_jwt_header(admin_id),
                )

        assert response.status_code == 200
        assert response.json()["status"] == "denied"
        assert mock_jr.decide.await_args.args[1] == JoinRequestStatus.DENIED
        assert mock_adapter.send_join_request_decision.await_args.kwargs["approved"] is False
        assert "company.join_request_denied" in _audit_actions(mock_audit)

    def test_non_admin_deny_gets_403(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        request_id = uuid.uuid4()

        mock_company = AsyncMock()
        mock_company.get_membership = AsyncMock(return_value=None)

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company),
            patch(
                "tessera_api.routers.companies.SqlJoinRequestRepository", return_value=AsyncMock()
            ),
        ):
            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    f"/v1/companies/{company_id}/join-requests/{request_id}/deny",
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 403
