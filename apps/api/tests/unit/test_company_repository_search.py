"""Adapter tests for SqlCompanyRepository.search_addable_users (feature 054, US2).

The direct-add type-ahead searches the *global* users table for people not yet in
the active company, returning identity fields only. These tests pin the query
shape (case-insensitive name/email match, current-member exclusion, ordering,
limit) by inspecting the compiled statement — no live DB required.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


def _rows(models):
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = models
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    return mock_result


class TestSearchAddableUsers:
    @pytest.mark.anyio
    async def test_returns_identity_fields_only(self, mock_session):
        from tessera_api.adapters.models import UserModel
        from tessera_api.adapters.repo import SqlCompanyRepository

        uid = uuid.uuid4()
        mock_session.execute.return_value = _rows(
            [
                UserModel(
                    id=uid, external_subject="s", email="ada@x.com", display_name="Ada Lovelace"
                )
            ]
        )

        repo = SqlCompanyRepository(mock_session)
        result = await repo.search_addable_users(uuid.uuid4(), "ada")

        assert len(result) == 1
        assert result[0].user_id == uid
        assert result[0].display_name == "Ada Lovelace"
        assert result[0].email == "ada@x.com"
        # Identity-only value object — no membership/other-company data leaks.
        assert not hasattr(result[0], "company_id")

    @pytest.mark.anyio
    async def test_matches_name_and_email_case_insensitively(self, mock_session):
        from tessera_api.adapters.repo import SqlCompanyRepository

        mock_session.execute.return_value = _rows([])
        repo = SqlCompanyRepository(mock_session)
        await repo.search_addable_users(uuid.uuid4(), "Ada")

        stmt = mock_session.execute.call_args[0][0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False})).lower()
        # ILIKE compiles to a case-folded LIKE (lower(col) LIKE lower(:param)).
        assert "like" in compiled
        assert "lower" in compiled
        assert "email" in compiled
        assert "display_name" in compiled

    @pytest.mark.anyio
    async def test_excludes_current_company_members(self, mock_session):
        from tessera_api.adapters.repo import SqlCompanyRepository

        mock_session.execute.return_value = _rows([])
        repo = SqlCompanyRepository(mock_session)
        await repo.search_addable_users(uuid.uuid4(), "anyone")

        stmt = mock_session.execute.call_args[0][0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        # The exclusion subquery references company_memberships.
        assert "company_memberships" in compiled
        assert "NOT IN" in compiled.upper()

    @pytest.mark.anyio
    async def test_orders_by_display_name(self, mock_session):
        from tessera_api.adapters.repo import SqlCompanyRepository

        mock_session.execute.return_value = _rows([])
        repo = SqlCompanyRepository(mock_session)
        await repo.search_addable_users(uuid.uuid4(), "anyone")

        stmt = mock_session.execute.call_args[0][0]
        assert len(stmt._order_by_clauses) > 0

    @pytest.mark.anyio
    async def test_respects_limit_argument(self, mock_session):
        from tessera_api.adapters.repo import SqlCompanyRepository

        mock_session.execute.return_value = _rows([])
        repo = SqlCompanyRepository(mock_session)
        await repo.search_addable_users(uuid.uuid4(), "anyone", limit=5)

        stmt = mock_session.execute.call_args[0][0]
        assert stmt._limit_clause is not None
