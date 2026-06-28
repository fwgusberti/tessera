from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AuditRecord(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    actor_type: str
    actor_id: UUID
    action: str
    entity_type: str
    entity_id: UUID
    occurred_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
