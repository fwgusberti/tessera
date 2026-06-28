from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.source_artifact import SourceArtifact


class SourceArtifactRepository(ABC):
    @abstractmethod
    async def upsert(self, artifact: SourceArtifact) -> SourceArtifact: ...

    @abstractmethod
    async def get_by_external_id(
        self, connector_id: UUID, external_id: str
    ) -> SourceArtifact | None: ...

    @abstractmethod
    async def list_by_connector(self, connector_id: UUID) -> list[SourceArtifact]: ...
