from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.onboarding_progress import OnboardingProgress


class OnboardingRepository(ABC):
    @abstractmethod
    async def create(self, progress: OnboardingProgress) -> OnboardingProgress: ...

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID) -> OnboardingProgress | None: ...

    @abstractmethod
    async def advance_step(
        self,
        user_id: UUID,
        next_step: str,
        company_join_method: str | None = None,
        company_id: UUID | None = None,
    ) -> OnboardingProgress: ...

    @abstractmethod
    async def complete(self, user_id: UUID) -> OnboardingProgress: ...
