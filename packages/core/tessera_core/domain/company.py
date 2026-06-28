from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Company(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    name: str
    industry: str | None = None
    team_size: str | None = None
    admin_user_id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
