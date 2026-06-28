from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentVersion(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    document_id: UUID
    version_number: int
    content_markdown: str
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    author_user_id: UUID | None = None
    approver_user_id: UUID | None = None
    approved_at: datetime | None = None
    source_artifact_id: UUID | None = None
    created_from_proposal_id: UUID | None = None
    created_at: datetime | None = None
