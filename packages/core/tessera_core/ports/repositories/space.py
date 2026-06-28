from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.role_permission import RolePermission
from tessera_core.domain.space import Space


class SpaceRepository(ABC):
    @abstractmethod
    async def create(self, space: Space) -> Space: ...

    @abstractmethod
    async def get_by_id(self, space_id: UUID) -> Space | None: ...

    @abstractmethod
    async def get_by_id_for_company(self, space_id: UUID, company_id: UUID) -> Space | None: ...

    @abstractmethod
    async def list_all(self) -> list[Space]: ...

    @abstractmethod
    async def list_by_company(self, company_id: UUID) -> list[Space]: ...

    @abstractmethod
    async def create_role_permission(self, permission: RolePermission) -> RolePermission: ...

    @abstractmethod
    async def list_role_permissions(self, space_id: UUID) -> list[RolePermission]: ...
