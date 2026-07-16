from __future__ import annotations

from datetime import datetime
from uuid import UUID

from tessera_core.domain.space_role import SpaceRole


class SpaceMemberListing:
    """Read-only projection of a space membership joined with the member's identity."""

    def __init__(
        self,
        id: UUID,
        space_id: UUID,
        user_id: UUID,
        display_name: str,
        email: str,
        role: SpaceRole,
        invited_by_user_id: UUID | None,
        created_at: datetime | None,
        updated_at: datetime | None,
    ) -> None:
        self.id = id
        self.space_id = space_id
        self.user_id = user_id
        self.display_name = display_name
        self.email = email
        self.role = role
        self.invited_by_user_id = invited_by_user_id
        self.created_at = created_at
        self.updated_at = updated_at
