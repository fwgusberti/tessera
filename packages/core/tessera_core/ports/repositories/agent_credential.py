from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.agent_credential import AgentCredential


class AgentCredentialRepository(ABC):
    @abstractmethod
    async def create(self, credential: AgentCredential) -> AgentCredential: ...

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> AgentCredential | None: ...

    @abstractmethod
    async def get_by_id_for_company(
        self, credential_id: UUID, company_id: UUID
    ) -> AgentCredential | None: ...

    @abstractmethod
    async def revoke(self, credential_id: UUID) -> AgentCredential: ...
