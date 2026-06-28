from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.password_reset_token import PasswordResetToken


class PasswordResetTokenRepository(ABC):
    @abstractmethod
    async def create(self, token: PasswordResetToken) -> PasswordResetToken: ...

    @abstractmethod
    async def get_by_hash(self, token_hash: str) -> PasswordResetToken | None: ...

    @abstractmethod
    async def consume_all_for_user(self, user_id: UUID) -> None: ...
