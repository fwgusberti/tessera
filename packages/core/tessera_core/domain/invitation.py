from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from tessera_core.domain.company_role import CompanyRole
from tessera_core.domain.invitation_status import InvitationStatus


class Invitation(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    company_id: UUID
    invited_by_user_id: UUID | None = None
    email: str
    token_hash: str
    status: InvitationStatus = InvitationStatus.PENDING
    role: CompanyRole = CompanyRole.MEMBER
    expires_at: datetime
    created_at: datetime | None = None
    accepted_at: datetime | None = None
