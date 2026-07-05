"""Space management endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.audit import write_audit
from tessera_api.adapters.database import SessionDep
from tessera_api.adapters.repo import (
    SqlSpaceMembershipRepository,
    SqlSpaceRepository,
    SqlUserRepository,
)
from tessera_api.auth.jwt_auth import verify_password
from tessera_api.auth.oidc import (
    CompanyAdminContext,
    CompanyContext,
    CompanyMemberContext,
    is_company_admin,
)
from tessera_core.domain.entities import (
    Confidentiality,
    RolePermission,
    Space,
    SpaceMembership,
    SpaceRole,
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


def _invalid_name(reason: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"error": {"code": "invalid_name", "message": reason}},
    )


class CreateSpaceRequest(BaseModel):
    name: str
    slug: str | None = None
    sector: str = "General"
    parent_space_id: UUID | None = None
    default_language: str = "pt-BR"
    retention_policy: dict[str, Any] = {}
    confidence_threshold: float = 0.7


class CreatePermissionRequest(BaseModel):
    idp_group: str
    role: UserRole
    max_confidentiality: Confidentiality = Confidentiality.INTERNAL


class SetParentRequest(BaseModel):
    parent_space_id: UUID


class RenameSpaceRequest(BaseModel):
    name: str


class DeleteSpaceRequest(BaseModel):
    password: str


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
async def create_space(body: CreateSpaceRequest, ctx: CompanyContext, session: SessionDep) -> dict:
    user_info, company_id = ctx
    actor_id = UUID(user_info.get("id") or user_info["sub"])

    repo = SqlSpaceRepository(session)
    membership_repo = SqlSpaceMembershipRepository(session)
    svc = SpaceHierarchyService(repo, membership_repo)

    try:
        created = await svc.create(
            actor_id=actor_id,
            company_id=company_id,
            name=body.name,
            sector=body.sector,
            slug=body.slug,
            parent_space_id=body.parent_space_id,
            default_language=body.default_language,
            retention_policy=body.retention_policy,
            confidence_threshold=body.confidence_threshold,
        )
    except PermissionError as exc:
        raise _forbidden() from exc
    except ValueError as exc:
        reason = str(exc)
        if reason in ("cross_company", "depth_limit"):
            raise _invalid_parent(reason) from exc
        raise _invalid_name(reason) from exc

    # Grant the creator admin access immediately (042) — there is no existing
    # membership yet to authorize against, so this bypasses MembershipService.invite
    # the same way create_company grants its creator an admin CompanyMembership directly.
    membership = await membership_repo.add(
        SpaceMembership(space_id=created.id, user_id=actor_id, role=SpaceRole.ADMIN)
    )
    await write_audit(
        session,
        actor_type="user",
        actor_id=actor_id,
        action="space_created",
        entity_type="space",
        entity_id=created.id,
        metadata={
            "company_id": str(company_id),
            "parent_space_id": str(body.parent_space_id) if body.parent_space_id else None,
        },
    )
    await write_audit(
        session,
        actor_type="user",
        actor_id=actor_id,
        action="member_invited",
        entity_type="space_membership",
        entity_id=membership.id,
        metadata={
            "space_id": str(created.id),
            "user_id": str(actor_id),
            "role": SpaceRole.ADMIN.value,
        },
    )

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
    return {"ancestors": [{"id": str(s.id), "name": s.name, "slug": s.slug} for s in ancestors]}


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
async def remove_space_parent(space_id: UUID, ctx: CompanyContext, session: SessionDep) -> dict:
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


@router.patch("/spaces/{space_id}/name")
async def rename_space(
    space_id: UUID, body: RenameSpaceRequest, ctx: CompanyContext, session: SessionDep
) -> dict:
    user_info, company_id = ctx
    user_id = UUID(user_info["sub"])

    repo = SqlSpaceRepository(session)
    membership_repo = SqlSpaceMembershipRepository(session)
    svc = SpaceHierarchyService(repo, membership_repo)

    try:
        updated = await svc.rename(
            actor_id=user_id,
            space_id=space_id,
            name=body.name,
            company_id=company_id,
        )
    except PermissionError as exc:
        raise _forbidden() from exc
    except ValueError as exc:
        reason = str(exc)
        if reason == "not_found":
            await write_audit(
                session,
                actor_type="user",
                actor_id=user_id,
                action="cross_tenant_denied",
                entity_type="space",
                entity_id=space_id,
                metadata={"company_id": str(company_id)},
            )
            await session.commit()
            raise _not_found() from exc
        raise _invalid_name(reason) from exc

    await write_audit(
        session,
        actor_type="user",
        actor_id=user_id,
        action="space_renamed",
        entity_type="space",
        entity_id=space_id,
        metadata={"new_name": updated.name},
    )

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


@router.delete("/spaces/{space_id}")
async def delete_space(
    space_id: UUID, body: DeleteSpaceRequest, ctx: CompanyMemberContext, session: SessionDep
) -> dict:
    user_info, company_id, caller_membership = ctx
    actor_id = UUID(user_info["sub"])

    # Re-verify the caller's own password before any destructive action. This
    # depends only on the caller's account, so running it first cannot leak
    # anything about the target space's existence or the caller's access to it.
    user = await SqlUserRepository(session).get_by_id(actor_id)
    if (
        user is None
        or not user.password_hash
        or not verify_password(body.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "invalid_credentials",
                    "message": "Current password is incorrect",
                }
            },
        )

    svc = SpaceHierarchyService(SqlSpaceRepository(session), SqlSpaceMembershipRepository(session))
    try:
        deleted_space_count, deleted_document_count = await svc.delete(
            actor_id=actor_id,
            space_id=space_id,
            company_id=company_id,
            is_company_admin=is_company_admin(caller_membership),
        )
    except PermissionError as exc:
        raise _forbidden() from exc
    except ValueError as exc:
        # Only "not_found" is possible here — audit the cross-tenant/missing probe.
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
        raise _not_found() from exc

    await write_audit(
        session,
        actor_type="user",
        actor_id=actor_id,
        action="space_deleted",
        entity_type="space",
        entity_id=space_id,
        metadata={
            "company_id": str(company_id),
            "deleted_space_count": deleted_space_count,
            "deleted_document_count": deleted_document_count,
        },
    )

    return {
        "deleted": True,
        "space_id": str(space_id),
        "deleted_space_count": deleted_space_count,
        "deleted_document_count": deleted_document_count,
    }
