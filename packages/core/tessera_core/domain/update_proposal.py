from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from tessera_core.domain.proposal_state import ProposalState


class UpdateProposal(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    document_id: UUID
    source_artifact_id: UUID | None = None
    proposed_markdown_patch: str
    state: ProposalState = ProposalState.PENDING
    created_at: datetime | None = None
    decided_by_user_id: UUID | None = None
    decided_at: datetime | None = None
    rejection_reason: str | None = None
    drift_score: float | None = None
    summary: str | None = None
