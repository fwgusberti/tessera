from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.space import SpaceModel
from tessera_api.adapters.models.space_membership import SpaceMembershipModel
from tessera_api.adapters.models.user import UserModel
from tessera_core.domain.space_member_listing import SpaceMemberListing
from tessera_core.domain.space_membership import SpaceMembership
from tessera_core.domain.space_role import SpaceRole
from tessera_core.ports.repositories.space_membership import SpaceMembershipRepository


def _membership_from_model(m: SpaceMembershipModel) -> SpaceMembership:
    return SpaceMembership(
        id=m.id,
        space_id=m.space_id,
        user_id=m.user_id,
        role=SpaceRole(m.role),
        invited_by_user_id=m.invited_by_user_id,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlSpaceMembershipRepository(SpaceMembershipRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, membership: SpaceMembership) -> SpaceMembership:
        model = SpaceMembershipModel(
            id=membership.id,
            space_id=membership.space_id,
            user_id=membership.user_id,
            role=membership.role.value,
            invited_by_user_id=membership.invited_by_user_id,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _membership_from_model(model)

    async def get(self, space_id: UUID, user_id: UUID) -> SpaceMembership | None:
        result = await self._session.execute(
            select(SpaceMembershipModel).where(
                SpaceMembershipModel.space_id == space_id,
                SpaceMembershipModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        return _membership_from_model(model) if model else None

    async def list_by_space(self, space_id: UUID) -> list[SpaceMembership]:
        result = await self._session.execute(
            select(SpaceMembershipModel).where(SpaceMembershipModel.space_id == space_id)
        )
        return [_membership_from_model(m) for m in result.scalars().all()]

    async def list_by_space_with_identity(
        self, space_id: UUID, company_id: UUID
    ) -> list[SpaceMemberListing]:
        # Tenant scope enforced inside the query: the JOIN on spaces requires
        # spaces.company_id == company_id (Constitution VI, defense in depth).
        stmt = (
            select(
                SpaceMembershipModel.id,
                SpaceMembershipModel.space_id,
                SpaceMembershipModel.user_id,
                UserModel.display_name,
                UserModel.email,
                SpaceMembershipModel.role,
                SpaceMembershipModel.invited_by_user_id,
                SpaceMembershipModel.created_at,
                SpaceMembershipModel.updated_at,
            )
            .join(UserModel, UserModel.id == SpaceMembershipModel.user_id)
            .join(
                SpaceModel,
                (SpaceModel.id == SpaceMembershipModel.space_id)
                & (SpaceModel.company_id == company_id),
            )
            .where(SpaceMembershipModel.space_id == space_id)
            .order_by(UserModel.display_name)
        )
        result = await self._session.execute(stmt)
        return [
            SpaceMemberListing(
                id=row.id,
                space_id=row.space_id,
                user_id=row.user_id,
                display_name=row.display_name,
                email=row.email,
                role=SpaceRole(row.role),
                invited_by_user_id=row.invited_by_user_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.all()
        ]

    async def list_by_user(self, user_id: UUID) -> list[SpaceMembership]:
        result = await self._session.execute(
            select(SpaceMembershipModel).where(SpaceMembershipModel.user_id == user_id)
        )
        return [_membership_from_model(m) for m in result.scalars().all()]

    async def update_role(self, space_id: UUID, user_id: UUID, role: SpaceRole) -> SpaceMembership:
        result = await self._session.execute(
            select(SpaceMembershipModel).where(
                SpaceMembershipModel.space_id == space_id,
                SpaceMembershipModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError("not a member")
        model.role = role.value
        await self._session.flush()
        await self._session.refresh(model)
        return _membership_from_model(model)

    async def remove(self, space_id: UUID, user_id: UUID) -> None:
        result = await self._session.execute(
            select(SpaceMembershipModel).where(
                SpaceMembershipModel.space_id == space_id,
                SpaceMembershipModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError("not a member")
        await self._session.delete(model)
        await self._session.flush()

    async def count_admins(self, space_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).where(
                SpaceMembershipModel.space_id == space_id,
                SpaceMembershipModel.role == SpaceRole.ADMIN.value,
            )
        )
        return result.scalar_one()
