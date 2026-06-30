"""Space management endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.audit import write_audit
from tessera_api.adapters.database import SessionDep
from tessera_api.adapters.repo import SqlSpaceRepository
from tessera_api.auth.oidc import (
    CompanyAdminContext,
    CompanyContext,
)
from tessera_core.domain.entities import (
    Confidentiality,
    RolePermission,
    Space,
    UserRole,
)

router = APIRouter(tags=["spaces"])


def _not_found() -> HTTPException:
    """Generic 404 for cross-company by-ID access — indistinguishable from absent (FR-004)."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": {"code": "not_found", "message": "Not found"}},
    )


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
async def create_space(
    body: CreateSpaceRequest, ctx: CompanyContext, session: SessionDep
) -> dict:
    user_info, company_id = ctx
    space = Space(
        slug=body.slug,
        name=body.name,
        sector=body.sector,
        company_id=company_id,
        default_language=body.default_language,
        retention_policy=body.retention_policy,
        confidence_threshold=body.confidence_threshold,
    )
    repo = SqlSpaceRepository(session)
    created = await repo.create(space)
    return {"space": created.model_dump()}


@router.get("/spaces")
async def list_spaces(ctx: CompanyContext, session: SessionDep) -> dict:
    _user_info, company_id = ctx
    repo = SqlSpaceRepository(session)
    spaces = await repo.list_by_company(company_id)
    return {"spaces": [s.model_dump() for s in spaces]}


@router.get("/spaces/{space_id}")
async def get_space(space_id: UUID, ctx: CompanyContext, session: SessionDep) -> dict:
    user_info, company_id = ctx
    repo = SqlSpaceRepository(session)
    space = await repo.get_by_id_for_company(space_id, company_id)

    if space is None:
        actor_id = UUID(user_info["sub"])
        await write_audit(
            session,
            actor_type="user",
            actor_id=actor_id,
            action="cross_tenant_denied",
            entity_type="space",
            entity_id=space_id,
            metadata={"company_id": str(company_id)},
        )
        await session.commit()
        raise _not_found()

    return {"space": space.model_dump()}


async def validate_space_for_company(
    space_id: UUID, company_id: UUID, session: AsyncSession
) -> None:
    """Raise 404 if space_id does not belong to company_id (indistinguishable from absent)."""
    repo = SqlSpaceRepository(session)
    space = await repo.get_by_id_for_company(space_id, company_id)
    if space is None:
        raise _not_found()


@router.post("/spaces/{space_id}/permissions", status_code=status.HTTP_201_CREATED)
async def create_permission(
    space_id: UUID, body: CreatePermissionRequest, ctx: CompanyAdminContext, session: SessionDep
) -> dict:
    user_info, company_id, _membership = ctx
    repo = SqlSpaceRepository(session)
    space = await repo.get_by_id_for_company(space_id, company_id)

    if space is None:
        actor_id = UUID(user_info["sub"])
        await write_audit(
            session,
            actor_type="user",
            actor_id=actor_id,
            action="cross_tenant_denied",
            entity_type="space",
            entity_id=space_id,
            metadata={"company_id": str(company_id)},
        )
        await session.commit()
        raise _not_found()

    permission = RolePermission(
        space_id=space_id,
        idp_group=body.idp_group,
        role=body.role,
        max_confidentiality=body.max_confidentiality,
    )
    created = await repo.create_role_permission(permission)
    return {"permission": created.model_dump()}
