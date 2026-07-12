"""Unit/contract tests for GET/PATCH /v1/companies/current (feature 060).

Covers:
- US1: any member reads the active company's full profile with their role.
- US2: an admin updates name/industry/team_size with validation + audit.
- US3: a non-admin member's PATCH is refused before any repository write.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from tessera_core.domain.entities import Company, CompanyMembership, CompanyRole


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


def _ctx(actor_id: uuid.UUID, company_id: uuid.UUID, role: CompanyRole) -> tuple:
    membership = CompanyMembership(
        id=uuid.uuid4(),
        user_id=actor_id,
        company_id=company_id,
        role=role,
        joined_at=datetime.now(UTC),
    )
    return ({"sub": str(actor_id), "id": str(actor_id), "is_admin": False}, company_id, membership)


def _company(company_id: uuid.UUID, **overrides) -> Company:
    defaults = dict(
        id=company_id,
        name="Acme Corp",
        industry="Technology",
        team_size="11-50",
        admin_user_id=uuid.uuid4(),
        created_at=datetime(2026, 3, 14, 9, 26, 53, tzinfo=UTC),
        updated_at=datetime(2026, 3, 14, 9, 26, 53, tzinfo=UTC),
    )
    defaults.update(overrides)
    return Company(**defaults)


class TestGetCurrentCompanyContract:
    """GET /v1/companies/current — the active company's profile (any member)."""

    @pytest.mark.anyio
    async def test_admin_receives_full_profile_with_admin_role(self):
        from tessera_api.routers.companies import get_current_company

        company_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id, company_id, CompanyRole.ADMIN)

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = _company(company_id)

        with patch(
            "tessera_api.routers.companies.SqlCompanyRepository",
            return_value=mock_repo,
        ):
            result = await get_current_company(ctx, session)

        assert result.id == str(company_id)
        assert result.name == "Acme Corp"
        assert result.industry == "Technology"
        assert result.team_size == "11-50"
        assert result.created_at == datetime(2026, 3, 14, 9, 26, 53, tzinfo=UTC)
        assert result.role == "admin"
        # The company id comes only from the authenticated context.
        mock_repo.get_by_id.assert_awaited_once_with(company_id)

    @pytest.mark.anyio
    async def test_plain_member_receives_profile_with_member_role(self):
        from tessera_api.routers.companies import get_current_company

        company_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id, company_id, CompanyRole.MEMBER)

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = _company(company_id)

        with patch(
            "tessera_api.routers.companies.SqlCompanyRepository",
            return_value=mock_repo,
        ):
            result = await get_current_company(ctx, session)

        assert result.role == "member"
        assert result.name == "Acme Corp"

    @pytest.mark.anyio
    async def test_unset_optionals_are_returned_as_null(self):
        from tessera_api.routers.companies import get_current_company

        company_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id, company_id, CompanyRole.MEMBER)

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = _company(company_id, industry=None, team_size=None)

        with patch(
            "tessera_api.routers.companies.SqlCompanyRepository",
            return_value=mock_repo,
        ):
            result = await get_current_company(ctx, session)

        assert result.industry is None
        assert result.team_size is None


