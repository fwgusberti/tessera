from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from tessera_core.domain.chunk import Chunk


class ChunkRepository(ABC):
    @abstractmethod
    async def upsert_chunks(self, chunks: list[Chunk]) -> None: ...

    @abstractmethod
    async def delete_by_document(self, document_id: UUID) -> None: ...

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        space_ids: list[UUID],
        max_confidentiality_level: int,
        top_k: int = 10,
    ) -> list[dict[str, Any]]: ...
