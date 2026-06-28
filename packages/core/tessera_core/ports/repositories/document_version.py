from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from tessera_core.domain.document_version import DocumentVersion


class DocumentVersionRepository(ABC):
    @abstractmethod
    async def create(self, version: DocumentVersion) -> DocumentVersion: ...

    @abstractmethod
    async def get_by_id(self, version_id: UUID) -> DocumentVersion | None: ...

    @abstractmethod
    async def list_by_document(self, document_id: UUID) -> list[DocumentVersion]: ...

    @abstractmethod
    async def next_version_number(self, document_id: UUID) -> int: ...

    @abstractmethod
    async def update_approval(
        self, version_id: UUID, approver_id: UUID, approved_at: datetime
    ) -> DocumentVersion: ...
