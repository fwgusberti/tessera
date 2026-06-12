"""Connector config and sync endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from tessera_core.domain.entities import Connector

router = APIRouter(tags=["connectors"])


class CreateConnectorRequest(BaseModel):
    type: str
    config: dict[str, Any]
    schedule: str | None = None


@router.post("/spaces/{space_id}/connectors", status_code=status.HTTP_201_CREATED)
async def create_connector(
    space_id: UUID, body: CreateConnectorRequest, request: Request
) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlConnectorRepository
    from tessera_api.auth.oidc import require_user

    user_info = await require_user(request)
    if not user_info.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin required")

    connector = Connector(
        space_id=space_id,
        type=body.type,
        config=body.config,
        schedule=body.schedule,
    )
    async with get_db() as session:
        repo = SqlConnectorRepository(session)
        created = await repo.create(connector)
    return {"connector": created.model_dump()}


@router.post("/connectors/{connector_id}/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_connector(connector_id: UUID, request: Request) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlConnectorRepository
    from tessera_api.auth.oidc import require_user
    from tessera_workers.ingestion.tasks import sync_connector_task

    user_info = await require_user(request)
    if not user_info.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin required")

    async with get_db() as session:
        repo = SqlConnectorRepository(session)
        connector = await repo.get_by_id(connector_id)
        if connector is None:
            raise HTTPException(status_code=404, detail="Connector not found")

    task = sync_connector_task.delay(str(connector_id))
    return {"job_id": task.id}
