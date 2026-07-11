"""MemberAccessService — member-centric space access read model (feature 058)."""

from __future__ import annotations

from uuid import UUID

from tessera_core.domain.member_space_access import MemberSpaceAccess
from tessera_core.ports.repositories.space import SpaceRepository
from tessera_core.ports.repositories.space_membership import SpaceMembershipRepository


class MemberAccessService:
    def __init__(
        self,
        space_repo: SpaceRepository,
        membership_repo: SpaceMembershipRepository,
    ) -> None:
        self._spaces = space_repo
        self._memberships = membership_repo

    async def space_access_for_member(
        self, member_id: UUID, company_id: UUID
    ) -> list[MemberSpaceAccess]:
        """Return one row per company space with the member's direct/effective role.

        Left-joins ``list_by_company`` (all company spaces) with
        ``list_accessible_by_user`` (effective role, direct + inherited) and
        ``list_by_user`` (direct rows, filtered to company spaces — memberships in
        other companies' spaces never surface).
        """
        spaces = await self._spaces.list_by_company(company_id)
        accesses = await self._spaces.list_accessible_by_user(member_id, company_id)
        memberships = await self._memberships.list_by_user(member_id)

        company_space_ids = {s.id for s in spaces}
        effective_by_space = {a.space.id: a.effective_role for a in accesses}
        direct_by_space = {
            m.space_id: m.role for m in memberships if m.space_id in company_space_ids
        }

        return [
            MemberSpaceAccess(
                space=space,
                direct_role=direct_by_space.get(space.id),
                effective_role=effective_by_space.get(space.id),
                is_direct=space.id in direct_by_space,
            )
            for space in spaces
        ]
