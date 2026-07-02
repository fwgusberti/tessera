from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentDraft(BaseModel):
    document_id: UUID
    content_markdown: str
    editor_user_id: UUID
    started_at: datetime
    last_autosaved_at: datetime
