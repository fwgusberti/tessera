from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.role_permission import RolePermissionModel
from tessera_api.adapters.models.space import SpaceModel
from tessera_core.domain.confidentiality import Confidentiality
from tessera_core.domain.role_permission import RolePermission
from tessera_core.domain.space import Space
from tessera_core.domain.user_role import UserRole
from tessera_core.ports.repositories.space import SpaceRepository


def _space_from_model(m: SpaceModel) -> Space:
    return Space(
        id=m.id,
        slug=m.slug,
        name=m.name,
        sector=m.sector,
        company_id=m.company_id,
        taxonomy=m.taxonomy or {},
        retention_policy=m.retention_policy or {},
        confidence_threshold=m.confidence_threshold,
        default_language=m.default_language,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _perm_from_model(m: RolePermissionModel) -> RolePermission:
    return RolePermission(
        id=m.id,
        space_id=m.space_id,
        idp_group=m.idp_group,
        role=UserRole(m.role),
        max_confidentiality=Confidentiality(m.max_confidentiality),
        created_at=m.created_at,
    )


class SqlSpaceRepository(SpaceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, space: Space) -> Space:
        model = SpaceModel(
            id=space.id,
            slug=space.slug,
            name=space.name,
            sector=space.sector,
            company_id=space.company_id,
            taxonomy=space.taxonomy,
            retention_policy=space.retention_policy,
            confidence_threshold=space.confidence_threshold,
            default_language=space.default_language,
        )
        self._session.add(model)
        await self._session.flush()
        return _space_from_model(model)

    async def get_by_id(self, space_id: UUID) -> Space | None:
        result = await self._session.execute(select(SpaceModel).where(SpaceModel.id == space_id))
        model = result.scalar_one_or_none()
        return _space_from_model(model) if model else None

    async def get_by_id_for_company(self, space_id: UUID, company_id: UUID) -> Space | None:
        result = await self._session.execute(
            select(SpaceModel).where(
                SpaceModel.id == space_id,
                SpaceModel.company_id == company_id,
            )
        )
        model = result.scalar_one_or_none()
        return _space_from_model(model) if model else None

    async def list_all(self) -> list[Space]:
        result = await self._session.execute(select(SpaceModel))
        return [_space_from_model(m) for m in result.scalars().all()]

    async def list_by_company(self, company_id: UUID) -> list[Space]:
        result = await self._session.execute(
            select(SpaceModel).where(SpaceModel.company_id == company_id)
        )
        return [_space_from_model(m) for m in result.scalars().all()]

    async def create_role_permission(self, permission: RolePermission) -> RolePermission:
        model = RolePermissionModel(
            id=permission.id,
            space_id=permission.space_id,
            idp_group=permission.idp_group,
            role=permission.role.value,
            max_confidentiality=permission.max_confidentiality.value,
        )
        self._session.add(model)
        await self._session.flush()
        return _perm_from_model(model)

    async def list_role_permissions(self, space_id: UUID) -> list[RolePermission]:
        result = await self._session.execute(
            select(RolePermissionModel).where(RolePermissionModel.space_id == space_id)
        )
        return [_perm_from_model(m) for m in result.scalars().all()]
