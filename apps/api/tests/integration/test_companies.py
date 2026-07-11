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

        mock_company = AsyncMock()
        mock_company.create = AsyncMock(return_value=company)
        mock_company.add_membership = AsyncMock(return_value=membership)

        mock_ob = AsyncMock()
        mock_ob.advance_step = AsyncMock(return_value=progress)

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company),
            patch("tessera_api.routers.companies.SqlOnboardingRepository", return_value=mock_ob),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/companies",
                    json={"name": "Acme Corp", "industry": "Technology", "team_size": "11-50"},
                    # Public founder domain → no domain auto-association side effect
                    # (US3), keeping this contract test focused on creation itself.
                    headers=_make_jwt_header(user_id, email="founder@gmail.com"),
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

        mock_inv = AsyncMock()
        mock_inv.get_pending_for_email = AsyncMock(return_value=[])

        mock_domain = AsyncMock()
        mock_domain.get_by_domain = AsyncMock(return_value=None)

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlInvitationRepository", return_value=mock_inv),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=AsyncMock()),
            patch("tessera_api.routers.companies.SqlDomainPolicyRepository", return_value=mock_domain),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=AsyncMock()),
        ):
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

        mock_company = AsyncMock()
        mock_company.get_by_id = AsyncMock(return_value=company)
        mock_company.get_membership = AsyncMock(return_value=None)
        mock_company.add_membership = AsyncMock(return_value=membership)

        mock_inv = AsyncMock()
        mock_inv.get_by_id = AsyncMock(return_value=invitation)
        mock_inv.update_status = AsyncMock(return_value=invitation)

        mock_ob = AsyncMock()
        mock_ob.advance_step = AsyncMock(return_value=progress)

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company),
            patch("tessera_api.routers.companies.SqlInvitationRepository", return_value=mock_inv),
            patch("tessera_api.routers.companies.SqlOnboardingRepository", return_value=mock_ob),
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

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "joined"
        assert body["company_name"] == "Acme Corp"

    def test_company_not_found_returns_404(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()

        mock_company = AsyncMock()
        mock_company.get_by_id = AsyncMock(return_value=None)

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company),
        ):
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

        mock_company = AsyncMock()
        mock_company.get_by_id = AsyncMock(return_value=company)

        mock_jr = AsyncMock()
        mock_jr.get_by_user_and_company = AsyncMock(return_value=join_req)

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlJoinRequestRepository", return_value=mock_jr),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_company),
        ):
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
            allowed = client.options(
                "/v1/companies",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type,authorization",
                },
            )
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

        mock_jr = AsyncMock()
        mock_jr.get_by_user_and_company = AsyncMock(return_value=join_req)
        mock_jr.cancel = AsyncMock(return_value=None)

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlJoinRequestRepository", return_value=mock_jr),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
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

        mock_repo = AsyncMock()
        mock_repo.list_memberships_for_user = AsyncMock(return_value=[membership])
        mock_repo.get_by_id = AsyncMock(return_value=company)

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_repo),
        ):
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


class TestActivateCompany:
    def test_activate_returns_200_with_token_for_member(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)

        company = Company(
            id=company_id, name="Acme Corp", admin_user_id=user_id,
            created_at=now, updated_at=now,
        )
        membership = CompanyMembership(
            id=uuid.uuid4(), user_id=user_id, company_id=company_id,
            role=CompanyRole.MEMBER, joined_at=now,
        )

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=company)
        mock_repo.get_membership = AsyncMock(return_value=membership)

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_repo),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    f"/v1/companies/{company_id}/activate",
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 200
        body = response.json()
        assert "token" in body
        assert body["company_id"] == str(company_id)
        assert body["company_name"] == "Acme Corp"

    def test_activate_returns_403_for_non_member(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)

        company = Company(
            id=company_id, name="Other Corp", admin_user_id=uuid.uuid4(),
            created_at=now, updated_at=now,
        )

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=company)
        mock_repo.get_membership = AsyncMock(return_value=None)

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_repo),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    f"/v1/companies/{company_id}/activate",
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 403


