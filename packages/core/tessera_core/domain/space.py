from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class Space(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    slug: str
    name: str
    sector: str
    company_id: UUID | None = None
    parent_space_id: UUID | None = None
    taxonomy: dict[str, Any] = Field(default_factory=dict)
    retention_policy: dict[str, Any] = Field(default_factory=dict)
    confidence_threshold: float = 0.7
    default_language: str = "pt-BR"
    created_at: datetime | None = None
    updated_at: datetime | None = None
