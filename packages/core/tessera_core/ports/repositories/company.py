from abc import ABC, abstractmethod
from uuid import UUID

from tessera_core.domain.company import Company
from tessera_core.domain.company_member_listing import CompanyMemberListing
from tessera_core.domain.company_member_match import CompanyMemberMatch
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

    @abstractmethod
    async def search_members_for_space(
        self, company_id: UUID, space_id: UUID, query: str, limit: int = 20
    ) -> list[CompanyMemberMatch]:
        """Search company members by name/email, excluding existing members of space_id."""
        ...

    @abstractmethod
    async def search_addable_users(
        self, company_id: UUID, query: str, limit: int = 20
    ) -> list[CompanyMemberMatch]:
        """Search the global user directory for people not already in ``company_id``.

        Matches ``display_name``/``email`` case-insensitively, excludes current
        members of ``company_id``, and returns identity fields only.
        """
        ...

    @abstractmethod
    async def list_members(self, company_id: UUID) -> list[CompanyMemberListing]:
        """List every member of the company with their company role, ordered by display name."""
        ...
