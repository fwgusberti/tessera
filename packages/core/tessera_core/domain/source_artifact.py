from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SourceArtifact(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    connector_id: UUID
    external_id: str
    path: str
    source_version: str | None = None
    raw_content: str | None = None
    content_hash: str
    fetched_at: datetime | None = None
