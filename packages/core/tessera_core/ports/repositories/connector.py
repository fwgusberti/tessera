from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.connector import Connector


class ConnectorRepository(ABC):
    @abstractmethod
    async def create(self, connector: Connector) -> Connector: ...

    @abstractmethod
    async def get_by_id(self, connector_id: UUID) -> Connector | None: ...

    @abstractmethod
    async def get_by_id_for_company(
        self, connector_id: UUID, company_id: UUID
    ) -> Connector | None: ...

    @abstractmethod
    async def list_by_space(self, space_id: UUID) -> list[Connector]: ...

    @abstractmethod
    async def update_sync_status(self, connector_id: UUID, status: str) -> Connector: ...
