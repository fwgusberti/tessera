from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.onboarding_progress import OnboardingProgressModel
from tessera_core.domain.onboarding_progress import OnboardingProgress
from tessera_core.ports.repositories.onboarding import OnboardingRepository


def _onboarding_from_model(m: OnboardingProgressModel) -> OnboardingProgress:
    return OnboardingProgress(
        id=m.id,
        user_id=m.user_id,
        completed_steps=list(m.completed_steps or []),
        current_step=m.current_step,
        company_join_method=m.company_join_method,
        company_id=m.company_id,
        completed_at=m.completed_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlOnboardingRepository(OnboardingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, progress: OnboardingProgress) -> OnboardingProgress:
        model = OnboardingProgressModel(
            id=progress.id,
            user_id=progress.user_id,
            completed_steps=list(progress.completed_steps),
            current_step=progress.current_step,
            company_join_method=progress.company_join_method,
            completed_at=progress.completed_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _onboarding_from_model(model)

    async def get_by_user_id(self, user_id: UUID) -> OnboardingProgress | None:
        result = await self._session.execute(
            select(OnboardingProgressModel).where(OnboardingProgressModel.user_id == user_id)
        )
        model = result.scalar_one_or_none()
        return _onboarding_from_model(model) if model else None

    async def advance_step(
        self,
        user_id: UUID,
        next_step: str,
        company_join_method: str | None = None,
        company_id: UUID | None = None,
    ) -> OnboardingProgress:
        result = await self._session.execute(
            select(OnboardingProgressModel).where(OnboardingProgressModel.user_id == user_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"OnboardingProgress for user {user_id} not found")

        current = model.current_step
        if current and current not in list(model.completed_steps or []):
            model.completed_steps = list(model.completed_steps or []) + [current]

        model.current_step = next_step
        model.updated_at = datetime.now(UTC)
        if company_join_method is not None:
            model.company_join_method = company_join_method
        if company_id is not None:
            model.company_id = company_id

        await self._session.flush()
        await self._session.refresh(model)
        return _onboarding_from_model(model)

    async def complete(self, user_id: UUID) -> OnboardingProgress:
        result = await self._session.execute(
            select(OnboardingProgressModel).where(OnboardingProgressModel.user_id == user_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"OnboardingProgress for user {user_id} not found")

        now = datetime.now(UTC)
        model.completed_at = now
        model.updated_at = now
        await self._session.flush()
        await self._session.refresh(model)
        return _onboarding_from_model(model)
