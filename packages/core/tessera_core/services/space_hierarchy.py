"""SpaceHierarchyService — domain logic for nested-space hierarchy."""

from __future__ import annotations

from uuid import UUID

from tessera_core.domain.space import Space
from tessera_core.domain.space_access import SpaceAccess
from tessera_core.domain.space_role import SpaceRole
from tessera_core.ports.repositories.space import SpaceRepository
from tessera_core.ports.repositories.space_membership import SpaceMembershipRepository
from tessera_core.services.slug import slugify

_MAX_DEPTH = 10


class SpaceHierarchyService:
    def __init__(
        self,
        space_repo: SpaceRepository,
        membership_repo: SpaceMembershipRepository,
    ) -> None:
        self._spaces = space_repo
        self._memberships = membership_repo

    async def list_accessible(
        self, user_id: UUID, company_id: UUID, is_company_admin: bool = False
    ) -> list[SpaceAccess]:
        """Return all SpaceAccess objects for the user in the given company.

        Company admins additionally see every remaining company space as implicit
        ``SpaceAccess(effective_role=ADMIN, is_direct=False)`` — the read-side
        expression of the implicit-admin rule (feature 036). Membership-derived
        accesses are passed through unchanged. Both source queries are scoped to
        ``company_id``, so no cross-company space can surface (Constitution VI).
        """
        accesses = await self._spaces.list_accessible_by_user(user_id, company_id)
        if not is_company_admin:
            return accesses

        covered = {a.space.id for a in accesses}
        company_spaces = await self._spaces.list_by_company(company_id)
        implicit = [
            SpaceAccess(space=space, effective_role=SpaceRole.ADMIN, is_direct=False)
            for space in company_spaces
            if space.id not in covered
        ]
        return accesses + implicit

    async def get_access(
        self,
        user_id: UUID,
        space_id: UUID,
        company_id: UUID,
        is_company_admin: bool = False,
    ) -> SpaceAccess | None:
        """Return the user's access to a single space, honoring the admin branch."""
        accesses = await self.list_accessible(user_id, company_id, is_company_admin)
        return next((a for a in accesses if a.space.id == space_id), None)

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

    async def create(
        self,
        actor_id: UUID,
        company_id: UUID,
        name: str,
        sector: str = "General",
        slug: str | None = None,
        parent_space_id: UUID | None = None,
        default_language: str = "pt-BR",
        retention_policy: dict | None = None,
        confidence_threshold: float = 0.7,
    ) -> Space:
        """Create a new space, optionally nested under parent_space_id.

        Validates:
        - name is non-empty after trim and <= 255 chars
        - if parent_space_id is set: it resolves in company, actor is ADMIN
          there, and the resulting depth stays within the limit
        Auto-derives a unique slug from name when slug is not given.
        """
        trimmed = name.strip()
        if not trimmed:
            raise ValueError("empty_name")
        if len(trimmed) > 255:
            raise ValueError("name_too_long")

        if parent_space_id is not None:
            parent_space = await self._spaces.get_by_id_for_company(parent_space_id, company_id)
            if parent_space is None:
                raise ValueError("cross_company")

            parent_membership = await self._memberships.get(parent_space_id, actor_id)
            if parent_membership is None or parent_membership.role != SpaceRole.ADMIN:
                raise PermissionError("Actor must be admin of parent space")

            ancestor_chain = await self._spaces.get_ancestor_chain(parent_space_id)
            if len(ancestor_chain) + 1 >= _MAX_DEPTH:
                raise ValueError("depth_limit")

        resolved_slug = await self._resolve_slug(slug, trimmed)

        return await self._spaces.create(
            Space(
                slug=resolved_slug,
                name=trimmed,
                sector=sector.strip() or "General",
                company_id=company_id,
                parent_space_id=parent_space_id,
                retention_policy=retention_policy or {},
                confidence_threshold=confidence_threshold,
                default_language=default_language,
            )
        )

    async def delete(
        self,
        actor_id: UUID,
        space_id: UUID,
        company_id: UUID,
        is_company_admin: bool = False,
    ) -> tuple[int, int]:
        """Delete a space and its full descendant subtree.

        Validates:
        - Space exists in company (ValueError("not_found") otherwise)
        - Actor is ADMIN in space, or is_company_admin is True (PermissionError otherwise)

        Returns (deleted_space_count, deleted_document_count).
        """
        space = await self._spaces.get_by_id_for_company(space_id, company_id)
        if space is None:
            raise ValueError("not_found")

        if not is_company_admin:
            membership = await self._memberships.get(space_id, actor_id)
            if membership is None or membership.role != SpaceRole.ADMIN:
                raise PermissionError("Actor must be admin of space")

        return await self._spaces.delete_subtree(space_id)

    async def _resolve_slug(self, slug: str | None, name: str) -> str:
        if slug:
            return slug

        base = slugify(name)
        candidate = base
        suffix = 2
        while await self._spaces.slug_exists(candidate):
            candidate = f"{base}-{suffix}"[:100]
            suffix += 1
        return candidate

    async def get_ancestor_path(self, space_id: UUID, company_id: UUID) -> list[Space]:
        """Return ancestor chain for breadcrumb display (no access grant implied)."""
        space = await self._spaces.get_by_id_for_company(space_id, company_id)
        if space is None:
            raise ValueError("not_found")
        return await self._spaces.get_ancestor_chain(space_id)
