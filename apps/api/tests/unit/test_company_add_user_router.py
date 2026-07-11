"""Contract tests for the feature-054 add-user endpoints (companies router).

All three endpoints live on the ``companies`` router, are gated by
``CompanyAdminContext``, and derive ``company_id`` solely from the authenticated
context. These tests drive them through ``TestClient`` with the ``admin_company_setup``
fixture (Alice = ADMIN of Company A) and mock the router's repositories.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

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


def _company(company_id: uuid.UUID) -> Company:
    return Company(id=company_id, name="Acme Corp", admin_user_id=uuid.uuid4())


def _user(
    user_id: uuid.UUID | None = None, email: str = "target@acme.test", name: str = "Target User"
):
    from tessera_core.domain.entities import User

    return User(
        id=user_id or uuid.uuid4(),
        external_subject=f"sub-{uuid.uuid4()}",
        email=email,
        display_name=name,
        is_admin=False,
    )


def _membership(user_id: uuid.UUID, company_id: uuid.UUID, role: CompanyRole = CompanyRole.MEMBER):
    return CompanyMembership(
        id=uuid.uuid4(),
        user_id=user_id,
        company_id=company_id,
        role=role,
        joined_at=datetime.now(UTC),
    )


def _pending_invitation(company_id: uuid.UUID, email: str) -> Invitation:
    return Invitation(
        company_id=company_id,
        email=email,
        token_hash="a" * 64,
        status=InvitationStatus.PENDING,
        expires_at=datetime.now(UTC),
    )


def _integrity_error() -> IntegrityError:
    return IntegrityError("stmt", {}, Exception("duplicate key"))


def _ob_repo() -> AsyncMock:
    """OnboardingProgress repo mock for the add-member completion step (T010).

    ``get_by_user_id`` returns None so the handler exercises the create branch; the
    remaining calls (``create``/``advance_step``/``complete``) are recorded for
    assertions and their return values are unused by the endpoint.
    """
    repo = AsyncMock()
    repo.get_by_user_id = AsyncMock(return_value=None)
    return repo


# ---------------------------------------------------------------------------
# US1 — POST /v1/companies/invitations (invite by email)
# ---------------------------------------------------------------------------


class TestInviteByEmailContract:
    def test_invite_success_returns_sent_and_audits(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup

        company_repo = AsyncMock()
        company_repo.get_by_id = AsyncMock(return_value=_company(company_a_id))
        company_repo.get_membership = AsyncMock(return_value=None)

        user_repo = AsyncMock()
        user_repo.get_by_email = AsyncMock(return_value=None)  # not yet registered
        user_repo.get_by_id = AsyncMock(return_value=_user(name="Alice Admin"))

        created = _pending_invitation(company_a_id, "new.person@x.com")
        inv_repo = AsyncMock()
        inv_repo.get_pending_for_email = AsyncMock(return_value=[])
        inv_repo.create = AsyncMock(return_value=created)

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.SqlInvitationRepository", return_value=inv_repo),
            patch(
                "tessera_api.routers.companies.send_invitation_email", new_callable=AsyncMock
            ) as mock_send,
            patch(
                "tessera_api.routers.companies.write_audit", new_callable=AsyncMock
            ) as mock_audit,
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.post(
                    "/v1/companies/invitations",
                    json={"email": "new.person@x.com"},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body == {"status": "sent", "email": "new.person@x.com", "role": "member"}
        mock_send.assert_awaited_once()
        # invitation was bound to the context company id
        assert inv_repo.create.await_args.args[0].company_id == company_a_id
        # audit invitation.sent written
        actions = [c.kwargs.get("action") for c in mock_audit.await_args_list]
        assert "invitation.sent" in actions

    def test_invite_existing_member_returns_409_already_member(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup
        target = _user(email="member@x.com")

        company_repo = AsyncMock()
        company_repo.get_membership = AsyncMock(return_value=_membership(target.id, company_a_id))

        user_repo = AsyncMock()
        user_repo.get_by_email = AsyncMock(return_value=target)

        inv_repo = AsyncMock()

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.SqlInvitationRepository", return_value=inv_repo),
            patch(
                "tessera_api.routers.companies.send_invitation_email", new_callable=AsyncMock
            ) as mock_send,
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.post(
                    "/v1/companies/invitations",
                    json={"email": "member@x.com"},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "already_member"
        mock_send.assert_not_awaited()

    def test_invite_existing_pending_returns_409_already_invited(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup

        company_repo = AsyncMock()
        company_repo.get_membership = AsyncMock(return_value=None)

        user_repo = AsyncMock()
        user_repo.get_by_email = AsyncMock(return_value=None)

        inv_repo = AsyncMock()
        inv_repo.get_pending_for_email = AsyncMock(
            return_value=[_pending_invitation(company_a_id, "dup@x.com")]
        )

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.SqlInvitationRepository", return_value=inv_repo),
            patch(
                "tessera_api.routers.companies.send_invitation_email", new_callable=AsyncMock
            ) as mock_send,
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.post(
                    "/v1/companies/invitations",
                    json={"email": "dup@x.com"},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "already_invited"
        mock_send.assert_not_awaited()

    def test_invite_race_integrity_error_maps_to_409_already_invited(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup

        company_repo = AsyncMock()
        company_repo.get_by_id = AsyncMock(return_value=_company(company_a_id))
        company_repo.get_membership = AsyncMock(return_value=None)

        user_repo = AsyncMock()
        user_repo.get_by_email = AsyncMock(return_value=None)
        user_repo.get_by_id = AsyncMock(return_value=_user())

        inv_repo = AsyncMock()
        inv_repo.get_pending_for_email = AsyncMock(return_value=[])
        inv_repo.create = AsyncMock(side_effect=_integrity_error())

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.SqlInvitationRepository", return_value=inv_repo),
            patch(
                "tessera_api.routers.companies.send_invitation_email", new_callable=AsyncMock
            ) as mock_send,
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.post(
                    "/v1/companies/invitations",
                    json={"email": "racer@x.com"},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "already_invited"
        mock_send.assert_not_awaited()

    def test_invite_malformed_email_returns_422_and_sends_nothing(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=AsyncMock()),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=AsyncMock()),
            patch(
                "tessera_api.routers.companies.SqlInvitationRepository",
                return_value=AsyncMock(),
            ),
            patch(
                "tessera_api.routers.companies.send_invitation_email", new_callable=AsyncMock
            ) as mock_send,
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.post(
                    "/v1/companies/invitations",
                    json={"email": "not-an-email"},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 422
        mock_send.assert_not_awaited()

    def test_invite_send_failure_returns_502_send_failed(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup

        company_repo = AsyncMock()
        company_repo.get_by_id = AsyncMock(return_value=_company(company_a_id))
        company_repo.get_membership = AsyncMock(return_value=None)

        user_repo = AsyncMock()
        user_repo.get_by_email = AsyncMock(return_value=None)
        user_repo.get_by_id = AsyncMock(return_value=_user())

        created = _pending_invitation(company_a_id, "fail@x.com")
        inv_repo = AsyncMock()
        inv_repo.get_pending_for_email = AsyncMock(return_value=[])
        inv_repo.create = AsyncMock(return_value=created)

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.SqlInvitationRepository", return_value=inv_repo),
            patch(
                "tessera_api.routers.companies.send_invitation_email",
                new=AsyncMock(side_effect=RuntimeError("smtp down")),
            ),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.post(
                    "/v1/companies/invitations",
                    json={"email": "fail@x.com"},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 502
        assert resp.json()["error"]["code"] == "send_failed"
        # the invitation row was created before the send was attempted
        inv_repo.create.assert_awaited_once()


# ---------------------------------------------------------------------------
# US2 — GET /v1/companies/addable-users (directory search)
# ---------------------------------------------------------------------------


class TestAddableUsersContract:
    def test_search_returns_identity_matches(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup
        from tessera_core.domain.company_member_match import CompanyMemberMatch

        match_id = uuid.uuid4()
        company_repo = AsyncMock()
        company_repo.search_addable_users = AsyncMock(
            return_value=[
                CompanyMemberMatch(user_id=match_id, display_name="Ada Lovelace", email="ada@x.com")
            ]
        )

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.get(
                    "/v1/companies/addable-users?q=ada",
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 200, resp.text
        assert resp.json() == {
            "users": [
                {"user_id": str(match_id), "display_name": "Ada Lovelace", "email": "ada@x.com"}
            ]
        }
        # search is scoped to the context company id, from context only
        company_repo.search_addable_users.assert_awaited_once()
        assert company_repo.search_addable_users.await_args.args[0] == company_a_id

    def test_short_query_returns_422(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=AsyncMock()),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.get(
                    "/v1/companies/addable-users?q=a",
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 422

    def test_missing_query_returns_422(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=AsyncMock()),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.get(
                    "/v1/companies/addable-users",
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# US2 — POST /v1/companies/members (direct add)
# ---------------------------------------------------------------------------


class TestAddMemberContract:
    def test_add_member_success_returns_member_and_audits(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup
        target = _user(email="ada@x.com", name="Ada Lovelace")

        company_repo = AsyncMock()
        company_repo.get_membership = AsyncMock(return_value=None)
        company_repo.add_membership = AsyncMock(
            return_value=_membership(target.id, company_a_id, CompanyRole.MEMBER)
        )

        user_repo = AsyncMock()
        user_repo.get_by_id = AsyncMock(return_value=target)

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.SqlOnboardingRepository", return_value=_ob_repo()),
            patch(
                "tessera_api.routers.companies.write_audit", new_callable=AsyncMock
            ) as mock_audit,
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.post(
                    "/v1/companies/members",
                    json={"user_id": str(target.id)},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 201, resp.text
        assert resp.json() == {
            "member": {
                "user_id": str(target.id),
                "display_name": "Ada Lovelace",
                "email": "ada@x.com",
                "role": "member",
            }
        }
        # membership was bound to the context company id
        assert company_repo.add_membership.await_args.args[0].company_id == company_a_id
        actions = [c.kwargs.get("action") for c in mock_audit.await_args_list]
        assert "company.member_added" in actions

    def test_add_member_persists_onboarding_completion_and_audits(self, admin_company_setup):
        """T007/US1 (contract C4): a direct add marks the target onboarded + audits it.

        After ``POST /v1/companies/members`` the target's OnboardingProgress is marked
        complete with ``company_join_method="added"`` and ``company_id`` = the active
        company, and an ``onboarding.completed`` audit record is written for the target.
        """
        token_a, company_a_id, _tb, _cb = admin_company_setup
        target = _user(email="ada@x.com", name="Ada Lovelace")

        company_repo = AsyncMock()
        company_repo.get_membership = AsyncMock(return_value=None)
        company_repo.add_membership = AsyncMock(
            return_value=_membership(target.id, company_a_id, CompanyRole.MEMBER)
        )
        user_repo = AsyncMock()
        user_repo.get_by_id = AsyncMock(return_value=target)
        ob_repo = _ob_repo()

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.SqlOnboardingRepository", return_value=ob_repo),
            patch(
                "tessera_api.routers.companies.write_audit", new_callable=AsyncMock
            ) as mock_audit,
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.post(
                    "/v1/companies/members",
                    json={"user_id": str(target.id)},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 201, resp.text

        # Onboarding marked complete for the TARGET, scoped to the active company.
        ob_repo.advance_step.assert_awaited_once()
        step_args = ob_repo.advance_step.await_args
        assert step_args.args[0] == target.id
        assert step_args.args[1] == "complete"
        assert step_args.kwargs["company_join_method"] == "added"
        assert step_args.kwargs["company_id"] == company_a_id
        ob_repo.complete.assert_awaited_once_with(target.id)

        # An onboarding.completed audit record was written for the target user.
        completed_audits = [
            c
            for c in mock_audit.await_args_list
            if c.kwargs.get("action") == "onboarding.completed"
        ]
        assert len(completed_audits) == 1, "expected exactly one onboarding.completed audit"
        assert completed_audits[0].kwargs["entity_type"] == "user"
        assert completed_audits[0].kwargs["entity_id"] == target.id

    def test_add_unknown_user_returns_404_no_such_user(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup

        company_repo = AsyncMock()
        company_repo.get_membership = AsyncMock(return_value=None)
        company_repo.add_membership = AsyncMock()

        user_repo = AsyncMock()
        user_repo.get_by_id = AsyncMock(return_value=None)

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.post(
                    "/v1/companies/members",
                    json={"user_id": str(uuid.uuid4())},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "no_such_user"
        company_repo.add_membership.assert_not_awaited()

    def test_add_existing_member_returns_409_already_member(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup
        target = _user()

        company_repo = AsyncMock()
        company_repo.get_membership = AsyncMock(return_value=_membership(target.id, company_a_id))
        company_repo.add_membership = AsyncMock()

        user_repo = AsyncMock()
        user_repo.get_by_id = AsyncMock(return_value=target)

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.post(
                    "/v1/companies/members",
                    json={"user_id": str(target.id)},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "already_member"
        company_repo.add_membership.assert_not_awaited()

    def test_add_member_race_integrity_error_maps_to_409(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup
        target = _user()

        company_repo = AsyncMock()
        company_repo.get_membership = AsyncMock(return_value=None)
        company_repo.add_membership = AsyncMock(side_effect=_integrity_error())

        user_repo = AsyncMock()
        user_repo.get_by_id = AsyncMock(return_value=target)

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.post(
                    "/v1/companies/members",
                    json={"user_id": str(target.id)},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "already_member"

    def test_add_member_invalid_role_returns_422(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=AsyncMock()),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=AsyncMock()),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.post(
                    "/v1/companies/members",
                    json={"user_id": str(uuid.uuid4()), "role": "superuser"},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# US3 — the admin-chosen role flows through both add paths
# ---------------------------------------------------------------------------


class TestRoleChoiceContract:
    def test_add_member_with_admin_role_creates_admin(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup
        target = _user()

        company_repo = AsyncMock()
        company_repo.get_membership = AsyncMock(return_value=None)
        company_repo.add_membership = AsyncMock(
            return_value=_membership(target.id, company_a_id, CompanyRole.ADMIN)
        )
        user_repo = AsyncMock()
        user_repo.get_by_id = AsyncMock(return_value=target)

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.SqlOnboardingRepository", return_value=_ob_repo()),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.post(
                    "/v1/companies/members",
                    json={"user_id": str(target.id), "role": "admin"},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 201, resp.text
        assert resp.json()["member"]["role"] == "admin"
        assert company_repo.add_membership.await_args.args[0].role == CompanyRole.ADMIN

    def test_add_member_defaults_to_member_role(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup
        target = _user()

        company_repo = AsyncMock()
        company_repo.get_membership = AsyncMock(return_value=None)
        company_repo.add_membership = AsyncMock(
            return_value=_membership(target.id, company_a_id, CompanyRole.MEMBER)
        )
        user_repo = AsyncMock()
        user_repo.get_by_id = AsyncMock(return_value=target)

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.SqlOnboardingRepository", return_value=_ob_repo()),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.post(
                    "/v1/companies/members",
                    json={"user_id": str(target.id)},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 201
        assert company_repo.add_membership.await_args.args[0].role == CompanyRole.MEMBER

    def test_invite_with_admin_role_persists_admin_on_invitation(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup

        company_repo = AsyncMock()
        company_repo.get_by_id = AsyncMock(return_value=_company(company_a_id))
        company_repo.get_membership = AsyncMock(return_value=None)
        user_repo = AsyncMock()
        user_repo.get_by_email = AsyncMock(return_value=None)
        user_repo.get_by_id = AsyncMock(return_value=_user())
        inv_repo = AsyncMock()
        inv_repo.get_pending_for_email = AsyncMock(return_value=[])
        inv_repo.create = AsyncMock(side_effect=lambda inv: inv)

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.SqlInvitationRepository", return_value=inv_repo),
            patch("tessera_api.routers.companies.send_invitation_email", new_callable=AsyncMock),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.post(
                    "/v1/companies/invitations",
                    json={"email": "admin.invite@x.com", "role": "admin"},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 201, resp.text
        assert resp.json()["role"] == "admin"
        assert inv_repo.create.await_args.args[0].role == CompanyRole.ADMIN

    def test_invite_defaults_to_member_role(self, admin_company_setup):
        token_a, company_a_id, _tb, _cb = admin_company_setup

        company_repo = AsyncMock()
        company_repo.get_by_id = AsyncMock(return_value=_company(company_a_id))
        company_repo.get_membership = AsyncMock(return_value=None)
        user_repo = AsyncMock()
        user_repo.get_by_email = AsyncMock(return_value=None)
        user_repo.get_by_id = AsyncMock(return_value=_user())
        inv_repo = AsyncMock()
        inv_repo.get_pending_for_email = AsyncMock(return_value=[])
        inv_repo.create = AsyncMock(side_effect=lambda inv: inv)

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.SqlInvitationRepository", return_value=inv_repo),
            patch("tessera_api.routers.companies.send_invitation_email", new_callable=AsyncMock),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.post(
                    "/v1/companies/invitations",
                    json={"email": "member.invite@x.com"},
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 201
        assert resp.json()["role"] == "member"
        assert inv_repo.create.await_args.args[0].role == CompanyRole.MEMBER


# ---------------------------------------------------------------------------
# US4 — all three endpoints are admin-only and derive company_id from context
# ---------------------------------------------------------------------------

_ENDPOINTS = [
    ("GET", "/v1/companies/addable-users?q=ab", None),
    ("POST", "/v1/companies/members", {"user_id": str(uuid.uuid4())}),
    ("POST", "/v1/companies/invitations", {"email": "x@y.com"}),
]


class TestAuthGating:
    def test_non_admin_member_gets_403_no_write(self, two_company_setup):
        # two_company_setup makes the caller an ordinary MEMBER of Company A.
        token_a, company_a_id, _tb, _cb = two_company_setup

        for method, path, body in _ENDPOINTS:
            company_repo = AsyncMock()
            with (
                _bypass_onboarding_guard(),
                patch(
                    "tessera_api.routers.companies.SqlCompanyRepository",
                    return_value=company_repo,
                ),
                patch("tessera_api.routers.companies.SqlUserRepository", return_value=AsyncMock()),
                patch(
                    "tessera_api.routers.companies.SqlInvitationRepository",
                    return_value=AsyncMock(),
                ),
                patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
            ):
                from tessera_api.main import app

                with TestClient(app) as client:
                    resp = client.request(
                        method,
                        path,
                        json=body,
                        headers={"Authorization": f"Bearer {token_a}"},
                    )

            assert resp.status_code == 403, f"{method} {path} -> {resp.status_code}"
            # The admin gate rejects before the handler runs — no membership/invite write.
            company_repo.add_membership.assert_not_awaited()
            company_repo.search_addable_users.assert_not_awaited()

    def test_unauthenticated_gets_401(self):
        from tessera_api.main import app

        for method, path, body in _ENDPOINTS:
            with _bypass_onboarding_guard(), TestClient(app) as client:
                resp = client.request(method, path, json=body)
            assert resp.status_code == 401, f"{method} {path} -> {resp.status_code}"
