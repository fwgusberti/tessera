"""Space management endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.audit import write_audit
from tessera_api.adapters.database import SessionDep
from tessera_api.adapters.repo import SqlSpaceMembershipRepository, SqlSpaceRepository
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
from tessera_core.services.space_hierarchy import SpaceHierarchyService

router = APIRouter(tags=["spaces"])


def _not_found() -> HTTPException:
    """Generic 404 — indistinguishable from absent (FR-004)."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": {"code": "not_found", "message": "Not found"}},
    )


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": {"code": "forbidden", "message": "Access denied"}},
    )


def _invalid_parent(reason: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"error": {"code": "invalid_parent", "message": reason}},
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


class SetParentRequest(BaseModel):
    parent_space_id: UUID


def _space_response(space: Space) -> dict:
    return space.model_dump()


def _space_access_response(access_list: list) -> list[dict]:
    result = []
    for acc in access_list:
        d = acc.space.model_dump()
        d["effective_role"] = acc.effective_role.value
        d["is_direct"] = acc.is_direct
        result.append(d)
    return result


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
    user_info, company_id = ctx
    user_id = UUID(user_info["sub"])
    repo = SqlSpaceRepository(session)
    accessible = await repo.list_accessible_by_user(user_id, company_id)
    return {"spaces": _space_access_response(accessible)}


@router.get("/spaces/{space_id}/ancestors")
async def get_ancestors(space_id: UUID, ctx: CompanyContext, session: SessionDep) -> dict:
    user_info, company_id = ctx
    user_id = UUID(user_info["sub"])
    repo = SqlSpaceRepository(session)

    # Caller must have effective access to the space (direct or inherited)
    accessible = await repo.list_accessible_by_user(user_id, company_id)
    accessible_ids = {a.space.id for a in accessible}
    if space_id not in accessible_ids:
        # Also accept: space exists in company but user has no membership at all
        space = await repo.get_by_id_for_company(space_id, company_id)
        if space is None:
            raise _not_found()
        # User has no access to this space
        raise _not_found()

    ancestors = await repo.get_ancestor_chain(space_id)
    return {
        "ancestors": [
            {"id": str(s.id), "name": s.name, "slug": s.slug}
            for s in ancestors
        ]
    }


@router.get("/spaces/{space_id}")
async def get_space(space_id: UUID, ctx: CompanyContext, session: SessionDep) -> dict:
    user_info, company_id = ctx
    user_id = UUID(user_info["sub"])
    repo = SqlSpaceRepository(session)

    # Check effective access (direct or inherited)
    accessible = await repo.list_accessible_by_user(user_id, company_id)
    accessible_ids = {a.space.id for a in accessible}

    if space_id not in accessible_ids:
        actor_id = user_id
        # Audit cross-tenant probe if space exists outside company or doesn't exist
        space_in_company = await repo.get_by_id_for_company(space_id, company_id)
        if space_in_company is None:
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

    space_access = next(a for a in accessible if a.space.id == space_id)
    return {"space": _space_response(space_access.space)}


@router.patch("/spaces/{space_id}/parent")
async def set_space_parent(
    space_id: UUID, body: SetParentRequest, ctx: CompanyContext, session: SessionDep
) -> dict:
    user_info, company_id = ctx
    user_id = UUID(user_info["sub"])

    repo = SqlSpaceRepository(session)
    membership_repo = SqlSpaceMembershipRepository(session)
    svc = SpaceHierarchyService(repo, membership_repo)

    try:
        updated = await svc.set_parent(
            actor_id=user_id,
            child_id=space_id,
            parent_id=body.parent_space_id,
            company_id=company_id,
        )
    except PermissionError as exc:
        raise _forbidden() from exc
    except ValueError as exc:
        raise _invalid_parent(str(exc)) from exc

    return {"space": _space_response(updated)}


@router.delete("/spaces/{space_id}/parent")
async def remove_space_parent(
    space_id: UUID, ctx: CompanyContext, session: SessionDep
) -> dict:
    user_info, company_id = ctx
    user_id = UUID(user_info["sub"])

    repo = SqlSpaceRepository(session)
    membership_repo = SqlSpaceMembershipRepository(session)
    svc = SpaceHierarchyService(repo, membership_repo)

    try:
        updated = await svc.remove_parent(
            actor_id=user_id,
            child_id=space_id,
            company_id=company_id,
        )
    except PermissionError as exc:
        raise _forbidden() from exc

    return {"space": _space_response(updated)}


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
