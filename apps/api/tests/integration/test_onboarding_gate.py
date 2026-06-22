"""Integration tests for the require_onboarding_complete guard.

Verifies that:
- Endpoints called during the onboarding company step are NOT blocked.
- Non-onboarding endpoints remain blocked for mid-onboarding users.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from tessera_core.domain.entities import (
    Company,
    CompanyMembership,
    CompanyRole,
    Invitation,
    InvitationStatus,
    OnboardingProgress,
)


def _make_jwt_header(user_id: uuid.UUID | None = None, email: str = "user@gate-test.com") -> dict:
    from tessera_api.auth.jwt_auth import create_access_token

    uid = user_id or uuid.uuid4()
    token = create_access_token(uid, email, False)
    return {"Authorization": f"Bearer {token}"}


def _make_incomplete_progress(user_id: uuid.UUID) -> OnboardingProgress:
    """OnboardingProgress with completed_at=None — simulates a mid-onboarding user."""
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


def _bearer_db_mocks(user_id: uuid.UUID):
    """Return (db_mock, ob_cls_mock) that make the bearer guard see incomplete onboarding.

    Patches tessera_api.adapters.database.get_db and
    tessera_api.adapters.repo.SqlOnboardingRepository — both imported dynamically
    inside require_onboarding_complete, so source-module patching is correct.
    """
    progress = _make_incomplete_progress(user_id)

    mock_session = AsyncMock()
    mock_db = MagicMock()
    mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

    mock_ob_cls = MagicMock()
    mock_ob_instance = AsyncMock()
    mock_ob_instance.get_by_user_id = AsyncMock(return_value=progress)
    mock_ob_cls.return_value = mock_ob_instance

    return mock_db, mock_ob_cls


def _handler_db_mock():
    """Return (db_mock, session) for mocking a route handler's get_db() call."""
    mock_session = AsyncMock()
    mock_db = MagicMock()
    mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_db, mock_session


