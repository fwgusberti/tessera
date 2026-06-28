from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.update_proposal import UpdateProposal


class ProposalRepository(ABC):
    @abstractmethod
    async def create(self, proposal: UpdateProposal) -> UpdateProposal: ...

    @abstractmethod
    async def get_by_id(self, proposal_id: UUID) -> UpdateProposal | None: ...

    @abstractmethod
    async def get_by_id_for_company(
        self, proposal_id: UUID, company_id: UUID
    ) -> UpdateProposal | None: ...

    @abstractmethod
    async def list_for_company(
        self,
        company_id: UUID,
        state: str | None = None,
        space_id: UUID | None = None,
    ) -> list[UpdateProposal]: ...

    @abstractmethod
    async def list_pending_for_document(self, document_id: UUID) -> list[UpdateProposal]: ...

    @abstractmethod
    async def update_state(self, proposal: UpdateProposal) -> UpdateProposal: ...

    @abstractmethod
    async def invalidate_pending_for_document(self, document_id: UUID) -> int: ...
