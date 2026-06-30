"""Tests for auth dependencies — require_company_context / _resolve_company_membership."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_token(company_id: uuid.UUID | None = None) -> str:
    from tessera_api.auth.jwt_auth import create_access_token

    return create_access_token(uuid.uuid4(), "alice@example.com", False, company_id=company_id)


def _make_token_for(user_id: uuid.UUID, company_id: uuid.UUID | None = None) -> str:
    from tessera_api.auth.jwt_auth import create_access_token

    return create_access_token(user_id, "alice@example.com", False, company_id=company_id)


def _make_request(token: str) -> MagicMock:
    """Build a minimal mock Request with the given Bearer token."""
    req = MagicMock()
    req.headers = {"Authorization": f"Bearer {token}"}
    req.session = {}
    return req


class TestRequireCompanyContext:
    @pytest.mark.anyio
    async def test_rejects_token_without_company_id_with_403(self):
        """JWT with no company_id claim must raise 403 no_company_context."""
        from fastapi import HTTPException

        from tessera_api.auth.oidc import _resolve_company_membership

        token = _make_token(company_id=None)
        request = _make_request(token)
        mock_session = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await _resolve_company_membership(request, mock_session)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error"]["code"] == "no_company_context"

    @pytest.mark.anyio
    async def test_accepts_token_with_company_id(self):
        """JWT with company_id claim must pass _resolve_company_membership."""
        from unittest.mock import patch

        from tessera_api.auth.oidc import _resolve_company_membership
        from tessera_core.domain.entities import CompanyMembership, CompanyRole

        company_id = uuid.uuid4()
        user_id = uuid.uuid4()
        token = _make_token_for(user_id, company_id)
        request = _make_request(token)
        mock_session = AsyncMock()

        membership = CompanyMembership(
            id=uuid.uuid4(), user_id=user_id, company_id=company_id,
            role=CompanyRole.MEMBER, joined_at=datetime.now(timezone.utc),
        )
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)
        mock_repo.get_membership = AsyncMock(return_value=membership)

        with patch("tessera_api.auth.oidc.SqlCompanyRepository", return_value=mock_repo):
            user_info, ctx_company_id, ctx_membership = await _resolve_company_membership(
                request, mock_session
            )

        assert ctx_company_id == company_id
        assert ctx_membership == membership
