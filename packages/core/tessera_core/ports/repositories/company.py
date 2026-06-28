from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.company import Company
from tessera_core.domain.company_membership import CompanyMembership


class CompanyRepository(ABC):
    @abstractmethod
    async def create(self, company: Company) -> Company: ...

    @abstractmethod
    async def get_by_id(self, company_id: UUID) -> Company | None: ...

    @abstractmethod
    async def add_membership(self, membership: CompanyMembership) -> CompanyMembership: ...

    @abstractmethod
    async def get_membership(self, user_id: UUID, company_id: UUID) -> CompanyMembership | None: ...

    @abstractmethod
    async def list_memberships_for_user(self, user_id: UUID) -> list[CompanyMembership]: ...
