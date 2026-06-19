"""Integration tests for POST /v1/invitations."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tessera_core.domain.entities import (
    Company,
    CompanyMembership,
    CompanyRole,
    Invitation,
    InvitationStatus,
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


def _make_jwt_header(user_id: uuid.UUID | None = None, email: str = "admin@acme.com") -> dict:
    from tessera_api.auth.jwt_auth import create_access_token

    uid = user_id or uuid.uuid4()
    token = create_access_token(uid, email, False)
    return {"Authorization": f"Bearer {token}"}


def _make_company(user_id: uuid.UUID, company_id: uuid.UUID | None = None) -> Company:
    now = datetime.now(UTC)
    return Company(
        id=company_id or uuid.uuid4(),
        name="Acme Corp",
        admin_user_id=user_id,
        created_at=now,
        updated_at=now,
    )


def _admin_membership(user_id: uuid.UUID, company_id: uuid.UUID) -> CompanyMembership:
    return CompanyMembership(
        id=uuid.uuid4(),
        user_id=user_id,
        company_id=company_id,
        role=CompanyRole.ADMIN,
        joined_at=datetime.now(UTC),
    )


class TestSendInvitations:
    def test_send_invitations_returns_207_with_sent_emails(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        company = _make_company(user_id, company_id)
        membership = _admin_membership(user_id, company_id)

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.invitations.get_db") as mock_get_db,
                patch("tessera_api.routers.invitations.SqlCompanyRepository") as mock_company_cls,
                patch("tessera_api.routers.invitations.SqlInvitationRepository") as mock_inv_cls,
                patch("tessera_api.routers.invitations.SqlUserRepository") as mock_user_cls,
                patch("tessera_api.routers.invitations.write_audit", new_callable=AsyncMock),
                patch("tessera_api.routers.invitations.send_invitation_email", new_callable=AsyncMock),
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_company = AsyncMock()
                mock_company.list_memberships_for_user = AsyncMock(return_value=[membership])
                mock_company.get_by_id = AsyncMock(return_value=company)
                mock_company.get_membership = AsyncMock(return_value=None)
                mock_company_cls.return_value = mock_company

                mock_inv = AsyncMock()
                mock_inv.get_pending_for_email = AsyncMock(return_value=[])
                mock_inv.create_bulk = AsyncMock(return_value=[])
                mock_inv_cls.return_value = mock_inv

                mock_user_cls.return_value = AsyncMock()

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        "/v1/invitations",
                        json={"emails": ["alice@acme.com", "bob@acme.com"]},
                        headers=_make_jwt_header(user_id),
                    )

        assert response.status_code == 207
        body = response.json()
        assert set(body["sent"]) == {"alice@acme.com", "bob@acme.com"}
        assert body["failed"] == []

    def test_already_member_is_reported_in_failed(self):
        from unittest.mock import MagicMock

        from tessera_core.domain.entities import User

        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        company = _make_company(user_id, company_id)
        membership = _admin_membership(user_id, company_id)

        alice_id = uuid.uuid4()
        alice_user = User(
            id=alice_id,
            external_subject="sub-alice",
            email="alice@acme.com",
            display_name="Alice",
            is_admin=False,
        )
        alice_membership = CompanyMembership(
            id=uuid.uuid4(),
            user_id=alice_id,
            company_id=company_id,
            role=CompanyRole.MEMBER,
            joined_at=datetime.now(UTC),
        )

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.invitations.get_db") as mock_get_db,
                patch("tessera_api.routers.invitations.SqlCompanyRepository") as mock_company_cls,
                patch("tessera_api.routers.invitations.SqlInvitationRepository") as mock_inv_cls,
                patch("tessera_api.routers.invitations.SqlUserRepository") as mock_user_cls,
                patch("tessera_api.routers.invitations.write_audit", new_callable=AsyncMock),
                patch("tessera_api.routers.invitations.send_invitation_email", new_callable=AsyncMock),
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_company = AsyncMock()
                mock_company.list_memberships_for_user = AsyncMock(return_value=[membership])
                mock_company.get_by_id = AsyncMock(return_value=company)
                mock_company.get_membership = AsyncMock(
                    side_effect=lambda uid, cid: alice_membership if uid == alice_id else None
                )
                mock_company_cls.return_value = mock_company

                mock_user = AsyncMock()
                mock_user.get_by_id = AsyncMock(return_value=None)
                mock_user.get_by_email = AsyncMock(
                    side_effect=lambda email: alice_user if email == "alice@acme.com" else None
                )
                mock_user_cls.return_value = mock_user

                mock_inv = AsyncMock()
                mock_inv.get_pending_for_email = AsyncMock(return_value=[])
                mock_inv.create_bulk = AsyncMock(return_value=[])
                mock_inv_cls.return_value = mock_inv

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        "/v1/invitations",
                        json={"emails": ["alice@acme.com", "bob@acme.com"]},
                        headers=_make_jwt_header(user_id),
                    )

        assert response.status_code == 207
        body = response.json()
        failed_emails = {f["email"] for f in body["failed"]}
        assert "alice@acme.com" in failed_emails
        reason = next(f["reason"] for f in body["failed"] if f["email"] == "alice@acme.com")
        assert reason == "already_member"

    def test_already_invited_is_reported_in_failed(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        company = _make_company(user_id, company_id)
        membership = _admin_membership(user_id, company_id)

        existing_inv = Invitation(
            id=uuid.uuid4(),
            company_id=company_id,
            email="alice@acme.com",
            token_hash="existing_hash",
            status=InvitationStatus.PENDING,
            expires_at=datetime.now(UTC),
        )

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.invitations.get_db") as mock_get_db,
                patch("tessera_api.routers.invitations.SqlCompanyRepository") as mock_company_cls,
                patch("tessera_api.routers.invitations.SqlInvitationRepository") as mock_inv_cls,
                patch("tessera_api.routers.invitations.SqlUserRepository") as mock_user_cls,
                patch("tessera_api.routers.invitations.write_audit", new_callable=AsyncMock),
                patch("tessera_api.routers.invitations.send_invitation_email", new_callable=AsyncMock),
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_company = AsyncMock()
                mock_company.list_memberships_for_user = AsyncMock(return_value=[membership])
                mock_company.get_by_id = AsyncMock(return_value=company)
                mock_company.get_membership = AsyncMock(return_value=None)
                mock_company_cls.return_value = mock_company

                mock_user_cls.return_value = AsyncMock()

                mock_inv = AsyncMock()
                mock_inv.get_pending_for_email = AsyncMock(
                    side_effect=lambda email: [existing_inv] if email == "alice@acme.com" else []
                )
                mock_inv.create_bulk = AsyncMock(return_value=[])
                mock_inv_cls.return_value = mock_inv

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        "/v1/invitations",
                        json={"emails": ["alice@acme.com", "bob@acme.com"]},
                        headers=_make_jwt_header(user_id),
                    )

        assert response.status_code == 207
        body = response.json()
        failed_emails = {f["email"] for f in body["failed"]}
        assert "alice@acme.com" in failed_emails
        reason = next(f["reason"] for f in body["failed"] if f["email"] == "alice@acme.com")
        assert reason == "already_invited"

    def test_returns_403_when_caller_is_not_admin(self):
        user_id = uuid.uuid4()

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.invitations.get_db") as mock_get_db,
                patch("tessera_api.routers.invitations.SqlCompanyRepository") as mock_company_cls,
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_company = AsyncMock()
                mock_company.list_memberships_for_user = AsyncMock(return_value=[])
                mock_company_cls.return_value = mock_company

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        "/v1/invitations",
                        json={"emails": ["alice@acme.com"]},
                        headers=_make_jwt_header(user_id),
                    )

        assert response.status_code == 403

    def test_returns_422_when_emails_empty(self):
        user_id = uuid.uuid4()

        with _bypass_onboarding_guard():
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/invitations",
                    json={"emails": []},
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 422

    def test_returns_422_when_email_invalid(self):
        user_id = uuid.uuid4()

        with _bypass_onboarding_guard():
            from fastapi.testclient import TestClient
            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.post(
                    "/v1/invitations",
                    json={"emails": ["not-an-email"]},
                    headers=_make_jwt_header(user_id),
                )

        assert response.status_code == 422

    def test_returns_401_when_no_auth(self):
        from fastapi.testclient import TestClient
        from tessera_api.main import app

        with TestClient(app) as client:
            response = client.post(
                "/v1/invitations",
                json={"emails": ["alice@acme.com"]},
            )

        assert response.status_code == 401

    def test_deduplicates_email_list(self):
        user_id = uuid.uuid4()
        company_id = uuid.uuid4()
        company = _make_company(user_id, company_id)
        membership = _admin_membership(user_id, company_id)

        with _bypass_onboarding_guard():
            with (
                patch("tessera_api.routers.invitations.get_db") as mock_get_db,
                patch("tessera_api.routers.invitations.SqlCompanyRepository") as mock_company_cls,
                patch("tessera_api.routers.invitations.SqlInvitationRepository") as mock_inv_cls,
                patch("tessera_api.routers.invitations.SqlUserRepository") as mock_user_cls,
                patch("tessera_api.routers.invitations.write_audit", new_callable=AsyncMock),
                patch("tessera_api.routers.invitations.send_invitation_email", new_callable=AsyncMock),
            ):
                session = AsyncMock()
                mock_get_db.return_value.__aenter__ = AsyncMock(return_value=session)
                mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_company = AsyncMock()
                mock_company.list_memberships_for_user = AsyncMock(return_value=[membership])
                mock_company.get_by_id = AsyncMock(return_value=company)
                mock_company.get_membership = AsyncMock(return_value=None)
                mock_company_cls.return_value = mock_company

                mock_user_cls.return_value = AsyncMock()

                mock_inv = AsyncMock()
                mock_inv.get_pending_for_email = AsyncMock(return_value=[])
                mock_inv.create_bulk = AsyncMock(return_value=[])
                mock_inv_cls.return_value = mock_inv

                from fastapi.testclient import TestClient
                from tessera_api.main import app

                with TestClient(app) as client:
                    response = client.post(
                        "/v1/invitations",
                        json={"emails": ["alice@acme.com", "alice@acme.com"]},
                        headers=_make_jwt_header(user_id),
                    )

        assert response.status_code == 207
        body = response.json()
        assert body["sent"].count("alice@acme.com") == 1
