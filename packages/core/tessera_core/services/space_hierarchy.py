"""SpaceHierarchyService — domain logic for nested-space hierarchy."""

from __future__ import annotations

from uuid import UUID

from tessera_core.domain.space import Space
from tessera_core.domain.space_access import SpaceAccess
from tessera_core.domain.space_role import SpaceRole
from tessera_core.ports.repositories.space import SpaceRepository
from tessera_core.ports.repositories.space_membership import SpaceMembershipRepository

_MAX_DEPTH = 10


class SpaceHierarchyService:
    def __init__(
        self,
        space_repo: SpaceRepository,
        membership_repo: SpaceMembershipRepository,
    ) -> None:
        self._spaces = space_repo
        self._memberships = membership_repo

    async def list_accessible(self, user_id: UUID, company_id: UUID) -> list[SpaceAccess]:
        """Return all SpaceAccess objects for the user in the given company."""
        return await self._spaces.list_accessible_by_user(user_id, company_id)

    async def set_parent(
        self,
        actor_id: UUID,
        child_id: UUID,
        parent_id: UUID,
        company_id: UUID,
    ) -> Space:
        """Set parent_id as the parent of child_id.

        Validates:
        - Self-parent
        - Cross-company parent (invisible → cross_company)
        - Actor is ADMIN in child
        - Actor is ADMIN in parent
        - No cycle
        - Depth ≤ 10
        """
        if child_id == parent_id:
            raise ValueError("self_parent")

        # Verify parent exists in company
        parent_space = await self._spaces.get_by_id_for_company(parent_id, company_id)
        if parent_space is None:
            raise ValueError("cross_company")

        # Check actor admin in child
        child_membership = await self._memberships.get(child_id, actor_id)
        if child_membership is None or child_membership.role != SpaceRole.ADMIN:
            raise PermissionError("Actor must be admin of child space")

        # Check actor admin in parent
        parent_membership = await self._memberships.get(parent_id, actor_id)
        if parent_membership is None or parent_membership.role != SpaceRole.ADMIN:
            raise PermissionError("Actor must be admin of parent space")

        # Cycle check: parent's ancestor chain must not contain child_id
        ancestor_chain = await self._spaces.get_ancestor_chain(parent_id)
        ancestor_ids = {s.id for s in ancestor_chain}
        if child_id in ancestor_ids:
            raise ValueError("cycle")

        # Depth limit check
        if len(ancestor_chain) + 1 >= _MAX_DEPTH:
            raise ValueError("depth_limit")

        updated = await self._spaces.set_parent(child_id, parent_id)
        return updated

    async def remove_parent(
        self,
        actor_id: UUID,
        child_id: UUID,
        company_id: UUID,
    ) -> Space:
        """Promote space to root by removing its parent.

        Requires actor to be ADMIN in child space.
        """
        child_membership = await self._memberships.get(child_id, actor_id)
        if child_membership is None or child_membership.role != SpaceRole.ADMIN:
            raise PermissionError("Actor must be admin of child space")

        updated = await self._spaces.remove_parent(child_id)
        return updated

    async def rename(
        self,
        actor_id: UUID,
        space_id: UUID,
        name: str,
        company_id: UUID,
    ) -> Space:
        """Rename a space.

        Validates:
        - Space exists in company
        - Actor is ADMIN in space
        - name is non-empty after trim and <= 255 chars
        """
        space = await self._spaces.get_by_id_for_company(space_id, company_id)
        if space is None:
            raise ValueError("not_found")

        membership = await self._memberships.get(space_id, actor_id)
        if membership is None or membership.role != SpaceRole.ADMIN:
            raise PermissionError("Actor must be admin of space")

        trimmed = name.strip()
        if not trimmed:
            raise ValueError("empty_name")
        if len(trimmed) > 255:
            raise ValueError("name_too_long")

        return await self._spaces.rename(space_id, trimmed)

    async def get_ancestor_path(self, space_id: UUID, company_id: UUID) -> list[Space]:
        """Return ancestor chain for breadcrumb display (no access grant implied)."""
        space = await self._spaces.get_by_id_for_company(space_id, company_id)
        if space is None:
            raise ValueError("not_found")
        return await self._spaces.get_ancestor_chain(space_id)
