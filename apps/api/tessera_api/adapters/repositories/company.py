from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.company import CompanyModel
from tessera_api.adapters.models.company_membership import CompanyMembershipModel
from tessera_api.adapters.models.space_membership import SpaceMembershipModel
from tessera_api.adapters.models.user import UserModel
from tessera_core.domain.company import Company
from tessera_core.domain.company_member_listing import CompanyMemberListing
from tessera_core.domain.company_member_match import CompanyMemberMatch
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

    async def search_members_for_space(
        self, company_id: UUID, space_id: UUID, query: str, limit: int = 20
    ) -> list[CompanyMemberMatch]:
        pattern = f"%{query}%"
        excluded = select(SpaceMembershipModel.user_id).where(
            SpaceMembershipModel.space_id == space_id
        )
        stmt = (
            select(UserModel)
            .join(CompanyMembershipModel, CompanyMembershipModel.user_id == UserModel.id)
            .where(
                CompanyMembershipModel.company_id == company_id,
                or_(UserModel.email.ilike(pattern), UserModel.display_name.ilike(pattern)),
                UserModel.id.notin_(excluded),
            )
            .order_by(UserModel.display_name)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [
            CompanyMemberMatch(user_id=u.id, display_name=u.display_name, email=u.email)
            for u in result.scalars().all()
        ]

    async def search_addable_users(
        self, company_id: UUID, query: str, limit: int = 20
    ) -> list[CompanyMemberMatch]:
        pattern = f"%{query}%"
        # Users already in this company are excluded; the search spans the global
        # users table (identity), never another tenant's owned data.
        excluded = select(CompanyMembershipModel.user_id).where(
            CompanyMembershipModel.company_id == company_id
        )
        stmt = (
            select(UserModel)
            .where(
                or_(UserModel.email.ilike(pattern), UserModel.display_name.ilike(pattern)),
                UserModel.id.notin_(excluded),
            )
            .order_by(UserModel.display_name)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [
            CompanyMemberMatch(user_id=u.id, display_name=u.display_name, email=u.email)
            for u in result.scalars().all()
        ]

    async def list_members(self, company_id: UUID) -> list[CompanyMemberListing]:
        stmt = (
            select(
                UserModel.id,
                UserModel.display_name,
                UserModel.email,
                CompanyMembershipModel.role,
            )
            .join(CompanyMembershipModel, CompanyMembershipModel.user_id == UserModel.id)
            .where(CompanyMembershipModel.company_id == company_id)
            .order_by(UserModel.display_name)
        )
        result = await self._session.execute(stmt)
        return [
            CompanyMemberListing(
                user_id=row.id,
                display_name=row.display_name,
                email=row.email,
                role=CompanyRole(row.role),
            )
            for row in result.all()
        ]
