from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OnboardingProgress(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    user_id: UUID
    completed_steps: list[str] = Field(default_factory=list)
    current_step: str = "profile"
    company_join_method: str | None = None
    company_id: UUID | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
