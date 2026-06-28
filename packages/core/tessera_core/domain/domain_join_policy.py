from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from tessera_core.domain.domain_policy_enum import DomainPolicy


class DomainJoinPolicy(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    company_id: UUID
    domain: str
    policy: DomainPolicy
    verified: bool = False
    created_at: datetime | None = None
    verified_at: datetime | None = None
