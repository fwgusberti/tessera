"""Contract tests for GET /v1/companies/members/{user_id}/space-access (feature 058).

Admin-gated member-centric space access view. The endpoint lives on the
``companies`` router, derives ``company_id`` solely from ``CompanyAdminContext``,
and assembles its response via the core ``MemberAccessService``. These tests
drive it through ``TestClient`` and patch the router's module-level repository
imports.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from tessera_core.domain.entities import (
    CompanyMembership,
    CompanyRole,
    Space,
    SpaceMembership,
    SpaceRole,
    User,
)
from tessera_core.domain.space_access import SpaceAccess

_GENERIC_NOT_FOUND = {"error": {"code": "not_found", "message": "Not found"}}
_GENERIC_FORBIDDEN = {"error": {"code": "forbidden", "message": "Access denied"}}


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


def _space(company_id: uuid.UUID, name: str, parent_id: uuid.UUID | None = None) -> Space:
    return Space(
        id=uuid.uuid4(),
        slug=f"sp-{uuid.uuid4().hex[:6]}",
        name=name,
        sector="tech",
        company_id=company_id,
        parent_space_id=parent_id,
    )


def _user(user_id: uuid.UUID, email: str = "member@acme.test", name: str = "Member") -> User:
    return User(
        id=user_id,
        external_subject=f"sub-{user_id}",
        email=email,
        display_name=name,
        is_admin=False,
    )


def _company_membership(user_id: uuid.UUID, company_id: uuid.UUID) -> CompanyMembership:
    return CompanyMembership(
        id=uuid.uuid4(),
        user_id=user_id,
        company_id=company_id,
        role=CompanyRole.MEMBER,
        joined_at=datetime.now(UTC),
    )


class TestMemberSpaceAccessContract:
    def test_200_response_shape_per_contract(self, admin_company_setup):
        """member + spaces[] rows carrying direct_role / effective_role / is_direct."""
        token_a, company_a_id, _tb, _cb = admin_company_setup
        target_id = uuid.uuid4()

        parent = _space(company_a_id, "Engineering")
        child = _space(company_a_id, "Docs", parent_id=parent.id)
        finance = _space(company_a_id, "Finance")

        company_repo = AsyncMock()
        company_repo.get_membership = AsyncMock(
            return_value=_company_membership(target_id, company_a_id)
        )

        user_repo = AsyncMock()
        user_repo.get_by_id = AsyncMock(
            return_value=_user(target_id, "eng@acme.test", "Eng Member")
        )

        space_repo = AsyncMock()
        space_repo.list_by_company = AsyncMock(return_value=[parent, child, finance])
        space_repo.list_accessible_by_user = AsyncMock(
            return_value=[
                SpaceAccess(space=parent, effective_role=SpaceRole.VIEWER, is_direct=True),
                SpaceAccess(space=child, effective_role=SpaceRole.VIEWER, is_direct=False),
            ]
        )

        membership_repo = AsyncMock()
        membership_repo.list_by_user = AsyncMock(
            return_value=[
                SpaceMembership(space_id=parent.id, user_id=target_id, role=SpaceRole.VIEWER)
            ]
        )

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.SqlSpaceRepository", return_value=space_repo),
            patch(
                "tessera_api.routers.companies.SqlSpaceMembershipRepository",
                return_value=membership_repo,
            ),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.get(
                    f"/v1/companies/members/{target_id}/space-access",
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["member"] == {
            "user_id": str(target_id),
            "display_name": "Eng Member",
            "email": "eng@acme.test",
        }

        rows = {r["id"]: r for r in body["spaces"]}
        assert set(rows) == {str(parent.id), str(child.id), str(finance.id)}
        for row in body["spaces"]:
            assert set(row.keys()) == {
                "id",
                "name",
                "slug",
                "parent_space_id",
                "direct_role",
                "effective_role",
                "is_direct",
            }

        direct_row = rows[str(parent.id)]
        assert direct_row["direct_role"] == "viewer"
        assert direct_row["effective_role"] == "viewer"
        assert direct_row["is_direct"] is True
        assert direct_row["parent_space_id"] is None

        inherited_row = rows[str(child.id)]
        assert inherited_row["direct_role"] is None
        assert inherited_row["effective_role"] == "viewer"
        assert inherited_row["is_direct"] is False
        assert inherited_row["parent_space_id"] == str(parent.id)

        none_row = rows[str(finance.id)]
        assert none_row["direct_role"] is None
        assert none_row["effective_role"] is None
        assert none_row["is_direct"] is False

        # tenant scoping: every space query used the context company id
        space_repo.list_by_company.assert_awaited_once_with(company_a_id)
        space_repo.list_accessible_by_user.assert_awaited_once_with(target_id, company_a_id)

    def test_non_admin_caller_gets_403(self, two_company_setup):
        """CompanyAdminContext gate: a plain member is refused with the generic body."""
        token_a, _ca, _tb, _cb = two_company_setup
        target_id = uuid.uuid4()

        with _bypass_onboarding_guard():
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.get(
                    f"/v1/companies/members/{target_id}/space-access",
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 403
        assert resp.json() == _GENERIC_FORBIDDEN

    def test_user_not_in_company_gets_generic_404(self, admin_company_setup):
        """A user_id with no membership in the active company is indistinguishable from absent."""
        token_a, _ca, _tb, _cb = admin_company_setup
        target_id = uuid.uuid4()

        company_repo = AsyncMock()
        company_repo.get_membership = AsyncMock(return_value=None)

        user_repo = AsyncMock()
        user_repo.get_by_id = AsyncMock(return_value=None)  # no such user at all

        space_repo = AsyncMock()

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository", return_value=company_repo),
            patch("tessera_api.routers.companies.SqlUserRepository", return_value=user_repo),
            patch("tessera_api.routers.companies.SqlSpaceRepository", return_value=space_repo),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            from tessera_api.main import app

            with TestClient(app) as client:
                resp = client.get(
                    f"/v1/companies/members/{target_id}/space-access",
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert resp.status_code == 404
        assert resp.json() == _GENERIC_NOT_FOUND
        # no space data was read for a non-member target
        space_repo.list_by_company.assert_not_awaited()
        space_repo.list_accessible_by_user.assert_not_awaited()