class TestOnboardingGateExemptions:
    """Endpoints called during onboarding must be reachable before onboarding completes."""

    def test_create_company_allowed_mid_onboarding(self):
        """POST /v1/companies must NOT be blocked for a mid-onboarding user (US1)."""
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)
        progress = _make_incomplete_progress(user_id)

        bearer_db, bearer_ob_cls = _bearer_db_mocks(user_id)
        handler_db, _ = _handler_db_mock()

        company = Company(
            id=company_id, name="Gate Test Co", admin_user_id=user_id,
            created_at=now, updated_at=now,
        )
        membership = CompanyMembership(
            id=uuid.uuid4(), user_id=user_id, company_id=company_id,
            role=CompanyRole.ADMIN, joined_at=now,
        )

        mock_company_repo = AsyncMock()
        mock_company_repo.create = AsyncMock(return_value=company)
        mock_company_repo.add_membership = AsyncMock(return_value=membership)

        mock_ob_handler = AsyncMock()
        mock_ob_handler.advance_step = AsyncMock(return_value=progress)

        with (
            patch("tessera_api.adapters.database.get_db", bearer_db),
            patch("tessera_api.adapters.repo.SqlOnboardingRepository", bearer_ob_cls),
            patch("tessera_api.routers.companies.get_db", handler_db),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company_repo),
            patch("tessera_api.routers.companies.SqlOnboardingRepository", return_value=mock_ob_handler),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/companies",
                    json={"name": "Gate Test Co"},
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 201, (
            f"Expected 201 (gate exempted), got {response.status_code}: {response.json()}"
        )

    def test_get_suggestions_allowed_mid_onboarding(self):
        """GET /v1/companies/suggestions must NOT be blocked for a mid-onboarding user (US2)."""
        user_id = uuid.uuid4()

        bearer_db, bearer_ob_cls = _bearer_db_mocks(user_id)
        handler_db, _ = _handler_db_mock()

        mock_inv_repo = AsyncMock()
        mock_inv_repo.get_pending_for_email = AsyncMock(return_value=[])

        mock_domain_repo = AsyncMock()
        mock_domain_repo.get_by_domain = AsyncMock(return_value=None)

        with (
            patch("tessera_api.adapters.database.get_db", bearer_db),
            patch("tessera_api.adapters.repo.SqlOnboardingRepository", bearer_ob_cls),
            patch("tessera_api.routers.companies.get_db", handler_db),
            patch("tessera_api.routers.companies.SqlInvitationRepository", return_value=mock_inv_repo),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=AsyncMock()),
            patch("tessera_api.routers.companies.SqlDomainPolicyRepository", return_value=mock_domain_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=AsyncMock()),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.get(
                    "/v1/companies/suggestions",
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 200, (
            f"Expected 200 (gate exempted), got {response.status_code}: {response.json()}"
        )

    def test_join_company_allowed_mid_onboarding(self):
        """POST /v1/companies/{id}/join must NOT be blocked for a mid-onboarding user (US3)."""
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        invitation_id = uuid.uuid4()
        now = datetime.now(UTC)
        progress = _make_incomplete_progress(user_id)

        bearer_db, bearer_ob_cls = _bearer_db_mocks(user_id)
        handler_db, _ = _handler_db_mock()

        company = Company(
            id=company_id, name="Existing Corp",
            admin_user_id=uuid.uuid4(), created_at=now, updated_at=now,
        )
        invitation = Invitation(
            id=invitation_id,
            company_id=company_id,
            email="user@gate-test.com",
            token_hash="hash",
            status=InvitationStatus.PENDING,
            expires_at=now + timedelta(days=3),
            created_at=now,
        )
        membership = CompanyMembership(
            id=uuid.uuid4(), user_id=user_id, company_id=company_id,
            role=CompanyRole.MEMBER, joined_at=now,
        )

        mock_company_repo = AsyncMock()
        mock_company_repo.get_by_id = AsyncMock(return_value=company)
        mock_company_repo.get_membership = AsyncMock(return_value=None)
        mock_company_repo.add_membership = AsyncMock(return_value=membership)

        mock_inv_repo = AsyncMock()
        mock_inv_repo.get_by_id = AsyncMock(return_value=invitation)
        mock_inv_repo.update_status = AsyncMock()

        mock_ob_handler = AsyncMock()
        mock_ob_handler.advance_step = AsyncMock(return_value=progress)

        with (
            patch("tessera_api.adapters.database.get_db", bearer_db),
            patch("tessera_api.adapters.repo.SqlOnboardingRepository", bearer_ob_cls),
            patch("tessera_api.routers.companies.get_db", handler_db),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company_repo),
            patch("tessera_api.routers.companies.SqlInvitationRepository", return_value=mock_inv_repo),
            patch("tessera_api.routers.companies.SqlOnboardingRepository", return_value=mock_ob_handler),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    f"/v1/companies/{company_id}/join",
                    json={"method": "invitation", "invitation_id": str(invitation_id)},
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 200, (
            f"Expected 200 (gate exempted), got {response.status_code}: {response.json()}"
        )


class TestAdminInvariantAfterEnrollment:
    """Admin-role invariant: exactly one ADMIN membership exists immediately after company creation."""

    def test_create_company_establishes_exactly_one_admin(self):
        """POST /v1/companies must create exactly one ADMIN membership for the new company (T011)."""
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)
        progress = _make_incomplete_progress(user_id)

        bearer_db, bearer_ob_cls = _bearer_db_mocks(user_id)
        handler_db, _ = _handler_db_mock()

        company = Company(
            id=company_id, name="Invariant Test Co", admin_user_id=user_id,
            created_at=now, updated_at=now,
        )
        membership = CompanyMembership(
            id=uuid.uuid4(), user_id=user_id, company_id=company_id,
            role=CompanyRole.ADMIN, joined_at=now,
        )

        mock_company_repo = AsyncMock()
        mock_company_repo.create = AsyncMock(return_value=company)
        mock_company_repo.add_membership = AsyncMock(return_value=membership)

        mock_ob_handler = AsyncMock()
        mock_ob_handler.advance_step = AsyncMock(return_value=progress)

        with (
            patch("tessera_api.adapters.database.get_db", bearer_db),
            patch("tessera_api.adapters.repo.SqlOnboardingRepository", bearer_ob_cls),
            patch("tessera_api.routers.companies.get_db", handler_db),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company_repo),
            patch("tessera_api.routers.companies.SqlOnboardingRepository", return_value=mock_ob_handler),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/companies",
                    json={"name": "Invariant Test Co"},
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 201, (
            f"Expected 201, got {response.status_code}: {response.json()}"
        )
        mock_company_repo.add_membership.assert_awaited_once()
        membership_arg = mock_company_repo.add_membership.await_args.args[0]
        assert membership_arg.user_id == user_id
        assert membership_arg.company_id == company_id
        assert membership_arg.role == CompanyRole.ADMIN, (
            f"Expected ADMIN role, got {membership_arg.role} — admin invariant violated"
        )


