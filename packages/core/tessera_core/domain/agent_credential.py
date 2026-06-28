from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from tessera_core.domain.confidentiality import Confidentiality


class AgentCredential(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    name: str
    token_hash: str
    scoped_space_ids: list[UUID] = Field(default_factory=list)
    max_confidentiality: Confidentiality = Confidentiality.INTERNAL
    created_by_user_id: UUID | None = None
    company_id: UUID | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None
