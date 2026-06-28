"""Admin endpoints: full space management, permissions, retention, connectors."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text, update

from tessera_api.adapters.celery import get_celery_app
from tessera_api.adapters.database import get_db
from tessera_api.adapters.models import SpaceModel
from tessera_api.adapters.repo import SqlAuditRepository, SqlSpaceRepository, SqlUserRepository
from tessera_api.auth.oidc import require_user
from tessera_core.domain.entities import AuditRecord

router = APIRouter(tags=["admin"])

# Sentinel entity id for fleet-wide operator actions that span all companies
# (the space-list sweep and bulk reindex), which have no single affected space.
_FLEET_WIDE = UUID(int=0)


class PlatformRoleRequest(BaseModel):
    is_admin: bool


@router.put("/users/{user_id}/platform-role")
async def set_platform_role(user_id: UUID, body: PlatformRoleRequest, request: Request) -> dict:
    user_info = await require_user(request)
    actor_id = UUID(user_info.get("id") or user_info.get("sub"))

    async with get_db() as session:
        user_repo = SqlUserRepository(session)
        actor = await user_repo.get_by_id(actor_id)
        if actor is None or not actor.is_admin:
            raise HTTPException(status_code=403, detail="Global Admin required")

        target = await user_repo.get_by_id(user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="User not found")

        previous_is_admin = target.is_admin
        updated = await user_repo.set_admin(user_id, body.is_admin)

        audit_repo = SqlAuditRepository(session)
        await audit_repo.append(
            AuditRecord(
                actor_type="user",
                actor_id=actor_id,
                action="platform_role_changed",
                entity_type="user",
                entity_id=user_id,
                metadata={
                    "user_id": str(user_id),
                    "previous_is_admin": previous_is_admin,
                    "new_is_admin": body.is_admin,
                },
            )
        )

    return {
        "user": {
            "id": str(updated.id),
            "display_name": updated.display_name,
            "email": updated.email,
            "is_admin": updated.is_admin,
        }
    }


class RetentionPolicyRequest(BaseModel):
    validity_days: int | None = None
    action_on_expiry: str = "archive"


@router.get("/admin/spaces")
async def list_all_spaces(request: Request) -> dict:
    user_info = await require_user(request)
    if not user_info.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin required")
    actor_id = UUID(user_info.get("id") or user_info.get("sub"))

    async with get_db() as session:
        repo = SqlSpaceRepository(session)
        spaces = await repo.list_all()
        # Single documented cross-tenant exception — audit the cross-company read.
        audit_repo = SqlAuditRepository(session)
        await audit_repo.append(
            AuditRecord(
                actor_type="user",
                actor_id=actor_id,
                action="cross_company_admin_access",
                entity_type="spaces",
                entity_id=_FLEET_WIDE,
                metadata={"endpoint": "/admin/spaces", "operation": "list"},
            )
        )
    return {"spaces": [s.model_dump() for s in spaces]}


@router.put("/admin/spaces/{space_id}/retention")
async def update_retention_policy(
    space_id: UUID, body: RetentionPolicyRequest, request: Request
) -> dict:
    user_info = await require_user(request)
    if not user_info.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin required")
    actor_id = UUID(user_info.get("id") or user_info.get("sub"))

    async with get_db() as session:
        await session.execute(
            update(SpaceModel)
            .where(SpaceModel.id == space_id)
            .values(retention_policy=body.model_dump())
        )
        repo = SqlSpaceRepository(session)
        space = await repo.get_by_id(space_id)
        # Single documented cross-tenant exception — audit the cross-company write.
        audit_repo = SqlAuditRepository(session)
        await audit_repo.append(
            AuditRecord(
                actor_type="user",
                actor_id=actor_id,
                action="cross_company_admin_access",
                entity_type="space",
                entity_id=space_id,
                metadata={
                    "endpoint": "/admin/spaces/{id}/retention",
                    "operation": "retention",
                },
            )
        )

    return {"space": space.model_dump() if space else None}


@router.post("/admin/reindex")
async def bulk_reindex(request: Request) -> dict:
    """Dispatch reindex tasks for all published documents with zero chunks."""
    user_info = await require_user(request)
    if not user_info.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin required")
    actor_id = UUID(user_info.get("id") or user_info.get("sub"))

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
        # Single documented cross-tenant exception — audit the fleet-wide dispatch.
        audit_repo = SqlAuditRepository(session)
        await audit_repo.append(
            AuditRecord(
                actor_type="user",
                actor_id=actor_id,
                action="cross_company_admin_access",
                entity_type="spaces",
                entity_id=_FLEET_WIDE,
                metadata={
                    "endpoint": "/admin/reindex",
                    "operation": "reindex",
                    "dispatched": len(rows),
                },
            )
        )

    celery = get_celery_app()
    for row in rows:
        celery.send_task(
            "tessera.index_document_version",
            args=[str(row["version_id"]), str(row["id"]), str(row["space_id"])],
        )

    return {"dispatched": len(rows)}