class TestOnboardingGateRegression:
    """Non-onboarding endpoints must remain blocked for mid-onboarding users."""

    def test_list_join_requests_blocked_mid_onboarding(self):
        """GET /v1/companies/{id}/join-requests must return 403 for a mid-onboarding user."""
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()

        bearer_db, bearer_ob_cls = _bearer_db_mocks(user_id)

        # No handler mocks — guard fires before handler runs
        with (
            patch("tessera_api.adapters.database.get_db", bearer_db),
            patch("tessera_api.adapters.repo.SqlOnboardingRepository", bearer_ob_cls),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.get(
                    f"/v1/companies/{company_id}/join-requests",
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 403
        assert "onboarding_required" in str(response.json())


class TestOnboardingGateIncompleteSession:
    """Guard must handle sessions missing 'sub' gracefully (return 401, not 500)."""

    def _encode_session_cookie(self, session_data: dict) -> str:
        import base64
        import json
        from itsdangerous import TimestampSigner

        signer = TimestampSigner("dev-secret-key-change-in-production")
        data = base64.b64encode(json.dumps(session_data).encode()).decode()
        return signer.sign(data).decode()

    def test_incomplete_session_returns_401_not_500(self):
        """A session cookie with active_company_id but no sub must yield HTTP 401, not 500."""
        company_id = uuid.uuid4()
        broken_session = {"user": {"active_company_id": str(company_id)}}
        session_cookie = self._encode_session_cookie(broken_session)

        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app, raise_server_exceptions=False) as client:
            client.cookies.set("session", session_cookie)
            response = client.get(f"/v1/companies/{company_id}/join-requests")

        assert response.status_code == 401, (
            f"Expected 401, got {response.status_code}: {response.json()}"
        )

    def test_complete_session_after_activate_passes_guard(self):
        """Session with sub (set by activate_company) must not crash on guarded routes (SC-001 regression)."""
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)

        # Session with a complete identity (as set by the fixed activate_company endpoint)
        complete_session = {
            "user": {
                "sub": str(user_id),
                "email": "user@example.com",
                "is_admin": False,
                "active_company_id": str(company_id),
            }
        }
        session_cookie = self._encode_session_cookie(complete_session)

        progress = OnboardingProgress(
            id=uuid.uuid4(),
            user_id=user_id,
            completed_steps=["profile", "company"],
            current_step="done",
            company_join_method="created",
            completed_at=datetime.now(UTC),
            created_at=now,
            updated_at=now,
        )
        mock_session_db = AsyncMock()
        mock_db = MagicMock()
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session_db)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_ob_cls = MagicMock()
        mock_ob_instance = AsyncMock()
        mock_ob_instance.get_by_user_id = AsyncMock(return_value=progress)
        mock_ob_cls.return_value = mock_ob_instance

        mock_company_repo = AsyncMock()
        mock_company_repo.get_membership = AsyncMock(return_value=None)  # not a member → 403

        with (
            patch("tessera_api.adapters.database.get_db", mock_db),
            patch("tessera_api.adapters.repo.SqlOnboardingRepository", mock_ob_cls),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company_repo),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app, raise_server_exceptions=False) as client:
                client.cookies.set("session", session_cookie)
                response = client.get(f"/v1/companies/{company_id}/join-requests")

        assert response.status_code != 500, (
            f"Got 500 — KeyError: 'sub' regression: {response.json()}"
        )


class TestStaleSessionNoJwt:
    """Stale session cookie with no JWT must return 401 — no accidental open access."""

    def _encode_session_cookie(self, session_data: dict) -> str:
        import base64
        import json
        from itsdangerous import TimestampSigner

        signer = TimestampSigner("dev-secret-key-change-in-production")
        data = base64.b64encode(json.dumps(session_data).encode()).decode()
        return signer.sign(data).decode()

    def test_stale_session_no_jwt_returns_401(self):
        """Stale session with active_company_id but no sub and no JWT → 401 (no open access)."""
        company_id = uuid.uuid4()
        broken_session = {"user": {"active_company_id": str(company_id)}}
        session_cookie = self._encode_session_cookie(broken_session)

        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            client.cookies.set("session", session_cookie)
            response = client.get("/v1/companies/me")

        assert response.status_code == 401
