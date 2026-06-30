"""Shared pytest fixtures for the Tessera API test suite."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest

from tessera_api.adapters.database import get_db
from tessera_api.main import app


@contextmanager
def _override_db(mock_session: AsyncMock | None = None):
    """Context manager that overrides get_db with a mock session for the duration."""
    if mock_session is None:
        mock_session = AsyncMock()

    async def _fake_db():
        yield mock_session

    app.dependency_overrides[get_db] = _fake_db
    try:
        yield mock_session
    finally:
        app.dependency_overrides.pop(get_db, None)


def _patched_membership_resolution(get_membership_side_effect):
    """Patch oidc's membership resolution with a custom get_membership side effect."""
    mock_session = AsyncMock()
    mock_company_repo = AsyncMock()
    mock_company_repo.get_membership = AsyncMock(side_effect=get_membership_side_effect)
    mock_company_repo.get_by_id = AsyncMock(return_value=None)

    return (
        _override_db(mock_session),
        patch("tessera_api.auth.oidc.SqlCompanyRepository", return_value=mock_company_repo),
    )


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

    mock_session = AsyncMock()
    mock_company_repo = AsyncMock()
    mock_company_repo.get_membership = AsyncMock(
        side_effect=lambda uid, cid: _make_membership(uid, cid)
    )
    mock_company_repo.get_by_id = AsyncMock(return_value=None)

    with (
        _override_db(mock_session),
        patch("tessera_api.auth.oidc.SqlCompanyRepository", return_value=mock_company_repo),
    ):
        yield token_a, company_a_id, token_b, company_b_id


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

    db_ctx, repo_ctx = _patched_membership_resolution(_ms)
    with db_ctx, repo_ctx:
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

    db_ctx, repo_ctx = _patched_membership_resolution(_ms)
    with db_ctx, repo_ctx:
        yield token_a, company_a_id, company_b_id


@pytest.fixture()
def reproduction_setup():
    """The spec's literal three-company reproduction (feature 037, SC-002)."""
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from tessera_api.auth.jwt_auth import create_access_token
    from tessera_core.domain.entities import CompanyMembership, CompanyRole, Space

    felipe_id = uuid.uuid4()
    a2_id = uuid.uuid4()
    a3_id = uuid.uuid4()
    company1_id = uuid.uuid4()
    company2_id = uuid.uuid4()
    company3_id = uuid.uuid4()
    now = datetime.now(UTC)

    # felipe & a@2 are ordinary members; a@3 carries the legacy global is_admin flag.
    felipe_token = create_access_token(felipe_id, "felipe@gusba.dev", False, company_id=company1_id)
    a2_token = create_access_token(a2_id, "a@2.com", False, company_id=company2_id)
    a3_token = create_access_token(a3_id, "a@3.com", True, company_id=company3_id)

    def _space(company_id, name):
        return Space(
            id=uuid.uuid4(),
            slug=f"space-{uuid.uuid4().hex[:8]}",
            name=name,
            sector="tech",
            company_id=company_id,
        )

    space_a = _space(company1_id, "Space A")
    space_b = _space(company1_id, "Space B")
    space_c = _space(company2_id, "Space C")

    spaces_by_company = {
        company1_id: [space_a, space_b],
        company2_id: [space_c],
        company3_id: [],
    }

    # Each user is a member of exactly their own company; everywhere else → None.
    member_company = {felipe_id: company1_id, a2_id: company2_id, a3_id: company3_id}

    def _ms(uid, cid):
        if member_company.get(uid) == cid:
            return CompanyMembership(
                id=uuid.uuid4(), user_id=uid, company_id=cid,
                role=CompanyRole.MEMBER, joined_at=now,
            )
        return None

    db_ctx, repo_ctx = _patched_membership_resolution(_ms)
    with db_ctx, repo_ctx:
        yield SimpleNamespace(
            felipe_token=felipe_token,
            a2_token=a2_token,
            a3_token=a3_token,
            company1_id=company1_id,
            company2_id=company2_id,
            company3_id=company3_id,
            space_a=space_a,
            space_b=space_b,
            space_c=space_c,
            spaces_by_company=spaces_by_company,
        )


@pytest.fixture()
def admin_company_setup():
    """Like ``two_company_setup`` but the caller (Alice) is ADMIN of Company A.

    Returns:
        (token_a, company_a_id, token_b, company_b_id)
    """
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

    mock_session = AsyncMock()
    mock_company_repo = AsyncMock()
    mock_company_repo.get_membership = AsyncMock(
        side_effect=lambda uid, cid: _make_membership(uid, cid)
    )
    mock_company_repo.get_by_id = AsyncMock(return_value=None)

    with (
        _override_db(mock_session),
        patch("tessera_api.auth.oidc.SqlCompanyRepository", return_value=mock_company_repo),
    ):
        yield token_a, company_a_id, token_b, company_b_id
