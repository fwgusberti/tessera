"""Onboarding endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from tessera_api.adapters.audit import write_audit
from tessera_api.adapters.database import get_db
from tessera_api.adapters.repo import SqlOnboardingRepository, SqlUserRepository
from tessera_api.auth.oidc import require_user
from tessera_core.domain.entities import OnboardingProgress

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ProfileRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    title: str | None = Field(default=None, max_length=150)


class OnboardingStatusResponse(BaseModel):
    completed: bool
    current_step: str
    completed_steps: list[str]
    company_join_method: str | None


class ProfileResponse(BaseModel):
    current_step: str
    completed_steps: list[str]


class CompleteResponse(BaseModel):
    completed: bool
    completed_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _status_response(progress: OnboardingProgress) -> dict:
    return {
        "completed": progress.completed_at is not None,
        "current_step": progress.current_step,
        "completed_steps": progress.completed_steps,
        "company_join_method": progress.company_join_method,
    }


async def _get_or_create_progress(
    user_id: UUID, repo: SqlOnboardingRepository
) -> OnboardingProgress:
    progress = await repo.get_by_user_id(user_id)
    if progress is None:
        progress = await repo.create(OnboardingProgress(user_id=user_id))
    return progress


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status")
async def get_status(request: Request) -> dict:
    user_info = await require_user(request)
    user_id = UUID(user_info["sub"])

    async with get_db() as session:
        repo = SqlOnboardingRepository(session)
        progress = await _get_or_create_progress(user_id, repo)

    return _status_response(progress)


@router.post("/profile")
async def save_profile(body: ProfileRequest, request: Request) -> dict:
    user_info = await require_user(request)
    user_id = UUID(user_info["sub"])

    async with get_db() as session:
        user_repo = SqlUserRepository(session)
        user = await user_repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        from sqlalchemy import update as sa_update
        from tessera_api.adapters.models import UserModel

        await session.execute(
            sa_update(UserModel)
            .where(UserModel.id == user_id)
            .values(display_name=body.full_name, title=body.title)
        )

        ob_repo = SqlOnboardingRepository(session)
        progress = await _get_or_create_progress(user_id, ob_repo)
        progress = await ob_repo.advance_step(user_id, "company")

        await write_audit(
            session,
            actor_type="user",
            actor_id=user_id,
            action="onboarding.profile_saved",
            entity_type="user",
            entity_id=user_id,
            metadata={"title": body.title},
        )

    return {
        "current_step": progress.current_step,
        "completed_steps": progress.completed_steps,
    }


@router.post("/complete")
async def complete_onboarding(request: Request) -> dict:
    user_info = await require_user(request)
    user_id = UUID(user_info["sub"])

    async with get_db() as session:
        ob_repo = SqlOnboardingRepository(session)
        progress = await ob_repo.complete(user_id)

        from sqlalchemy import update as sa_update
        from tessera_api.adapters.models import UserModel

        await session.execute(
            sa_update(UserModel)
            .where(UserModel.id == user_id)
            .values(onboarding_completed=True)
        )

        await write_audit(
            session,
            actor_type="user",
            actor_id=user_id,
            action="onboarding.completed",
            entity_type="user",
            entity_id=user_id,
        )

    return {
        "completed": True,
        "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
    }
