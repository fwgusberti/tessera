"""Admin endpoints: full space management, permissions, retention, connectors."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
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
    from sqlalchemy import update

    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.models import SpaceModel
    from tessera_api.adapters.repo import SqlSpaceRepository
    from tessera_api.auth.oidc import require_user

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


@router.post("/admin/reindex")
async def bulk_reindex(request: Request) -> dict:
    """Dispatch reindex tasks for all published documents with zero chunks."""
    from sqlalchemy import text

    from tessera_api.adapters.celery import get_celery_app
    from tessera_api.adapters.database import get_db
    from tessera_api.auth.oidc import require_user

    user_info = await require_user(request)
    if not user_info.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin required")

    async with get_db() as session:
        result = await session.execute(text("""
            SELECT d.id, d.space_id, dv.id AS version_id
            FROM documents d
            JOIN document_versions dv ON dv.id = d.current_version_id
            WHERE d.state = 'published'
              AND d.current_version_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM chunks c WHERE c.document_id = d.id
              )
        """))
        rows = result.mappings().all()

    celery = get_celery_app()
    for row in rows:
        celery.send_task(
            "tessera.index_document_version",
            args=[str(row["version_id"]), str(row["id"]), str(row["space_id"])],
        )

    return {"dispatched": len(rows)}