class TestGetMyCompaniesAuth:
    """Verify auth fallthrough and gate exemption for GET /v1/companies/me."""

    def _encode_session_cookie(self, session_data: dict) -> str:
        import base64
        import json
        from itsdangerous import TimestampSigner

        signer = TimestampSigner("dev-secret-key-change-in-production")
        data = base64.b64encode(json.dumps(session_data).encode()).decode()
        return signer.sign(data).decode()

    def test_stale_session_with_valid_jwt_returns_200(self):
        """Stale session (no sub) + valid JWT Bearer → require_user falls through to JWT → 200."""
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)

        stale_session = {"user": {"active_company_id": str(company_id)}}
        session_cookie = self._encode_session_cookie(stale_session)

        company = Company(id=company_id, name="Acme Corp", admin_user_id=user_id, created_at=now)
        membership = CompanyMembership(
            id=uuid.uuid4(), user_id=user_id, company_id=company_id, role=CompanyRole.ADMIN
        )

        mock_repo = AsyncMock()
        mock_repo.list_memberships_for_user = AsyncMock(return_value=[membership])
        mock_repo.get_by_id = AsyncMock(return_value=company)

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_repo),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                client.cookies.set("session", session_cookie)
                response = client.get("/v1/companies/me", headers=_make_jwt_header(user_id))

        assert response.status_code == 200

    def test_mid_onboarding_user_returns_empty_list(self):
        """User with valid JWT but incomplete onboarding gets 200 + empty list (gate exemption)."""
        user_id = uuid.uuid4()

        progress = OnboardingProgress(
            id=uuid.uuid4(),
            user_id=user_id,
            completed_steps=["profile"],
            current_step="company",
            company_join_method=None,
            completed_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_ob_instance = AsyncMock()
        mock_ob_instance.get_by_user_id = AsyncMock(return_value=progress)

        handler_repo = AsyncMock()
        handler_repo.list_memberships_for_user = AsyncMock(return_value=[])

        with (
            _with_db(),
            patch("tessera_api.adapters.repo.SqlOnboardingRepository", return_value=mock_ob_instance),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=handler_repo),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.get("/v1/companies/me", headers=_make_jwt_header(user_id))

        assert response.status_code == 200
        assert response.json()["companies"] == []


class TestActivateCompanySession:
    """Verify that activate_company stores a complete identity in the session."""

    def _decode_session_cookie(self, cookie_value: str) -> dict:
        import base64
        import json
        from itsdangerous import TimestampSigner

        signer = TimestampSigner("dev-secret-key-change-in-production")
        raw = signer.unsign(cookie_value.encode(), max_age=None)
        return json.loads(base64.b64decode(raw))

    def _encode_session_cookie(self, session_data: dict) -> str:
        import base64
        import json
        from itsdangerous import TimestampSigner

        signer = TimestampSigner("dev-secret-key-change-in-production")
        data = base64.b64encode(json.dumps(session_data).encode()).decode()
        return signer.sign(data).decode()

    def _make_repo_mock(self, user_id: uuid.UUID, company_id: uuid.UUID, now: datetime):
        company = Company(
            id=company_id, name="Session Test Corp", admin_user_id=user_id,
            created_at=now, updated_at=now,
        )
        membership = CompanyMembership(
            id=uuid.uuid4(), user_id=user_id, company_id=company_id,
            role=CompanyRole.MEMBER, joined_at=now,
        )
        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=company)
        mock_repo.get_membership = AsyncMock(return_value=membership)
        return mock_repo

    def test_jwt_user_activate_stores_complete_identity(self):
        """JWT-only user activating a company gets sub, email, is_admin, and active_company_id in session."""
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)
        mock_repo = self._make_repo_mock(user_id, company_id, now)

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_repo),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    f"/v1/companies/{company_id}/activate",
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 200

        session_cookie = response.cookies.get("session")
        assert session_cookie is not None, "No session cookie in response — session was not persisted"

        session_data = self._decode_session_cookie(session_cookie)
        user = session_data.get("user", {})

        assert "sub" in user, f"Session user missing 'sub': {user}"
        assert "email" in user, f"Session user missing 'email': {user}"
        assert "is_admin" in user, f"Session user missing 'is_admin': {user}"
        assert "active_company_id" in user, f"Session user missing 'active_company_id': {user}"
        assert user["sub"] == str(user_id)
        assert user["active_company_id"] == str(company_id)

    def test_activate_company_preserves_existing_session_fields(self):
        """Existing session with sub and extra fields is not overwritten; only active_company_id is added."""
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        now = datetime.now(UTC)
        mock_repo = self._make_repo_mock(user_id, company_id, now)

        existing_session = {
            "user": {
                "sub": str(user_id),
                "email": "existing@oidc.example.com",
                "is_admin": True,
                "name": "OIDC User",
            }
        }
        original_cookie = self._encode_session_cookie(existing_session)

        with (
            _bypass_onboarding_guard(),
            _with_db(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=mock_repo),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                client.cookies.set("session", original_cookie)
                response = client.post(
                    f"/v1/companies/{company_id}/activate",
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 200

        result_cookie = response.cookies.get("session") or original_cookie
        session_data = self._decode_session_cookie(result_cookie)
        user = session_data.get("user", {})

        assert user.get("sub") == str(user_id), f"sub was overwritten: {user}"
        assert user.get("email") == "existing@oidc.example.com", f"email was overwritten: {user}"
        assert user.get("is_admin") is True, f"is_admin was overwritten: {user}"
        assert user.get("name") == "OIDC User", f"extra OIDC field was lost: {user}"


class TestAdminAddOnboardingJourney:
    """T006/US1: the end-to-end admin-add journey (contract table rows 1-2, 4).

    An admin adds an already-registered, not-yet-onboarded user; the direct-add
    endpoint marks the target onboarded, and the target's own ``GET /onboarding/status``
    then reports ``completed=true`` via the membership branch. (The server-gate leg —
    the added user's data calls returning 200 — is proven authoritatively against the
    real gate in ``test_onboarding_gate.py``; this file overrides that guard.)
    """

    def test_admin_add_then_status_reports_completed(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup
        from tessera_core.domain.entities import User

        target_id = uuid.uuid4()
        target = User(
            id=target_id,
            external_subject=f"sub-{target_id}",
            email="added@acme.test",
            display_name="Added Member",
            is_admin=False,
        )

        # --- Phase 1: admin directly adds the target ---------------------------------
        company_repo = AsyncMock()
        company_repo.get_membership = AsyncMock(return_value=None)
        company_repo.add_membership = AsyncMock(
            return_value=CompanyMembership(
                id=uuid.uuid4(),
                user_id=target_id,
                company_id=company_a_id,
                role=CompanyRole.MEMBER,
                joined_at=datetime.now(UTC),
            )
        )
        user_repo = AsyncMock()
        user_repo.get_by_id = AsyncMock(return_value=target)
        ob_repo = AsyncMock()
        ob_repo.get_by_user_id = AsyncMock(return_value=None)

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.SqlOnboardingRepository", return_value=ob_repo),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                add_resp = client.post(
                    "/v1/companies/members",
                    json={"user_id": str(target_id)},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert add_resp.status_code == 201, add_resp.text
        # The target was marked onboarded as part of the add (contract C4).
        ob_repo.complete.assert_awaited_once_with(target_id)

        # --- Phase 2: the added user checks their own onboarding status --------------
        # Membership is now authoritative — even with a null completed_at the status
        # endpoint reports completed=true (contract C3 / table rows 1-2).
        status_progress = _make_progress(target_id)  # completed_at is None
        status_ob = AsyncMock()
        status_ob.get_by_user_id = AsyncMock(return_value=status_progress)
        status_co = AsyncMock()
        status_co.list_memberships_for_user = AsyncMock(
            return_value=[
                CompanyMembership(
                    id=uuid.uuid4(),
                    user_id=target_id,
                    company_id=company_a_id,
                    role=CompanyRole.MEMBER,
                    joined_at=datetime.now(UTC),
                )
            ]
        )

        with (
            _with_db(),
            patch("tessera_api.routers.onboarding.SqlOnboardingRepository", return_value=status_ob),
            patch("tessera_api.routers.onboarding.SqlCompanyRepository", return_value=status_co),
        ):
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                status_resp = client.get(
                    "/v1/onboarding/status", headers=_make_jwt_header(target_id)
                )

        assert status_resp.status_code == 200, status_resp.text
        assert status_resp.json()["completed"] is True
