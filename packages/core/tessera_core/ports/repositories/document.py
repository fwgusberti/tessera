from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.document import Document
from tessera_core.domain.document_lifecycle_state import DocumentLifecycleState


class DocumentRepository(ABC):
    @abstractmethod
    async def create(self, document: Document) -> Document: ...

    @abstractmethod
    async def get_by_id(self, document_id: UUID) -> Document | None: ...

    @abstractmethod
    async def get_by_id_for_company(
        self, document_id: UUID, company_id: UUID
    ) -> Document | None: ...

    @abstractmethod
    async def list_by_space(
        self, space_id: UUID, state: DocumentLifecycleState | None = None
    ) -> list[Document]: ...

    @abstractmethod
    async def list_by_space_ids(
        self,
        space_ids: list[UUID],
        state: DocumentLifecycleState | None = None,
    ) -> list[Document]: ...

    @abstractmethod
    async def list_by_space_ids_for_company(
        self,
        space_ids: list[UUID],
        company_id: UUID,
        state: DocumentLifecycleState | None = None,
    ) -> list[Document]: ...

    @abstractmethod
    async def update_state(self, document_id: UUID, state: DocumentLifecycleState) -> Document: ...

    @abstractmethod
    async def set_current_version(self, document_id: UUID, version_id: UUID) -> Document: ...

    @abstractmethod
    async def set_owner(self, document_id: UUID, user_id: UUID) -> Document: ...
