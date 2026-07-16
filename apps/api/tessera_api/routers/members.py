"""Space member management endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.audit import write_audit
from tessera_api.adapters.database import SessionDep
from tessera_api.adapters.repo import (
    SqlAuditRepository,
    SqlCompanyRepository,
    SqlSpaceMembershipRepository,
    SqlSpaceRepository,
    SqlUserRepository,
)
from tessera_api.auth.oidc import (
    CompanyMemberContext,
    is_company_admin,
)
from tessera_api.routers.spaces import validate_space_for_company
from tessera_core.domain.entities import SpaceMembership, SpaceRole
from tessera_core.permissions.access import can_manage_members, can_read_space_document
from tessera_core.services.membership import MembershipService

router = APIRouter(tags=["members"])


def _not_found() -> HTTPException:
    """Generic 404 for cross-company by-ID access — indistinguishable from absent (FR-004)."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": {"code": "not_found", "message": "Not found"}},
    )


async def _require_space_in_company(
    space_id: UUID,
    company_id: UUID,
    actor_id: UUID,
    session: AsyncSession,
) -> None:
    """Verify space belongs to the active company; on miss audit + raise generic 404."""
    space_repo = SqlSpaceRepository(session)
    space = await space_repo.get_by_id_for_company(space_id, company_id)

    if space is None:
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


class InviteMemberRequest(BaseModel):
    user_id: UUID
    role: SpaceRole


class ChangeRoleRequest(BaseModel):
    role: SpaceRole


