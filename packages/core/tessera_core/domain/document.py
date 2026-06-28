from __future__ import annotations

import uuid
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from tessera_core.domain.confidentiality import Confidentiality
from tessera_core.domain.document_lifecycle_state import DocumentLifecycleState


class Document(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    space_id: UUID
    owner_user_id: UUID | None = None
    title: str
    language: str = "pt-BR"
    confidentiality: Confidentiality = Confidentiality.INTERNAL
    tags: list[str] = Field(default_factory=list)
    validity_until: date | None = None
    state: DocumentLifecycleState = DocumentLifecycleState.INGESTED
    current_version_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
