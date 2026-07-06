"""Feature 054 (T023, US3): invitation acceptance grants the invitation's role.

``POST /v1/companies/{id}/join`` (method="invitation") must create the membership
with ``invitation.role`` instead of a hard-coded MEMBER, so an admin-role invite
makes the acceptor an administrator. A member/legacy invitation still yields MEMBER.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

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


def _run_join(company_id: uuid.UUID, invitation: Invitation):
    from tessera_api.auth.jwt_auth import create_access_token
    from tessera_api.main import app

    user_id = uuid.uuid4()
    token = create_access_token(user_id, "invitee@x.com", False)

    company_repo = AsyncMock()
    company_repo.get_by_id = AsyncMock(
        return_value=Company(id=company_id, name="Acme", admin_user_id=uuid.uuid4())
    )
    company_repo.get_membership = AsyncMock(return_value=None)
    company_repo.add_membership = AsyncMock(
        side_effect=lambda m: CompanyMembership(
            id=uuid.uuid4(),
            user_id=m.user_id,
            company_id=m.company_id,
            role=m.role,
            joined_at=datetime.now(UTC),
        )
    )

    inv_repo = AsyncMock()
    inv_repo.get_by_id = AsyncMock(return_value=invitation)
    inv_repo.update_status = AsyncMock()

    ob_repo = AsyncMock()

    with _bypass_onboarding_guard():
        with (
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlInvitationRepository", return_value=inv_repo),
            patch("tessera_api.routers.companies.SqlOnboardingRepository", return_value=ob_repo),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            with TestClient(app) as client:
                resp = client.post(
                    f"/v1/companies/{company_id}/join",
                    json={"method": "invitation", "invitation_id": str(invitation.id)},
                    headers={"Authorization": f"Bearer {token}"},
                )
    return resp, company_repo


def _invitation(company_id: uuid.UUID, role: CompanyRole) -> Invitation:
    return Invitation(
        company_id=company_id,
        email="invitee@x.com",
        token_hash="a" * 64,
        status=InvitationStatus.PENDING,
        role=role,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )


def test_admin_invitation_grants_admin_role():
    company_id = uuid.uuid4()
    resp, company_repo = _run_join(company_id, _invitation(company_id, CompanyRole.ADMIN))

    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "admin"
    assert company_repo.add_membership.await_args.args[0].role == CompanyRole.ADMIN


def test_member_invitation_grants_member_role():
    company_id = uuid.uuid4()
    resp, company_repo = _run_join(company_id, _invitation(company_id, CompanyRole.MEMBER))

    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "member"
    assert company_repo.add_membership.await_args.args[0].role == CompanyRole.MEMBER
