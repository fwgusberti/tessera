from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from tessera_core.domain.company_role import CompanyRole


class CompanyMembership(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    user_id: UUID
    company_id: UUID
    role: CompanyRole
    joined_at: datetime | None = None
