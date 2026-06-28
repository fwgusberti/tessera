from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from tessera_core.domain.join_request_status import JoinRequestStatus


class JoinRequest(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    user_id: UUID
    company_id: UUID
    status: JoinRequestStatus = JoinRequestStatus.PENDING
    requested_at: datetime | None = None
    decided_at: datetime | None = None
    decided_by_user_id: UUID | None = None
