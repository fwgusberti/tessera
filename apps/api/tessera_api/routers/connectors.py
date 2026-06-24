"""Connector config and sync endpoints.

Company-scoped (feature 035): creating a connector requires the target space to
belong to a company the caller administers, and syncing requires the connector to
belong to it. A cross-company attempt is audited as ``cross_tenant_denied`` and
returns the generic 403 body — and crucially enqueues no Celery sync job.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from tessera_api.adapters.audit import write_audit
from tessera_api.adapters.database import get_db
from tessera_api.adapters.repo import SqlConnectorRepository, SqlSpaceRepository
from tessera_api.auth.oidc import require_company_admin
from tessera_core.domain.entities import Connector

try:
    # The workers package ships in a separate runtime/env; import it at module
    # level so tests can patch ``sync_connector_task``, but tolerate its absence
    # so the API app still imports where workers isn't installed.
    from tessera_workers.ingestion.tasks import sync_connector_task
except ModuleNotFoundError:  # pragma: no cover - depends on deployment env
    sync_connector_task = None

router = APIRouter(tags=["connectors"])


class CreateConnectorRequest(BaseModel):
    type: str
    config: dict[str, Any]
    schedule: str | None = None


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": {"code": "forbidden", "message": "Access denied"}},
    )


async def _audit_cross_tenant_denied(
    actor_id: UUID, entity_type: str, entity_id: UUID, company_id: UUID
) -> None:
    async with get_db() as audit_session:
        await write_audit(
            audit_session,
            actor_type="user",
            actor_id=actor_id,
            action="cross_tenant_denied",
            entity_type=entity_type,
            entity_id=entity_id,
            metadata={"company_id": str(company_id)},
        )


@router.post("/spaces/{space_id}/connectors", status_code=status.HTTP_201_CREATED)
async def create_connector(space_id: UUID, body: CreateConnectorRequest, request: Request) -> dict:
    user_info, company_id, _membership = await require_company_admin(request)
    actor_id = UUID(user_info["sub"])

    async with get_db() as session:
        space_repo = SqlSpaceRepository(session)
        space = await space_repo.get_by_id_for_company(space_id, company_id)

    if space is None:
        await _audit_cross_tenant_denied(actor_id, "space", space_id, company_id)
        raise _forbidden()

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
    user_info, company_id, _membership = await require_company_admin(request)
    actor_id = UUID(user_info["sub"])

    async with get_db() as session:
        repo = SqlConnectorRepository(session)
        connector = await repo.get_by_id_for_company(connector_id, company_id)

    if connector is None:
        # Deny and audit BEFORE enqueuing any work (FR-005).
        await _audit_cross_tenant_denied(actor_id, "connector", connector_id, company_id)
        raise _forbidden()

    task = sync_connector_task.delay(str(connector_id))
    return {"job_id": task.id}
