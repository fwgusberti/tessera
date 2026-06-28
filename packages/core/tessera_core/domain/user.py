from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class User(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    external_subject: str
    email: str
    display_name: str
    is_admin: bool = False
    groups: list[str] = Field(default_factory=list)
    default_language: str = "pt-BR"
    password_hash: str | None = None
    title: str | None = None
    onboarding_completed: bool = False
    created_at: datetime | None = None
