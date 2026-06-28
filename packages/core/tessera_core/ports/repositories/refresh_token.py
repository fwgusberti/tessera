from abc import ABC, abstractmethod
from uuid import UUID


class RefreshTokenRepository(ABC):
    @abstractmethod
    async def revoke_all_except(self, user_id: UUID, except_hash: str) -> None: ...

    @abstractmethod
    async def revoke_all_for_user(self, user_id: UUID) -> None: ...
