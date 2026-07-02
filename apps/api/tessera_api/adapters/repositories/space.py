from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.role_permission import RolePermissionModel
from tessera_api.adapters.models.space import SpaceModel
from tessera_core.domain.confidentiality import Confidentiality
from tessera_core.domain.role_permission import RolePermission
from tessera_core.domain.space import Space
from tessera_core.domain.space_access import SpaceAccess
from tessera_core.domain.space_role import SpaceRole
from tessera_core.domain.user_role import UserRole
from tessera_core.ports.repositories.space import SpaceRepository

_RANK_ROLE = {3: SpaceRole.ADMIN, 2: SpaceRole.EDITOR, 1: SpaceRole.VIEWER}


def _space_from_model(m: SpaceModel) -> Space:
    return Space(
        id=m.id,
        slug=m.slug,
        name=m.name,
        sector=m.sector,
        company_id=m.company_id,
        parent_space_id=m.parent_space_id,
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
            parent_space_id=space.parent_space_id,
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

    async def get_ancestor_chain(self, space_id: UUID) -> list[Space]:
        """Walk upward from space_id's parent to root via recursive CTE.

        Returns ordered list [immediate_parent, ..., root]. Empty if root space.
        """
        sql = text("""
            WITH RECURSIVE ancestors AS (
                SELECT s.*, 1 AS depth
                FROM spaces s
                WHERE s.id = (
                    SELECT parent_space_id FROM spaces WHERE id = :space_id
                )
                UNION ALL
                SELECT s.*, a.depth + 1
                FROM spaces s
                JOIN ancestors a ON s.id = a.parent_space_id
            )
            SELECT
                id, slug, name, sector, company_id, parent_space_id,
                taxonomy, retention_policy, confidence_threshold,
                default_language, created_at, updated_at
            FROM ancestors
            ORDER BY depth
        """)
        result = await self._session.execute(sql, {"space_id": space_id})
        rows = result.mappings().all()
        return [
            Space(
                id=r["id"],
                slug=r["slug"],
                name=r["name"],
                sector=r["sector"],
                company_id=r["company_id"],
                parent_space_id=r["parent_space_id"],
                taxonomy=r["taxonomy"] or {},
                retention_policy=r["retention_policy"] or {},
                confidence_threshold=r["confidence_threshold"],
                default_language=r["default_language"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    async def set_parent(self, space_id: UUID, parent_space_id: UUID) -> Space:
        """Set parent_space_id on space_id; returns updated Space."""
        await self._session.execute(
            update(SpaceModel)
            .where(SpaceModel.id == space_id)
            .values(parent_space_id=parent_space_id)
        )
        await self._session.flush()
        result = await self._session.execute(select(SpaceModel).where(SpaceModel.id == space_id))
        model = result.scalar_one()
        return _space_from_model(model)

    async def remove_parent(self, space_id: UUID) -> Space:
        """Set parent_space_id = NULL; returns updated Space."""
        await self._session.execute(
            update(SpaceModel).where(SpaceModel.id == space_id).values(parent_space_id=None)
        )
        await self._session.flush()
        result = await self._session.execute(select(SpaceModel).where(SpaceModel.id == space_id))
        model = result.scalar_one()
        return _space_from_model(model)

    async def rename(self, space_id: UUID, name: str) -> Space:
        """Set name on space_id; returns updated Space."""
        await self._session.execute(
            update(SpaceModel).where(SpaceModel.id == space_id).values(name=name)
        )
        await self._session.flush()
        result = await self._session.execute(select(SpaceModel).where(SpaceModel.id == space_id))
        model = result.scalar_one()
        return _space_from_model(model)

    async def list_accessible_by_user(self, user_id: UUID, company_id: UUID) -> list[SpaceAccess]:
        """Recursive CTE: direct memberships + all descendant spaces.

        Role propagates downward. Both CTE legs scoped to company_id (Principle VI).
        """
        sql = text("""
            WITH RECURSIVE accessible AS (
                SELECT
                    s.id,
                    CASE sm.role
                        WHEN 'admin'  THEN 3
                        WHEN 'editor' THEN 2
                        ELSE 1
                    END AS role_rank,
                    TRUE AS is_direct
                FROM spaces s
                JOIN space_memberships sm
                  ON sm.space_id = s.id AND sm.user_id = :user_id
                WHERE s.company_id = :company_id

                UNION ALL

                SELECT
                    s.id,
                    a.role_rank,
                    FALSE AS is_direct
                FROM spaces s
                JOIN accessible a ON s.parent_space_id = a.id
                WHERE s.company_id = :company_id
            )
            SELECT
                id,
                MAX(role_rank)     AS role_rank,
                bool_or(is_direct) AS is_direct
            FROM accessible
            GROUP BY id
        """)
        rows = (
            await self._session.execute(sql, {"user_id": user_id, "company_id": company_id})
        ).all()

        if not rows:
            return []

        space_ids = [r[0] for r in rows]
        spaces_result = await self._session.execute(
            select(SpaceModel).where(SpaceModel.id.in_(space_ids))
        )
        spaces_map = {m.id: m for m in spaces_result.scalars().all()}

        accesses: list[SpaceAccess] = []
        for row in rows:
            sid, role_rank, is_direct = row
            if sid not in spaces_map:
                continue
            space = _space_from_model(spaces_map[sid])
            role = _RANK_ROLE.get(role_rank, SpaceRole.VIEWER)
            accesses.append(SpaceAccess(space=space, effective_role=role, is_direct=is_direct))

        return accesses
