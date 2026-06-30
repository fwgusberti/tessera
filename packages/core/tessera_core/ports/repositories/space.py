from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.role_permission import RolePermission
from tessera_core.domain.space import Space
from tessera_core.domain.space_access import SpaceAccess


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

    @abstractmethod
    async def get_ancestor_chain(self, space_id: UUID) -> list[Space]:
        """Ordered list from immediate parent to root (empty if root space)."""
        ...

    @abstractmethod
    async def set_parent(self, space_id: UUID, parent_space_id: UUID) -> Space:
        """Set parent_space_id on space_id; returns updated Space."""
        ...

    @abstractmethod
    async def remove_parent(self, space_id: UUID) -> Space:
        """Set parent_space_id = NULL; returns updated Space."""
        ...

    @abstractmethod
    async def list_accessible_by_user(
        self, user_id: UUID, company_id: UUID
    ) -> list[SpaceAccess]:
        """Returns all spaces the user can access (direct + inherited), scoped to company_id."""
        ...
