from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from tessera_core.domain.confidentiality import Confidentiality


class Chunk(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    document_version_id: UUID
    document_id: UUID
    space_id: UUID
    ordinal: int
    text: str
    embedding: list[float] | None = None
    confidentiality: Confidentiality = Confidentiality.INTERNAL
    language: str = "pt-BR"
    created_at: datetime | None = None