@router.post("/spaces/{space_id}/members", status_code=status.HTTP_201_CREATED)
async def invite_member(
    space_id: UUID, body: InviteMemberRequest, ctx: CompanyMemberContext, session: SessionDep
) -> dict:
    user_info, company_id, caller_membership = ctx
    company_admin = is_company_admin(caller_membership)
    actor_id = UUID(user_info.get("id") or user_info.get("sub"))
    await _require_space_in_company(space_id, company_id, actor_id, session)

    user_repo = SqlUserRepository(session)
    actor = await user_repo.get_by_id(actor_id)
    if actor is None:
        raise HTTPException(status_code=401, detail="User not found")

    membership_repo = SqlSpaceMembershipRepository(session)
    audit_repo = SqlAuditRepository(session)
    svc = MembershipService(repo=membership_repo, audit=audit_repo)

    try:
        membership = await svc.invite(
            actor, space_id, body.user_id, body.role, is_company_admin=company_admin
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        msg = str(e)
        if "already a member" in msg:
            raise HTTPException(status_code=400, detail=msg) from e
        raise HTTPException(status_code=404, detail=msg) from e

    return {"membership": membership.model_dump()}


@router.get("/spaces/{space_id}/members")
async def list_members(
    space_id: UUID, ctx: CompanyMemberContext, session: SessionDep
) -> dict:
    user_info, company_id, caller_membership = ctx
    company_admin = is_company_admin(caller_membership)

    await validate_space_for_company(space_id, company_id, session)

    actor_id = UUID(user_info.get("id") or user_info.get("sub"))

    user_repo = SqlUserRepository(session)
    actor = await user_repo.get_by_id(actor_id)
    if actor is None:
        raise HTTPException(status_code=401, detail="User not found")

    membership_repo = SqlSpaceMembershipRepository(session)
    listings = await membership_repo.list_by_space_with_identity(space_id, company_id)

    # The permission check needs bare memberships; derive them from the
    # enriched rows instead of issuing a second list_by_space query.
    memberships = [
        SpaceMembership(
            id=row.id,
            space_id=row.space_id,
            user_id=row.user_id,
            role=row.role,
            invited_by_user_id=row.invited_by_user_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in listings
    ]

    if not can_read_space_document(
        actor, space_id, memberships, is_company_admin=company_admin
    ):
        raise HTTPException(status_code=403, detail="Not a member of this space")

    return {
        "members": [
            {
                "id": row.id,
                "space_id": row.space_id,
                "user_id": row.user_id,
                "display_name": row.display_name,
                "email": row.email,
                "role": row.role.value,
                "invited_by_user_id": row.invited_by_user_id,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in listings
        ]
    }


@router.get("/spaces/{space_id}/members/me")
async def get_my_membership(
    space_id: UUID, ctx: CompanyMemberContext, session: SessionDep
) -> dict:
    user_info, company_id, _caller_membership = ctx
    actor_id = UUID(user_info.get("id") or user_info.get("sub"))
    await _require_space_in_company(space_id, company_id, actor_id, session)

    user_repo = SqlUserRepository(session)
    actor = await user_repo.get_by_id(actor_id)
    if actor is None:
        raise HTTPException(status_code=401, detail="User not found")

    membership_repo = SqlSpaceMembershipRepository(session)
    membership = await membership_repo.get(space_id, actor_id)

    if membership is None:
        raise HTTPException(status_code=404, detail="Not a member of this space")

    return {"membership": membership.model_dump()}


@router.get("/spaces/{space_id}/members/search")
async def search_members(
    space_id: UUID, q: str, ctx: CompanyMemberContext, session: SessionDep
) -> dict:
    """Search company members eligible to be added to this space (FR-002, FR-003).

    Authorized per target space (FR-002a): caller must be an admin of space_id
    or a company admin — same rule as POST /spaces/{space_id}/members.
    """
    user_info, company_id, caller_membership = ctx
    company_admin = is_company_admin(caller_membership)
    actor_id = UUID(user_info.get("id") or user_info.get("sub"))
    await _require_space_in_company(space_id, company_id, actor_id, session)

    user_repo = SqlUserRepository(session)
    actor = await user_repo.get_by_id(actor_id)
    if actor is None:
        raise HTTPException(status_code=401, detail="User not found")

    membership_repo = SqlSpaceMembershipRepository(session)
    memberships = await membership_repo.list_by_space(space_id)

    if not can_manage_members(actor, space_id, memberships, is_company_admin=company_admin):
        raise HTTPException(status_code=403, detail="Only space admins can search members")

    company_repo = SqlCompanyRepository(session)
    matches = await company_repo.search_members_for_space(company_id, space_id, q)

    return {
        "members": [
            {"user_id": str(m.user_id), "display_name": m.display_name, "email": m.email}
            for m in matches
        ]
    }


@router.put("/spaces/{space_id}/members/{user_id}")
async def change_member_role(
    space_id: UUID,
    user_id: UUID,
    body: ChangeRoleRequest,
    ctx: CompanyMemberContext,
    session: SessionDep,
) -> dict:
    user_info, company_id, caller_membership = ctx
    company_admin = is_company_admin(caller_membership)
    actor_id = UUID(user_info.get("id") or user_info.get("sub"))
    await _require_space_in_company(space_id, company_id, actor_id, session)

    user_repo = SqlUserRepository(session)
    actor = await user_repo.get_by_id(actor_id)
    if actor is None:
        raise HTTPException(status_code=401, detail="User not found")

    membership_repo = SqlSpaceMembershipRepository(session)
    audit_repo = SqlAuditRepository(session)
    svc = MembershipService(repo=membership_repo, audit=audit_repo)

    try:
        membership = await svc.change_role(
            actor, space_id, user_id, body.role, is_company_admin=company_admin
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        msg = str(e)
        if "last admin" in msg:
            raise HTTPException(status_code=409, detail=msg) from e
        raise HTTPException(status_code=404, detail=msg) from e

    return {"membership": membership.model_dump()}


@router.delete("/spaces/{space_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    space_id: UUID,
    user_id: UUID,
    ctx: CompanyMemberContext,
    session: SessionDep,
) -> Response:
    user_info, company_id, caller_membership = ctx
    company_admin = is_company_admin(caller_membership)
    actor_id = UUID(user_info.get("id") or user_info.get("sub"))
    await _require_space_in_company(space_id, company_id, actor_id, session)

    user_repo = SqlUserRepository(session)
    actor = await user_repo.get_by_id(actor_id)
    if actor is None:
        raise HTTPException(status_code=401, detail="User not found")

    membership_repo = SqlSpaceMembershipRepository(session)
    audit_repo = SqlAuditRepository(session)
    svc = MembershipService(repo=membership_repo, audit=audit_repo)

    try:
        await svc.remove(actor, space_id, user_id, is_company_admin=company_admin)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        msg = str(e)
        if "last admin" in msg:
            raise HTTPException(status_code=409, detail=msg) from e
        raise HTTPException(status_code=404, detail=msg) from e

    return Response(status_code=204)
