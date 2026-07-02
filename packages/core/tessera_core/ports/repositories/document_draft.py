from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.document_draft import DocumentDraft


class DocumentDraftRepository(ABC):
    @abstractmethod
    async def get_by_document_id_for_company(
        self, document_id: UUID, company_id: UUID
    ) -> DocumentDraft | None: ...

    @abstractmethod
    async def upsert_for_company(
        self,
        document_id: UUID,
        company_id: UUID,
        editor_user_id: UUID,
        content_markdown: str,
    ) -> DocumentDraft: ...

    @abstractmethod
    async def delete_for_company(self, document_id: UUID, company_id: UUID) -> None: ...
