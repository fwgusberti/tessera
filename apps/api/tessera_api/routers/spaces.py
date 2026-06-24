"""Space management endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from tessera_api.adapters.audit import write_audit
from tessera_api.adapters.database import get_db
from tessera_api.adapters.repo import SqlSpaceRepository
from tessera_api.auth.oidc import require_company_admin, require_company_context
from tessera_core.domain.entities import (
    Confidentiality,
    RolePermission,
    Space,
    UserRole,
)

router = APIRouter(tags=["spaces"])


class CreateSpaceRequest(BaseModel):
    slug: str
    name: str
    sector: str
    default_language: str = "pt-BR"
    retention_policy: dict[str, Any] = {}
    confidence_threshold: float = 0.7


class CreatePermissionRequest(BaseModel):
    idp_group: str
    role: UserRole
    max_confidentiality: Confidentiality = Confidentiality.INTERNAL


@router.post("/spaces", status_code=status.HTTP_201_CREATED)
async def create_space(body: CreateSpaceRequest, request: Request) -> dict:
    user_info, company_id = await require_company_context(request)

    space = Space(
        slug=body.slug,
        name=body.name,
        sector=body.sector,
        company_id=company_id,
        default_language=body.default_language,
        retention_policy=body.retention_policy,
        confidence_threshold=body.confidence_threshold,
    )
    async with get_db() as session:
        repo = SqlSpaceRepository(session)
        created = await repo.create(space)
    return {"space": created.model_dump()}


@router.get("/spaces")
async def list_spaces(request: Request) -> dict:
    user_info, company_id = await require_company_context(request)
    async with get_db() as session:
        repo = SqlSpaceRepository(session)
        spaces = await repo.list_by_company(company_id)
    return {"spaces": [s.model_dump() for s in spaces]}


@router.get("/spaces/{space_id}")
async def get_space(space_id: UUID, request: Request) -> dict:
    user_info, company_id = await require_company_context(request)
    async with get_db() as session:
        repo = SqlSpaceRepository(session)
        space = await repo.get_by_id_for_company(space_id, company_id)

    if space is None:
        actor_id = UUID(user_info["sub"])
        async with get_db() as audit_session:
            await write_audit(
                audit_session,
                actor_type="user",
                actor_id=actor_id,
                action="cross_tenant_denied",
                entity_type="space",
                entity_id=space_id,
                metadata={"company_id": str(company_id)},
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "forbidden", "message": "Access denied"}},
        )

    return {"space": space.model_dump()}


async def validate_space_for_company(space_id: UUID, company_id: UUID) -> None:
    """Raise 403 if space_id does not belong to company_id."""
    async with get_db() as session:
        repo = SqlSpaceRepository(session)
        space = await repo.get_by_id_for_company(space_id, company_id)
    if space is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "forbidden", "message": "Access denied"}},
        )


@router.post("/spaces/{space_id}/permissions", status_code=status.HTTP_201_CREATED)
async def create_permission(
    space_id: UUID, body: CreatePermissionRequest, request: Request
) -> dict:
    user_info, company_id, _membership = await require_company_admin(request)

    async with get_db() as session:
        repo = SqlSpaceRepository(session)
        space = await repo.get_by_id_for_company(space_id, company_id)

    if space is None:
        actor_id = UUID(user_info["sub"])
        async with get_db() as audit_session:
            await write_audit(
                audit_session,
                actor_type="user",
                actor_id=actor_id,
                action="cross_tenant_denied",
                entity_type="space",
                entity_id=space_id,
                metadata={"company_id": str(company_id)},
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "forbidden", "message": "Access denied"}},
        )

    permission = RolePermission(
        space_id=space_id,
        idp_group=body.idp_group,
        role=body.role,
        max_confidentiality=body.max_confidentiality,
    )
    async with get_db() as session:
        repo = SqlSpaceRepository(session)
        created = await repo.create_role_permission(permission)
    return {"permission": created.model_dump()}
