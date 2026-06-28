from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from tessera_core.domain.confidentiality import Confidentiality
from tessera_core.domain.user_role import UserRole


class RolePermission(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    space_id: UUID
    idp_group: str
    role: UserRole
    max_confidentiality: Confidentiality = Confidentiality.INTERNAL
    created_at: datetime | None = None