class TestPatchCurrentCompanyContract:
    """PATCH /v1/companies/current — admin-only profile update with audit."""

    @pytest.mark.anyio
    async def test_happy_path_returns_saved_profile_and_writes_audit(self):
        from tessera_api.routers.companies import UpdateCompanyRequest, update_current_company

        company_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id, company_id, CompanyRole.ADMIN)

        old = _company(company_id, name="Acme Corp", industry="Technology", team_size="11-50")
        saved = _company(
            company_id, name="Acme Corporation", industry="Technology", team_size="51-200"
        )

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = old
        mock_repo.update_details.return_value = saved

        body = UpdateCompanyRequest(
            name="Acme Corporation", industry="Technology", team_size="51-200"
        )

        with (
            patch(
                "tessera_api.routers.companies.SqlCompanyRepository",
                return_value=mock_repo,
            ),
            patch(
                "tessera_api.routers.companies.write_audit", new_callable=AsyncMock
            ) as mock_audit,
        ):
            result = await update_current_company(body, ctx, session)

        assert result.name == "Acme Corporation"
        assert result.team_size == "51-200"
        assert result.role == "admin"
        mock_repo.update_details.assert_awaited_once_with(
            company_id,
            name="Acme Corporation",
            industry="Technology",
            team_size="51-200",
        )

        mock_audit.assert_awaited_once()
        audit_kwargs = mock_audit.await_args.kwargs
        assert audit_kwargs["action"] == "company.updated"
        assert audit_kwargs["entity_type"] == "company"
        assert audit_kwargs["entity_id"] == company_id
        changed = audit_kwargs["metadata"]["changed"]
        # Only actually-changed fields appear (FR-010): industry did not change.
        assert set(changed.keys()) == {"name", "team_size"}
        assert changed["name"] == {"from": "Acme Corp", "to": "Acme Corporation"}
        assert changed["team_size"] == {"from": "11-50", "to": "51-200"}

    @pytest.mark.anyio
    @pytest.mark.parametrize("bad_name", ["", "   ", "x" * 256])
    async def test_invalid_name_rejected_with_422(self, bad_name):
        from fastapi import HTTPException

        from tessera_api.routers.companies import UpdateCompanyRequest, update_current_company

        company_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id, company_id, CompanyRole.ADMIN)

        mock_repo = AsyncMock()
        body = UpdateCompanyRequest(name=bad_name, industry=None, team_size=None)

        with (
            patch(
                "tessera_api.routers.companies.SqlCompanyRepository",
                return_value=mock_repo,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await update_current_company(body, ctx, session)

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["error"]["code"] == "invalid_name"
        mock_repo.update_details.assert_not_awaited()

    @pytest.mark.anyio
    async def test_invalid_team_size_rejected_with_422(self):
        from fastapi import HTTPException

        from tessera_api.routers.companies import UpdateCompanyRequest, update_current_company

        company_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id, company_id, CompanyRole.ADMIN)

        mock_repo = AsyncMock()
        body = UpdateCompanyRequest(name="Acme Corp", industry=None, team_size="7-77")

        with (
            patch(
                "tessera_api.routers.companies.SqlCompanyRepository",
                return_value=mock_repo,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await update_current_company(body, ctx, session)

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["error"]["code"] == "invalid_team_size"
        mock_repo.update_details.assert_not_awaited()

    @pytest.mark.anyio
    async def test_null_optionals_clear_stored_values(self):
        from tessera_api.routers.companies import UpdateCompanyRequest, update_current_company

        company_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id, company_id, CompanyRole.ADMIN)

        old = _company(company_id)
        saved = _company(company_id, industry=None, team_size=None)

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = old
        mock_repo.update_details.return_value = saved

        body = UpdateCompanyRequest(name="Acme Corp", industry=None, team_size=None)

        with (
            patch(
                "tessera_api.routers.companies.SqlCompanyRepository",
                return_value=mock_repo,
            ),
            patch("tessera_api.routers.companies.write_audit", new_callable=AsyncMock),
        ):
            result = await update_current_company(body, ctx, session)

        assert result.industry is None
        assert result.team_size is None
        mock_repo.update_details.assert_awaited_once_with(
            company_id, name="Acme Corp", industry=None, team_size=None
        )

    @pytest.mark.anyio
    async def test_missing_company_returns_404(self):
        from fastapi import HTTPException

        from tessera_api.routers.companies import UpdateCompanyRequest, update_current_company

        company_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        session = AsyncMock()
        ctx = _ctx(actor_id, company_id, CompanyRole.ADMIN)

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None
        mock_repo.update_details.return_value = None

        body = UpdateCompanyRequest(name="Acme Corp", industry=None, team_size=None)

        with (
            patch(
                "tessera_api.routers.companies.SqlCompanyRepository",
                return_value=mock_repo,
            ),
            pytest.raises(HTTPException) as exc_info,
        ):
            await update_current_company(body, ctx, session)

        assert exc_info.value.status_code == 404


class TestPatchCurrentCompanyNonAdmin:
    """US3: a non-admin member's PATCH is refused before any write (FR-008)."""

    def test_member_patch_forbidden_and_repo_never_called(self, two_company_setup):
        token_a, _company_a_id, _token_b, _company_b_id = two_company_setup

        with (
            _bypass_onboarding_guard(),
            patch("tessera_api.routers.companies.SqlCompanyRepository") as mock_repo_cls,
        ):
            mock_repo = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            from fastapi.testclient import TestClient

            from tessera_api.main import app

            with TestClient(app) as client:
                response = client.patch(
                    "/v1/companies/current",
                    headers={"Authorization": f"Bearer {token_a}"},
                    json={"name": "Hacked", "industry": None, "team_size": None},
                )

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"
        mock_repo.update_details.assert_not_awaited()
