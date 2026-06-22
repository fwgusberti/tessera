"""Space member management endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel

from tessera_api.adapters.database import get_db
from tessera_api.adapters.repo import (
    SqlAuditRepository,
    SqlSpaceMembershipRepository,
    SqlUserRepository,
)
from tessera_api.auth.oidc import require_company_context, require_user
from tessera_api.routers.spaces import validate_space_for_company
from tessera_core.domain.entities import SpaceRole
from tessera_core.permissions.access import can_read_space_document
from tessera_core.services.membership import MembershipService

router = APIRouter(tags=["members"])


class InviteMemberRequest(BaseModel):
    user_id: UUID
    role: SpaceRole


class ChangeRoleRequest(BaseModel):
    role: SpaceRole


@router.post("/spaces/{space_id}/members", status_code=status.HTTP_201_CREATED)
async def invite_member(space_id: UUID, body: InviteMemberRequest, request: Request) -> dict:
    user_info = await require_user(request)
    actor_id = UUID(user_info.get("id") or user_info.get("sub"))

    async with get_db() as session:
        user_repo = SqlUserRepository(session)
        actor = await user_repo.get_by_id(actor_id)
        if actor is None:
            raise HTTPException(status_code=401, detail="User not found")

        membership_repo = SqlSpaceMembershipRepository(session)
        audit_repo = SqlAuditRepository(session)
        svc = MembershipService(repo=membership_repo, audit=audit_repo)

        try:
            membership = await svc.invite(actor, space_id, body.user_id, body.role)
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from e
        except ValueError as e:
            msg = str(e)
            if "already a member" in msg:
                raise HTTPException(status_code=400, detail=msg) from e
            raise HTTPException(status_code=404, detail=msg) from e

    return {"membership": membership.model_dump()}


@router.get("/spaces/{space_id}/members")
async def list_members(space_id: UUID, request: Request) -> dict:
    user_info, company_id = await require_company_context(request)

    await validate_space_for_company(space_id, company_id)

    actor_id = UUID(user_info.get("id") or user_info.get("sub"))

    async with get_db() as session:
        user_repo = SqlUserRepository(session)
        actor = await user_repo.get_by_id(actor_id)
        if actor is None:
            raise HTTPException(status_code=401, detail="User not found")

        membership_repo = SqlSpaceMembershipRepository(session)
        memberships = await membership_repo.list_by_space(space_id)

        if not can_read_space_document(actor, space_id, memberships):
            raise HTTPException(status_code=403, detail="Not a member of this space")

    return {"members": [m.model_dump() for m in memberships]}


@router.get("/spaces/{space_id}/members/me")
async def get_my_membership(space_id: UUID, request: Request) -> dict:
    user_info = await require_user(request)
    actor_id = UUID(user_info.get("id") or user_info.get("sub"))

    async with get_db() as session:
        user_repo = SqlUserRepository(session)
        actor = await user_repo.get_by_id(actor_id)
        if actor is None:
            raise HTTPException(status_code=401, detail="User not found")

        membership_repo = SqlSpaceMembershipRepository(session)
        membership = await membership_repo.get(space_id, actor_id)

    if membership is None:
        raise HTTPException(status_code=404, detail="Not a member of this space")

    return {"membership": membership.model_dump()}


@router.put("/spaces/{space_id}/members/{user_id}")
async def change_member_role(
    space_id: UUID, user_id: UUID, body: ChangeRoleRequest, request: Request
) -> dict:
    user_info = await require_user(request)
    actor_id = UUID(user_info.get("id") or user_info.get("sub"))

    async with get_db() as session:
        user_repo = SqlUserRepository(session)
        actor = await user_repo.get_by_id(actor_id)
        if actor is None:
            raise HTTPException(status_code=401, detail="User not found")

        membership_repo = SqlSpaceMembershipRepository(session)
        audit_repo = SqlAuditRepository(session)
        svc = MembershipService(repo=membership_repo, audit=audit_repo)

        try:
            membership = await svc.change_role(actor, space_id, user_id, body.role)
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from e
        except ValueError as e:
            msg = str(e)
            if "last admin" in msg:
                raise HTTPException(status_code=409, detail=msg) from e
            raise HTTPException(status_code=404, detail=msg) from e

    return {"membership": membership.model_dump()}


@router.delete("/spaces/{space_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(space_id: UUID, user_id: UUID, request: Request) -> Response:
    user_info = await require_user(request)
    actor_id = UUID(user_info.get("id") or user_info.get("sub"))

    async with get_db() as session:
        user_repo = SqlUserRepository(session)
        actor = await user_repo.get_by_id(actor_id)
        if actor is None:
            raise HTTPException(status_code=401, detail="User not found")

        membership_repo = SqlSpaceMembershipRepository(session)
        audit_repo = SqlAuditRepository(session)
        svc = MembershipService(repo=membership_repo, audit=audit_repo)

        try:
            await svc.remove(actor, space_id, user_id)
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from e
        except ValueError as e:
            msg = str(e)
            if "last admin" in msg:
                raise HTTPException(status_code=409, detail=msg) from e
            raise HTTPException(status_code=404, detail=msg) from e

    return Response(status_code=204)
