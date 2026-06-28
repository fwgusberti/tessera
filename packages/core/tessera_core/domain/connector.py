from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class Connector(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    space_id: UUID
    type: str
    config: dict[str, Any] = Field(default_factory=dict)
    schedule: str | None = None
    last_sync_at: datetime | None = None
    status: str = "ok"
    created_at: datetime | None = None
    updated_at: datetime | None = None
