from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OnboardingProgress(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    user_id: UUID
    completed_steps: list[str] = Field(default_factory=list)
    current_step: str = "profile"
    company_join_method: str | None = None
    company_id: UUID | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


def has_completed_onboarding(
    progress: OnboardingProgress | None, has_company_membership: bool
) -> bool:
    """Return whether the user has satisfied company onboarding.

    Belonging to at least one company is authoritative: such a user is considered
    onboarded regardless of ``completed_at`` (covers the admin-added path and
    recovers pre-existing trapped accounts). Otherwise a stored ``completed_at``
    still counts. A user with neither is not yet onboarded.
    """
    return has_company_membership or (progress is not None and progress.completed_at is not None)
