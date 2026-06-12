"""Admin endpoints: full space management, permissions, retention, connectors."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

router = APIRouter(tags=["admin"])


class RetentionPolicyRequest(BaseModel):
    validity_days: int | None = None
    action_on_expiry: str = "archive"


@router.get("/admin/spaces")
async def list_all_spaces(request: Request) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlSpaceRepository
    from tessera_api.auth.oidc import require_user

    user_info = await require_user(request)
    if not user_info.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin required")

    async with get_db() as session:
        repo = SqlSpaceRepository(session)
        spaces = await repo.list_all()
    return {"spaces": [s.model_dump() for s in spaces]}


@router.put("/admin/spaces/{space_id}/retention")
async def update_retention_policy(
    space_id: UUID, body: RetentionPolicyRequest, request: Request
) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlSpaceRepository
    from tessera_api.auth.oidc import require_user
    from sqlalchemy import update
    from tessera_api.adapters.models import SpaceModel

    user_info = await require_user(request)
    if not user_info.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin required")

    async with get_db() as session:
        await session.execute(
            update(SpaceModel)
            .where(SpaceModel.id == space_id)
            .values(retention_policy=body.model_dump())
        )
        repo = SqlSpaceRepository(session)
        space = await repo.get_by_id(space_id)

    return {"space": space.model_dump() if space else None}
