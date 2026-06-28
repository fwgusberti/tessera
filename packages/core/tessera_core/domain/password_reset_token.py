from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PasswordResetToken(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    user_id: UUID
    token_hash: str
    created_at: datetime | None = None
    expires_at: datetime
    consumed_at: datetime | None = None
