"""Shared pytest fixtures for the Tessera API test suite."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture()
def two_company_setup():
    """Set up two isolated company contexts for cross-tenant isolation testing.

    Creates Alice / Company Alpha and Bob / Company Beta with scoped JWTs.
    Also patches the membership check in require_company_context so tests don't
    need a real DB for the auth layer. Individual tests can override the
    SqlCompanyRepository patch when testing revocation scenarios.

    Returns:
        (token_a, company_a_id, token_b, company_b_id)
    """
    import contextlib
    from unittest.mock import patch

    from tessera_api.auth.jwt_auth import create_access_token
    from tessera_core.domain.entities import CompanyMembership, CompanyRole

    alice_id = uuid.uuid4()
    bob_id = uuid.uuid4()
    company_a_id = uuid.uuid4()
    company_b_id = uuid.uuid4()
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    token_a = create_access_token(alice_id, "alice@alpha.test", False, company_id=company_a_id)
    token_b = create_access_token(bob_id, "bob@beta.test", False, company_id=company_b_id)

    def _make_membership(user_id, company_id):
        return CompanyMembership(
            id=uuid.uuid4(), user_id=user_id, company_id=company_id,
            role=CompanyRole.MEMBER, joined_at=now,
        )

    mock_db = MagicMock()
    mock_session = AsyncMock()
    mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

    mock_company_repo = AsyncMock()
    mock_company_repo.get_membership = AsyncMock(
        side_effect=lambda uid, cid: _make_membership(uid, cid)
    )

    with (
        patch("tessera_api.auth.oidc.get_db", mock_db),
        patch("tessera_api.auth.oidc.SqlCompanyRepository", return_value=mock_company_repo),
    ):
        yield token_a, company_a_id, token_b, company_b_id
