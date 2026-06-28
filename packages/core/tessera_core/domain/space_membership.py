from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from tessera_core.domain.space_role import SpaceRole


class SpaceMembership(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    space_id: UUID
    user_id: UUID
    role: SpaceRole
    invited_by_user_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
