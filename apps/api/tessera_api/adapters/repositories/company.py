from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.company import CompanyModel
from tessera_api.adapters.models.company_membership import CompanyMembershipModel
from tessera_core.domain.company import Company
from tessera_core.domain.company_membership import CompanyMembership
from tessera_core.domain.company_role import CompanyRole
from tessera_core.ports.repositories.company import CompanyRepository


def _company_from_model(m: CompanyModel) -> Company:
    return Company(
        id=m.id,
        name=m.name,
        industry=m.industry,
        team_size=m.team_size,
        admin_user_id=m.admin_user_id,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _company_membership_from_model(m: CompanyMembershipModel) -> CompanyMembership:
    return CompanyMembership(
        id=m.id,
        user_id=m.user_id,
        company_id=m.company_id,
        role=CompanyRole(m.role),
        joined_at=m.joined_at,
    )


class SqlCompanyRepository(CompanyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, company: Company) -> Company:
        model = CompanyModel(
            id=company.id,
            name=company.name,
            industry=company.industry,
            team_size=company.team_size,
            admin_user_id=company.admin_user_id,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _company_from_model(model)

    async def get_by_id(self, company_id: UUID) -> Company | None:
        result = await self._session.execute(
            select(CompanyModel).where(CompanyModel.id == company_id)
        )
        model = result.scalar_one_or_none()
        return _company_from_model(model) if model else None

    async def add_membership(self, membership: CompanyMembership) -> CompanyMembership:
        model = CompanyMembershipModel(
            id=membership.id,
            user_id=membership.user_id,
            company_id=membership.company_id,
            role=membership.role.value,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _company_membership_from_model(model)

    async def get_membership(self, user_id: UUID, company_id: UUID) -> CompanyMembership | None:
        result = await self._session.execute(
            select(CompanyMembershipModel).where(
                CompanyMembershipModel.user_id == user_id,
                CompanyMembershipModel.company_id == company_id,
            )
        )
        model = result.scalar_one_or_none()
        return _company_membership_from_model(model) if model else None

    async def list_memberships_for_user(self, user_id: UUID) -> list[CompanyMembership]:
        result = await self._session.execute(
            select(CompanyMembershipModel).where(CompanyMembershipModel.user_id == user_id)
        )
        return [_company_membership_from_model(m) for m in result.scalars().all()]
