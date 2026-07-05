"""Unit/contract tests for GET /v1/companies/members (feature 053).

Covers:
- US1: an admin of the active company receives the roster (200).
- US2: a non-admin member receives 403 and no roster; an unauthenticated
  caller receives 401 and no roster.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from tessera_core.domain.entities import CompanyMemberListing, CompanyMembership, CompanyRole


@contextmanager
def _bypass_onboarding_guard():
    """Override require_onboarding_complete to skip the DB check in these tests."""
    from tessera_api.auth.bearer import require_onboarding_complete
    from tessera_api.main import app

    async def _noop():
        return None

    app.dependency_overrides[require_onboarding_complete] = _noop
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_onboarding_complete, None)


def _admin_ctx(actor_id: uuid.UUID, company_id: uuid.UUID) -> tuple:
    membership = CompanyMembership(
        id=uuid.uuid4(),
        user_id=actor_id,
        company_id=company_id,
        role=CompanyRole.ADMIN,
        joined_at=datetime.now(UTC),
    )
    return ({"sub": str(actor_id), "id": str(actor_id), "is_admin": False}, company_id, membership)


class TestListCompanyMembersContract:
    """GET /v1/companies/members — the active company's roster (admin only)."""

    @pytest.mark.anyio
    async def test_admin_receives_roster_with_roles(self):
        from tessera_api.routers.companies import list_company_members

        company_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _admin_ctx(actor_id, company_id)

        ada_id = uuid.uuid4()
        grace_id = uuid.uuid4()
        mock_company_repo = AsyncMock()
        mock_company_repo.list_members.return_value = [
            CompanyMemberListing(
                user_id=ada_id,
                display_name="Ada Lovelace",
                email="ada@acme.example",
                role=CompanyRole.ADMIN,
            ),
            CompanyMemberListing(
                user_id=grace_id,
                display_name="Grace Hopper",
                email="grace@acme.example",
                role=CompanyRole.MEMBER,
            ),
        ]

        with patch(
            "tessera_api.routers.companies.SqlCompanyRepository",
            return_value=mock_company_repo,
        ):
            result = await list_company_members(ctx, session)

        assert result == {
            "members": [
                {
                    "user_id": str(ada_id),
                    "display_name": "Ada Lovelace",
                    "email": "ada@acme.example",
                    "role": "admin",
                },
                {
                    "user_id": str(grace_id),
                    "display_name": "Grace Hopper",
                    "email": "grace@acme.example",
                    "role": "member",
                },
            ]
        }
        # The roster is derived from the authenticated company context only.
        mock_company_repo.list_members.assert_awaited_once_with(company_id)

    @pytest.mark.anyio
    async def test_admin_of_empty_company_receives_empty_list(self):
        from tessera_api.routers.companies import list_company_members

        company_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _admin_ctx(actor_id, company_id)

        mock_company_repo = AsyncMock()
        mock_company_repo.list_members.return_value = []

        with patch(
            "tessera_api.routers.companies.SqlCompanyRepository",
            return_value=mock_company_repo,
        ):
            result = await list_company_members(ctx, session)

        assert result == {"members": []}

    def test_non_admin_member_forbidden_no_roster(self, two_company_setup):
        """US2: a non-admin member of the active company → 403, no roster in body."""
        token_a, company_a_id, _token_b, _company_b_id = two_company_setup

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository") as mock_repo_cls,
        ):
            mock_repo = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.get(
                    "/v1/companies/members",
                    headers={"Authorization": f"Bearer {token_a}"},
                )

        assert response.status_code == 403
        assert "members" not in response.json()
        # The roster query is never reached for a non-admin.
        mock_repo.list_members.assert_not_awaited()

    def test_unauthenticated_caller_unauthorized_no_roster(self):
        """US2: an unauthenticated caller → 401, no roster in body."""
        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository") as mock_repo_cls,
        ):
            mock_repo = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.get("/v1/companies/members")

        assert response.status_code == 401
        assert "members" not in response.json()
        mock_repo.list_members.assert_not_awaited()
