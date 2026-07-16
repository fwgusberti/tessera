from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.space_member_listing import SpaceMemberListing
from tessera_core.domain.space_membership import SpaceMembership
from tessera_core.domain.space_role import SpaceRole


class SpaceMembershipRepository(ABC):
    @abstractmethod
    async def add(self, membership: SpaceMembership) -> SpaceMembership: ...

    @abstractmethod
    async def get(self, space_id: UUID, user_id: UUID) -> SpaceMembership | None: ...

    @abstractmethod
    async def list_by_space(self, space_id: UUID) -> list[SpaceMembership]: ...

    @abstractmethod
    async def list_by_space_with_identity(
        self, space_id: UUID, company_id: UUID
    ) -> list[SpaceMemberListing]:
        """Members of the space joined with their identity, ordered by display_name.

        company_id is enforced inside the query (tenant scope) — a space outside
        the company yields an empty list.
        """
        ...

    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[SpaceMembership]: ...

    @abstractmethod
    async def update_role(
        self, space_id: UUID, user_id: UUID, role: SpaceRole
    ) -> SpaceMembership: ...

    @abstractmethod
    async def remove(self, space_id: UUID, user_id: UUID) -> None: ...

    @abstractmethod
    async def count_admins(self, space_id: UUID) -> int: ...
