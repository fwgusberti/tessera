from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.user import User


class UserRepository(ABC):
    @abstractmethod
    async def upsert(self, user: User) -> User: ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def get_by_subject(self, subject: str) -> User | None: ...

    @abstractmethod
    async def set_admin(self, user_id: UUID, is_admin: bool) -> User: ...
