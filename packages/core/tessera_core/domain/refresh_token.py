from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from tessera_core.domain.token_kind import TokenKind


class RefreshToken(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    user_id: UUID
    token_hash: str
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    is_revoked: bool = False
    company_id: UUID | None = None
    token_kind: TokenKind = "full"
