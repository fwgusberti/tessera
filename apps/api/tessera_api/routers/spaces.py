"""Space management endpoints."""

from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from tessera_core.domain.entities import Confidentiality, RolePermission, Space, UserRole
from tessera_core.permissions.access import AccessContext, can_admin_space

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
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlSpaceRepository
    from tessera_api.auth.oidc import require_user

    user_info = await require_user(request)
    if not user_info.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")

    space = Space(
        slug=body.slug,
        name=body.name,
        sector=body.sector,
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
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlSpaceRepository
    from tessera_api.auth.oidc import require_user

    user_info = await require_user(request)
    async with get_db() as session:
        repo = SqlSpaceRepository(session)
        spaces = await repo.list_all()
    return {"spaces": [s.model_dump() for s in spaces]}


@router.post("/spaces/{space_id}/permissions", status_code=status.HTTP_201_CREATED)
async def create_permission(space_id: UUID, body: CreatePermissionRequest, request: Request) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlSpaceRepository
    from tessera_api.auth.oidc import require_user

    user_info = await require_user(request)
    if not user_info.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")

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
