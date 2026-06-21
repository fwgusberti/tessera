"""Domain service for space membership management."""

from __future__ import annotations

from uuid import UUID

from tessera_core.domain.entities import AuditRecord, SpaceMembership, SpaceRole, User
from tessera_core.permissions.access import can_manage_members
from tessera_core.ports.repositories import AuditRepository, SpaceMembershipRepository


class MembershipService:
    def __init__(
        self,
        repo: SpaceMembershipRepository,
        audit: AuditRepository,
    ) -> None:
        self._repo = repo
        self._audit = audit

    async def invite(
        self,
        actor: User,
        space_id: UUID,
        user_id: UUID,
        role: SpaceRole,
    ) -> SpaceMembership:
        memberships = await self._repo.list_by_space(space_id)
        if not can_manage_members(actor, space_id, memberships):
            raise PermissionError("Only space admins can invite members")

        existing = await self._repo.get(space_id, user_id)
        if existing is not None:
            raise ValueError("already a member")

        membership = SpaceMembership(
            space_id=space_id,
            user_id=user_id,
            role=role,
            invited_by_user_id=actor.id,
        )
        created = await self._repo.add(membership)

        await self._audit.append(
            AuditRecord(
                actor_type="user",
                actor_id=actor.id,
                action="member_invited",
                entity_type="space_membership",
                entity_id=created.id,
                metadata={
                    "space_id": str(space_id),
                    "user_id": str(user_id),
                    "role": role.value,
                },
            )
        )
        return created

    async def change_role(
        self,
        actor: User,
        space_id: UUID,
        user_id: UUID,
        new_role: SpaceRole,
    ) -> SpaceMembership:
        memberships = await self._repo.list_by_space(space_id)
        if not can_manage_members(actor, space_id, memberships):
            raise PermissionError("Only space admins can change member roles")

        target = next((m for m in memberships if m.user_id == user_id), None)
        if target is None:
            raise ValueError("not a member")

        previous_role = target.role

        if new_role != SpaceRole.ADMIN and previous_role == SpaceRole.ADMIN:
            admin_count = await self._repo.count_admins(space_id)
            if admin_count <= 1:
                raise ValueError("last admin")

        updated = await self._repo.update_role(space_id, user_id, new_role)

        await self._audit.append(
            AuditRecord(
                actor_type="user",
                actor_id=actor.id,
                action="role_changed",
                entity_type="space_membership",
                entity_id=updated.id,
                metadata={
                    "space_id": str(space_id),
                    "user_id": str(user_id),
                    "previous_role": previous_role.value,
                    "new_role": new_role.value,
                },
            )
        )
        return updated

    async def remove(
        self,
        actor: User,
        space_id: UUID,
        user_id: UUID,
    ) -> None:
        memberships = await self._repo.list_by_space(space_id)
        if not can_manage_members(actor, space_id, memberships):
            raise PermissionError("Only space admins can remove members")

        target = next((m for m in memberships if m.user_id == user_id), None)
        if target is None:
            raise ValueError("not a member")

        if target.role == SpaceRole.ADMIN:
            admin_count = await self._repo.count_admins(space_id)
            if admin_count <= 1:
                raise ValueError("last admin")

        previous_role = target.role
        await self._repo.remove(space_id, user_id)

        await self._audit.append(
            AuditRecord(
                actor_type="user",
                actor_id=actor.id,
                action="member_removed",
                entity_type="space_membership",
                entity_id=target.id,
                metadata={
                    "space_id": str(space_id),
                    "user_id": str(user_id),
                    "previous_role": previous_role.value,
                },
            )
        )
