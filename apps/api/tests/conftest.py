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


def _patched_membership_resolution(get_membership_side_effect):
    """Patch oidc's membership resolution with a custom get_membership side effect."""
    from unittest.mock import patch

    mock_db = MagicMock()
    mock_session = AsyncMock()
    mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

    mock_company_repo = AsyncMock()
    mock_company_repo.get_membership = AsyncMock(side_effect=get_membership_side_effect)

    return (
        patch("tessera_api.auth.oidc.get_db", mock_db),
        patch("tessera_api.auth.oidc.SqlCompanyRepository", return_value=mock_company_repo),
    )


@pytest.fixture()
def admin_in_a_member_in_b():
    """A single user who is ADMIN of Company A and ordinary MEMBER of Company B (US3).

    Returns ``(token_a, company_a_id, token_b, company_b_id)`` — two company-scoped
    tokens for the *same* user. Admin authority must apply only while A is active.
    """
    from datetime import UTC, datetime

    from tessera_api.auth.jwt_auth import create_access_token
    from tessera_core.domain.entities import CompanyMembership, CompanyRole

    user_id = uuid.uuid4()
    company_a_id = uuid.uuid4()
    company_b_id = uuid.uuid4()

    token_a = create_access_token(user_id, "multi@x.test", False, company_id=company_a_id)
    token_b = create_access_token(user_id, "multi@x.test", False, company_id=company_b_id)

    def _ms(uid, cid):
        role = CompanyRole.ADMIN if cid == company_a_id else CompanyRole.MEMBER
        return CompanyMembership(
            id=uuid.uuid4(), user_id=uid, company_id=cid, role=role,
            joined_at=datetime.now(UTC),
        )

    p_db, p_repo = _patched_membership_resolution(_ms)
    with p_db, p_repo:
        yield token_a, company_a_id, token_b, company_b_id


@pytest.fixture()
def legacy_global_admin_setup():
    """Company A admin who ALSO carries the legacy global ``is_admin=True`` flag and
    holds NO membership in Company B (US4).

    The JWT asserts ``is_admin=True``; ``get_membership`` returns ADMIN for Company A
    and ``None`` for Company B. The global flag must confer zero authority over B.
    Returns ``(token_a, company_a_id, company_b_id)``.
    """
    from datetime import UTC, datetime

    from tessera_api.auth.jwt_auth import create_access_token
    from tessera_core.domain.entities import CompanyMembership, CompanyRole

    user_id = uuid.uuid4()
    company_a_id = uuid.uuid4()
    company_b_id = uuid.uuid4()

    # is_admin=True embedded in the token — the legacy global flag.
    token_a = create_access_token(user_id, "legacy@x.test", True, company_id=company_a_id)

    def _ms(uid, cid):
        if cid == company_a_id:
            return CompanyMembership(
                id=uuid.uuid4(), user_id=uid, company_id=cid,
                role=CompanyRole.ADMIN, joined_at=datetime.now(UTC),
            )
        return None  # no membership in Company B

    p_db, p_repo = _patched_membership_resolution(_ms)
    with p_db, p_repo:
        yield token_a, company_a_id, company_b_id


@pytest.fixture()
def admin_company_setup():
    """Like ``two_company_setup`` but the caller (Alice) is ADMIN of Company A.

    The mocked ``get_membership`` returns ``CompanyRole.ADMIN`` for the caller in
    Company A and ``CompanyRole.MEMBER`` in every other company, so handlers gated
    by ``require_company_admin`` / deriving ``is_company_admin`` see admin authority
    only while Company A is active. Reused by US1/US2/US4 admin-authority tests.

    Returns:
        (token_a, company_a_id, token_b, company_b_id)
    """
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
        role = CompanyRole.ADMIN if company_id == company_a_id else CompanyRole.MEMBER
        return CompanyMembership(
            id=uuid.uuid4(), user_id=user_id, company_id=company_id,
            role=role, joined_at=now,
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
