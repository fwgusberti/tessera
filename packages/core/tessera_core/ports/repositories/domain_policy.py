from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.domain_join_policy import DomainJoinPolicy


class DomainPolicyRepository(ABC):
    @abstractmethod
    async def create(self, policy: DomainJoinPolicy) -> DomainJoinPolicy: ...

    @abstractmethod
    async def get_by_domain(self, domain: str) -> DomainJoinPolicy | None: ...

    @abstractmethod
    async def get_by_id(self, policy_id: UUID) -> DomainJoinPolicy | None: ...

    @abstractmethod
    async def list_by_company(self, company_id: UUID) -> list[DomainJoinPolicy]: ...

    @abstractmethod
    async def mark_verified(self, policy_id: UUID) -> DomainJoinPolicy: ...
