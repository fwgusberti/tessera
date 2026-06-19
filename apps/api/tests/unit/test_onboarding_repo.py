"""Unit tests for SqlOnboardingRepository.

These tests mock the AsyncSession and verify the mapping between ORM models
and domain entities. They follow TDD — written before the implementation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tessera_core.domain.entities import OnboardingProgress


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def make_progress(user_id):
    def _make(**kwargs) -> OnboardingProgress:
        defaults = dict(
            user_id=user_id,
            completed_steps=[],
            current_step="profile",
            company_join_method=None,
            completed_at=None,
        )
        defaults.update(kwargs)
        return OnboardingProgress(**defaults)

    return _make


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


class TestSqlOnboardingRepositoryCreate:
    @pytest.mark.anyio
    async def test_create_persists_and_returns_progress(self, mock_session, make_progress):
        from tessera_api.adapters.repo import SqlOnboardingRepository

        progress = make_progress()
        repo = SqlOnboardingRepository(mock_session)

        result = await repo.create(progress)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert result.user_id == progress.user_id
        assert result.current_step == "profile"
        assert result.completed_at is None

    @pytest.mark.anyio
    async def test_create_sets_completed_steps_empty_by_default(self, mock_session, make_progress):
        from tessera_api.adapters.repo import SqlOnboardingRepository

        progress = make_progress()
        repo = SqlOnboardingRepository(mock_session)
        result = await repo.create(progress)

        assert result.completed_steps == []


class TestSqlOnboardingRepositoryGetByUserId:
    @pytest.mark.anyio
    async def test_returns_none_when_not_found(self, mock_session, user_id):
        from tessera_api.adapters.repo import SqlOnboardingRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = SqlOnboardingRepository(mock_session)
        result = await repo.get_by_user_id(user_id)

        assert result is None

    @pytest.mark.anyio
    async def test_returns_progress_when_found(self, mock_session, user_id):
        from tessera_api.adapters.repo import SqlOnboardingRepository
        from tessera_api.adapters.models import OnboardingProgressModel

        model = OnboardingProgressModel(
            id=uuid.uuid4(),
            user_id=user_id,
            completed_steps=[],
            current_step="profile",
            company_join_method=None,
            completed_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = model
        mock_session.execute.return_value = mock_result

        repo = SqlOnboardingRepository(mock_session)
        result = await repo.get_by_user_id(user_id)

        assert result is not None
        assert result.user_id == user_id
        assert result.current_step == "profile"


class TestSqlOnboardingRepositoryAdvanceStep:
    @pytest.mark.anyio
    async def test_advance_step_marks_current_step_completed(self, mock_session, user_id):
        """advance_step(user_id, 'company') marks 'profile' (current) as complete."""
        from tessera_api.adapters.repo import SqlOnboardingRepository
        from tessera_api.adapters.models import OnboardingProgressModel

        model = OnboardingProgressModel(
            id=uuid.uuid4(),
            user_id=user_id,
            completed_steps=[],
            current_step="profile",  # starting at profile
            company_join_method=None,
            completed_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = model
        mock_session.execute.return_value = mock_result

        repo = SqlOnboardingRepository(mock_session)
        result = await repo.advance_step(user_id, "company")

        # "profile" (was current) should now be in completed_steps
        assert "profile" in result.completed_steps
        assert result.current_step == "company"

    @pytest.mark.anyio
    async def test_advance_step_stores_company_join_method(self, mock_session, user_id):
        from tessera_api.adapters.repo import SqlOnboardingRepository
        from tessera_api.adapters.models import OnboardingProgressModel

        model = OnboardingProgressModel(
            id=uuid.uuid4(),
            user_id=user_id,
            completed_steps=["profile"],
            current_step="company",  # currently at company
            company_join_method=None,
            completed_at=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = model
        mock_session.execute.return_value = mock_result

        repo = SqlOnboardingRepository(mock_session)
        result = await repo.advance_step(user_id, "invite", company_join_method="created")

        assert result.company_join_method == "created"
        assert result.current_step == "invite"


class TestSqlOnboardingRepositoryComplete:
    @pytest.mark.anyio
    async def test_complete_sets_completed_at(self, mock_session, user_id):
        from tessera_api.adapters.repo import SqlOnboardingRepository
        from tessera_api.adapters.models import OnboardingProgressModel

        now = datetime.now(UTC)
        model = OnboardingProgressModel(
            id=uuid.uuid4(),
            user_id=user_id,
            completed_steps=["profile", "company", "invite"],
            current_step="complete",
            company_join_method="created",
            completed_at=now,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = model
        mock_session.execute.return_value = mock_result

        repo = SqlOnboardingRepository(mock_session)
        result = await repo.complete(user_id)

        assert result.completed_at is not None

    @pytest.mark.anyio
    async def test_complete_raises_when_not_found(self, mock_session, user_id):
        from tessera_api.adapters.repo import SqlOnboardingRepository

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = SqlOnboardingRepository(mock_session)
        with pytest.raises(ValueError, match="not found"):
            await repo.complete(user_id)
