"""Company management endpoints."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError

from tessera_api.adapters.audit import write_audit
from tessera_api.adapters.database import SessionDep
from tessera_api.adapters.repo import (
    SqlCompanyRepository,
    SqlDomainPolicyRepository,
    SqlInvitationRepository,
    SqlJoinRequestRepository,
    SqlOnboardingRepository,
    SqlSpaceMembershipRepository,
    SqlSpaceRepository,
    SqlUserRepository,
)
from tessera_api.auth.oidc import CompanyAdminContext, CompanyMemberContext, CurrentUser
from tessera_api.routers.invitations import INVITATION_TTL_DAYS, send_invitation_email
from tessera_core.domain.entities import (
    Company,
    CompanyMembership,
    CompanyRole,
    DomainJoinPolicy,
    DomainPolicy,
    Invitation,
    InvitationStatus,
    JoinRequest,
    JoinRequestStatus,
    OnboardingProgress,
    extract_domain,
    is_public_email_domain,
)
from tessera_core.services.member_access import MemberAccessService

router = APIRouter(tags=["companies"])

VALID_TEAM_SIZES = {"1-10", "11-50", "51-200", "201-1000", "1000+"}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CreateCompanyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    industry: str | None = Field(default=None, max_length=100)
    team_size: str | None = None


class JoinRequest_(BaseModel):
    method: Literal["invitation", "domain_match"]
    invitation_id: UUID | None = None


class CreateDomainPolicyRequest(BaseModel):
    domain: str = Field(min_length=1, max_length=255)
    policy: Literal["auto_join", "request_approval"]


class CompanyMeEntry(BaseModel):
    id: str
    name: str
    role: Literal["admin", "member"]


class CompanyMeResponse(BaseModel):
    companies: list[CompanyMeEntry]


class InviteCompanyMemberRequest(BaseModel):
    email: EmailStr
    role: CompanyRole = CompanyRole.MEMBER


class AddCompanyMemberRequest(BaseModel):
    user_id: UUID
    role: CompanyRole = CompanyRole.MEMBER


class CompanyProfileResponse(BaseModel):
    id: str
    name: str
    industry: str | None
    team_size: str | None
    created_at: datetime | None
    role: Literal["admin", "member"]


class UpdateCompanyRequest(BaseModel):
    # Name limits are enforced in the handler so violations surface as the
    # contract's `invalid_name` code rather than a bare pydantic 422.
    name: str
    industry: str | None = Field(default=None, max_length=100)
    team_size: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _email_domain(email: str) -> str:
    return email.split("@")[-1].lower()


async def _require_company_admin(
    user_id: UUID, company_id: UUID, company_repo: SqlCompanyRepository
) -> None:
    membership = await company_repo.get_membership(user_id, company_id)
    if membership is None or membership.role != CompanyRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "forbidden", "message": "Company admin required"}},
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/companies/me")
async def get_my_companies(user_info: CurrentUser, session: SessionDep) -> CompanyMeResponse:
    user_id = UUID(user_info["sub"])

    company_repo = SqlCompanyRepository(session)
    memberships = await company_repo.list_memberships_for_user(user_id)

    entries = []
    for m in memberships:
        company = await company_repo.get_by_id(m.company_id)
        if company is None:
            continue
        entries.append(
            CompanyMeEntry(
                id=str(company.id),
                name=company.name,
                role=m.role.value,
            )
        )

    entries.sort(key=lambda e: e.name)

    return CompanyMeResponse(companies=entries)


@router.get("/companies/current")
async def get_current_company(
    ctx: CompanyMemberContext, session: SessionDep
) -> CompanyProfileResponse:
    """Read the active company's profile (any member).

    The company id derives solely from the authenticated ``CompanyMemberContext``
    (JWT ``company_id`` claim) — never from client input (Principle VI, FR-009).
    ``role`` is the caller's own membership role so the client can decide whether
    to offer edit controls; the server remains the enforcement point.
    """
    _user_info, company_id, membership = ctx

    company_repo = SqlCompanyRepository(session)
    company = await company_repo.get_by_id(company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "not_found", "message": "Company not found"}},
        )

    return CompanyProfileResponse(
        id=str(company.id),
        name=company.name,
        industry=company.industry,
        team_size=company.team_size,
        created_at=company.created_at,
        role=membership.role.value,
    )


@router.patch("/companies/current")
async def update_current_company(
    body: UpdateCompanyRequest, ctx: CompanyAdminContext, session: SessionDep
) -> CompanyProfileResponse:
    """Update the active company's profile (admin only) — validation mirrors
    ``POST /v1/companies``; every successful save writes a ``company.updated``
    audit record with a changed-fields map (FR-010, SC-004).

    The company id derives solely from ``CompanyAdminContext`` and the update is
    scoped ``WHERE id = :company_id`` — cross-tenant writes are inexpressible
    (Principle VI). Concurrency is last-write-wins per the spec assumption.
    """
    user_info, company_id, membership = ctx
    admin_id = UUID(user_info["sub"])

    name = body.name.strip()
    if not name or len(name) > 255:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "invalid_name",
                    "message": "Company name must be 1-255 characters and not blank",
                }
            },
        )

    if body.team_size is not None and body.team_size not in VALID_TEAM_SIZES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "invalid_team_size",
                    "message": f"team_size must be one of {VALID_TEAM_SIZES}",
                }
            },
        )

    company_repo = SqlCompanyRepository(session)
    current = await company_repo.get_by_id(company_id)
    if current is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "not_found", "message": "Company not found"}},
        )

    updated = await company_repo.update_details(
        company_id, name=name, industry=body.industry, team_size=body.team_size
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "not_found", "message": "Company not found"}},
        )

    changed = {
        field: {"from": old_value, "to": new_value}
        for field, old_value, new_value in (
            ("name", current.name, updated.name),
            ("industry", current.industry, updated.industry),
            ("team_size", current.team_size, updated.team_size),
        )
        if old_value != new_value
    }

    await write_audit(
        session,
        actor_type="user",
        actor_id=admin_id,
        action="company.updated",
        entity_type="company",
        entity_id=company_id,
        metadata={"company_id": str(company_id), "changed": changed},
    )

    return CompanyProfileResponse(
        id=str(updated.id),
        name=updated.name,
        industry=updated.industry,
        team_size=updated.team_size,
        created_at=updated.created_at,
        role=membership.role.value,
    )


@router.get("/companies/members")
async def list_company_members(ctx: CompanyAdminContext, session: SessionDep) -> dict:
    """List the members of the caller's active company (admin only).

    The company is derived solely from the authenticated ``CompanyAdminContext``
    (JWT claim / active-company session) — never from client input (Principle VI).
    """
    _user_info, company_id, _membership = ctx

    company_repo = SqlCompanyRepository(session)
    members = await company_repo.list_members(company_id)

    return {
        "members": [
            {
                "user_id": str(m.user_id),
                "display_name": m.display_name,
                "email": m.email,
                "role": m.role.value,
            }
            for m in members
        ]
    }


@router.get("/companies/members/{user_id}/space-access")
async def get_member_space_access(
    user_id: UUID, ctx: CompanyAdminContext, session: SessionDep
) -> dict:
    """Member-centric space access view: every company space with the target
    member's direct/effective role (feature 058, FR-001).

    ``company_id`` derives solely from ``CompanyAdminContext`` (Principle VI).
    A ``user_id`` with no membership in the active company returns a generic 404
    indistinguishable from absent — cross-company probes additionally leave a
    ``cross_tenant_denied`` audit record (053/054 convention).
    """
    user_info, company_id, _membership = ctx
    admin_id = UUID(user_info["sub"])

    company_repo = SqlCompanyRepository(session)
    user_repo = SqlUserRepository(session)

    target_membership = await company_repo.get_membership(user_id, company_id)
    target = await user_repo.get_by_id(user_id)
    if target_membership is None or target is None:
        if target is not None:
            # The user exists but belongs to another company — audit the probe.
            await write_audit(
                session,
                actor_type="user",
                actor_id=admin_id,
                action="cross_tenant_denied",
                entity_type="user",
                entity_id=user_id,
                metadata={"company_id": str(company_id)},
            )
            await session.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "not_found", "message": "Not found"}},
        )

    svc = MemberAccessService(SqlSpaceRepository(session), SqlSpaceMembershipRepository(session))
    rows = await svc.space_access_for_member(user_id, company_id)

    return {
        "member": {
            "user_id": str(target.id),
            "display_name": target.display_name,
            "email": target.email,
        },
        "spaces": [
            {
                "id": str(r.space.id),
                "name": r.space.name,
                "slug": r.space.slug,
                "parent_space_id": (
                    str(r.space.parent_space_id) if r.space.parent_space_id else None
                ),
                "direct_role": r.direct_role.value if r.direct_role else None,
                "effective_role": r.effective_role.value if r.effective_role else None,
                "is_direct": r.is_direct,
            }
            for r in rows
        ],
    }


@router.post("/companies/invitations", status_code=status.HTTP_201_CREATED)
async def invite_company_member(
    body: InviteCompanyMemberRequest, ctx: CompanyAdminContext, session: SessionDep
) -> dict:
    """Invite a person by email to the caller's active company with a chosen role.

    The company is derived solely from ``CompanyAdminContext`` — never from client
    input (Principle VI). The chosen role is persisted on the invitation so it is
    granted when the invitee accepts (FR-004, FR-011).
    """
    user_info, company_id, _membership = ctx
    admin_id = UUID(user_info["sub"])
    email = body.email.lower()

    company_repo = SqlCompanyRepository(session)
    user_repo = SqlUserRepository(session)
    inv_repo = SqlInvitationRepository(session)

    # Guard: already a member of this company (FR-007).
    target_user = await user_repo.get_by_email(email)
    if target_user:
        existing_membership = await company_repo.get_membership(target_user.id, company_id)
        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "already_member",
                        "message": "Already a member of this company",
                    }
                },
            )

    # Guard: an outstanding invitation already exists for this company (FR-008).
    pending = await inv_repo.get_pending_for_email(email)
    if any(p.company_id == company_id for p in pending):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {"code": "already_invited", "message": "An invitation is already pending"}
            },
        )

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    try:
        created = await inv_repo.create(
            Invitation(
                company_id=company_id,
                invited_by_user_id=admin_id,
                email=email,
                token_hash=token_hash,
                status=InvitationStatus.PENDING,
                role=body.role,
                expires_at=datetime.now(UTC) + timedelta(days=INVITATION_TTL_DAYS),
            )
        )
    except IntegrityError:
        # Concurrent invite tripped the pending-uniqueness index (FR-008 race).
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {"code": "already_invited", "message": "An invitation is already pending"}
            },
        ) from None

    # Persist the invitation regardless of delivery outcome, so a send failure
    # still leaves the pending record behind (contract: row created, 502 surfaced).
    await session.commit()

    company = await company_repo.get_by_id(company_id)
    caller = await user_repo.get_by_id(admin_id)
    invited_by_name = caller.display_name if caller else user_info.get("email", "")

    try:
        await send_invitation_email(
            to=email,
            company_name=company.name if company else "",
            invited_by=invited_by_name,
            token=token,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": {
                    "code": "send_failed",
                    "message": "The invitation could not be delivered",
                }
            },
        ) from None

    await write_audit(
        session,
        actor_type="user",
        actor_id=admin_id,
        action="invitation.sent",
        entity_type="invitation",
        entity_id=created.id,
        metadata={"email": email, "company_id": str(company_id)},
    )

    return {"status": "sent", "email": email, "role": body.role.value}


@router.get("/companies/addable-users")
async def search_addable_users(
    ctx: CompanyAdminContext,
    session: SessionDep,
    q: str = Query(min_length=2),
) -> dict:
    """Type-ahead search of registered users not already in the active company.

    Scoped to the ``CompanyAdminContext`` company_id; returns identity fields only
    and requires a minimum query length so it cannot enumerate the directory (US2,
    US4). ``company_id`` is never sourced from client input.
    """
    _user_info, company_id, _membership = ctx

    company_repo = SqlCompanyRepository(session)
    matches = await company_repo.search_addable_users(company_id, q)

    return {
        "users": [
            {"user_id": str(m.user_id), "display_name": m.display_name, "email": m.email}
            for m in matches
        ]
    }


@router.post("/companies/members", status_code=status.HTTP_201_CREATED)
async def add_company_member(
    body: AddCompanyMemberRequest, ctx: CompanyAdminContext, session: SessionDep
) -> dict:
    """Directly add an already-registered user to the active company (US2, FR-003).

    The membership is created immediately with the admin-chosen role; ``company_id``
    comes solely from ``CompanyAdminContext`` (Principle VI, FR-010).
    """
    user_info, company_id, _membership = ctx
    admin_id = UUID(user_info["sub"])

    company_repo = SqlCompanyRepository(session)
    user_repo = SqlUserRepository(session)

    target = await user_repo.get_by_id(body.user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "no_such_user", "message": "No such user"}},
        )

    existing = await company_repo.get_membership(body.user_id, company_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {"code": "already_member", "message": "Already a member of this company"}
            },
        )

    try:
        membership = await company_repo.add_membership(
            CompanyMembership(user_id=body.user_id, company_id=company_id, role=body.role)
        )
    except IntegrityError:
        # Concurrent add tripped uq_company_membership (FR-007 race).
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {"code": "already_member", "message": "Already a member of this company"}
            },
        ) from None

    await write_audit(
        session,
        actor_type="user",
        actor_id=admin_id,
        action="company.member_added",
        entity_type="company_membership",
        entity_id=membership.id,
        metadata={"company_id": str(company_id), "user_id": str(body.user_id)},
    )

    # Persist the target's onboarding completion so stored state stays truthful
    # (mirrors the approve-join path). Membership already satisfies both gates, but
    # marking the OnboardingProgress complete + emitting an audit keeps the record
    # accurate (FR-003). Idempotent: re-adding refreshes without error.
    ob_repo = SqlOnboardingRepository(session)
    if await ob_repo.get_by_user_id(body.user_id) is None:
        await ob_repo.create(OnboardingProgress(user_id=body.user_id))
    await ob_repo.advance_step(
        body.user_id, "complete", company_join_method="added", company_id=company_id
    )
    await ob_repo.complete(body.user_id)

    await write_audit(
        session,
        actor_type="user",
        actor_id=admin_id,
        action="onboarding.completed",
        entity_type="user",
        entity_id=body.user_id,
    )

    return {
        "member": {
            "user_id": str(target.id),
            "display_name": target.display_name,
            "email": target.email,
            "role": membership.role.value,
        }
    }


@router.post("/companies", status_code=status.HTTP_201_CREATED)
async def create_company(
    body: CreateCompanyRequest, request: Request, user_info: CurrentUser, session: SessionDep
) -> dict:
    user_id = UUID(user_info["sub"])

    if body.team_size is not None and body.team_size not in VALID_TEAM_SIZES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "invalid_team_size",
                    "message": f"team_size must be one of {VALID_TEAM_SIZES}",
                }
            },
        )

    company_repo = SqlCompanyRepository(session)
    ob_repo = SqlOnboardingRepository(session)

    company = await company_repo.create(
        Company(
            name=body.name,
            industry=body.industry,
            team_size=body.team_size,
            admin_user_id=user_id,
        )
    )
    membership = await company_repo.add_membership(
        CompanyMembership(user_id=user_id, company_id=company.id, role=CompanyRole.ADMIN)
    )

    await ob_repo.advance_step(
        user_id, "invite", company_join_method="created", company_id=company.id
    )

    await write_audit(
        session,
        actor_type="user",
        actor_id=user_id,
        action="company.created",
        entity_type="company",
        entity_id=company.id,
    )

    # Domain auto-association side effect (US3): make the company matchable by the
    # founder's email domain when it is a real (non-public) work domain that no
    # other company has already claimed. Marking it verified lights up the existing
    # suggestions/join code paths; the admin-approval gate is the safety net. This
    # is best-effort — company creation must never fail because of it.
    email = user_info.get("email", "")
    founder_domain = extract_domain(email)
    if founder_domain and not is_public_email_domain(founder_domain):
        domain_repo = SqlDomainPolicyRepository(session)
        if await domain_repo.get_by_domain(founder_domain) is None:
            try:
                async with session.begin_nested():
                    await domain_repo.create(
                        DomainJoinPolicy(
                            company_id=company.id,
                            domain=founder_domain,
                            policy=DomainPolicy.REQUEST_APPROVAL,
                            verified=True,
                        )
                    )
                    await write_audit(
                        session,
                        actor_type="user",
                        actor_id=user_id,
                        action="company.domain_auto_associated",
                        entity_type="company",
                        entity_id=company.id,
                        metadata={"company_id": str(company.id), "domain": founder_domain},
                    )
            except IntegrityError:
                # A concurrent creation claimed this domain first (unique index).
                # The savepoint rolls back only the policy write; the new company
                # is simply not matchable by that domain and creation proceeds.
                pass

    from tessera_api.auth.jwt_auth import create_access_token

    token = create_access_token(
        user_id,
        user_info.get("email", ""),
        user_info.get("is_admin", False),
        company_id=company.id,
    )
    request.session.setdefault("user", {})["active_company_id"] = str(company.id)

    return {
        "id": str(company.id),
        "name": company.name,
        "industry": company.industry,
        "team_size": company.team_size,
        "role": membership.role.value,
        "created_at": company.created_at.isoformat() if company.created_at else None,
        "token": token,
    }


@router.get("/companies/suggestions")
async def get_suggestions(user_info: CurrentUser, session: SessionDep) -> dict:
    email = user_info.get("email", "")
    domain = _email_domain(email) if "@" in email else ""

    invitations_out = []
    domain_matches_out = []

    inv_repo = SqlInvitationRepository(session)
    company_repo = SqlCompanyRepository(session)
    domain_repo = SqlDomainPolicyRepository(session)
    user_repo = SqlUserRepository(session)

    # Pending invitations for this email
    pending = await inv_repo.get_pending_for_email(email)
    for inv in pending:
        from datetime import UTC, datetime

        if inv.expires_at < datetime.now(UTC):
            continue
        company = await company_repo.get_by_id(inv.company_id)
        if company is None:
            continue
        invited_by_name = ""
        if inv.invited_by_user_id:
            inviter = await user_repo.get_by_id(inv.invited_by_user_id)
            if inviter:
                invited_by_name = inviter.display_name
        invitations_out.append(
            {
                "id": str(inv.id),
                "company_id": str(inv.company_id),
                "company_name": company.name,
                "invited_by": invited_by_name,
                "expires_at": inv.expires_at.isoformat(),
            }
        )

    # Verified domain policies for the caller's email domain
    if domain:
        policy = await domain_repo.get_by_domain(domain)
        if policy and policy.verified:
            company = await company_repo.get_by_id(policy.company_id)
            if company:
                domain_matches_out.append(
                    {
                        "company_id": str(company.id),
                        "company_name": company.name,
                        "domain": policy.domain,
                        "policy": policy.policy.value,
                    }
                )

    return {"invitations": invitations_out, "domain_matches": domain_matches_out}


@router.post("/companies/{company_id}/join")
async def join_company(
    company_id: UUID, body: JoinRequest_, user_info: CurrentUser, session: SessionDep
) -> dict:
    user_id = UUID(user_info["sub"])
    email = user_info.get("email", "")

    company_repo = SqlCompanyRepository(session)
    ob_repo = SqlOnboardingRepository(session)

    company = await company_repo.get_by_id(company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    # Check already a member
    existing_membership = await company_repo.get_membership(user_id, company_id)
    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "already_member",
                    "message": "Already a member of this company",
                }
            },
        )

    if body.method == "invitation":
        if body.invitation_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": {
                        "code": "missing_invitation_id",
                        "message": "invitation_id is required for method=invitation",
                    }
                },
            )
        inv_repo = SqlInvitationRepository(session)
        invitation = await inv_repo.get_by_id(body.invitation_id)

        if invitation is None or invitation.status != InvitationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "invitation_invalid",
                        "message": "Invitation not found, expired, or already used",
                    }
                },
            )
        from datetime import UTC, datetime

        if invitation.expires_at < datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {"code": "invitation_expired", "message": "Invitation has expired"}
                },
            )

        await inv_repo.update_status(invitation.id, InvitationStatus.ACCEPTED)
        # Grant the role the admin chose at invite time (FR-011). Legacy invitations
        # default to member via the column default, so behavior is unchanged for them.
        await company_repo.add_membership(
            CompanyMembership(user_id=user_id, company_id=company_id, role=invitation.role)
        )
        await ob_repo.advance_step(user_id, "complete", company_join_method="joined")

        await write_audit(
            session,
            actor_type="user",
            actor_id=user_id,
            action="company.joined_via_invitation",
            entity_type="company",
            entity_id=company_id,
        )

        return {
            "status": "joined",
            "company_id": str(company_id),
            "company_name": company.name,
            "role": invitation.role.value,
        }

    elif body.method == "domain_match":
        domain = _email_domain(email) if "@" in email else ""
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email domain required"
            )

        domain_repo = SqlDomainPolicyRepository(session)
        policy = await domain_repo.get_by_domain(domain)
        if policy is None or policy.company_id != company_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "no_domain_policy",
                        "message": "No verified domain policy found",
                    }
                },
            )
        if not policy.verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "domain_not_verified",
                        "message": "Domain not yet verified",
                    }
                },
            )

        if policy.policy == DomainPolicy.AUTO_JOIN:
            await company_repo.add_membership(
                CompanyMembership(user_id=user_id, company_id=company_id, role=CompanyRole.MEMBER)
            )
            await ob_repo.advance_step(user_id, "complete", company_join_method="joined")

            await write_audit(
                session,
                actor_type="user",
                actor_id=user_id,
                action="company.joined_via_domain_auto",
                entity_type="company",
                entity_id=company_id,
            )

            return {
                "status": "joined",
                "company_id": str(company_id),
                "company_name": company.name,
                "role": "member",
            }

        else:  # request_approval
            jr_repo = SqlJoinRequestRepository(session)
            existing_request = await jr_repo.get_by_user_and_company(user_id, company_id)
            if existing_request and existing_request.status == JoinRequestStatus.PENDING:
                return {
                    "status": "pending",
                    "company_id": str(company_id),
                    "company_name": company.name,
                }

            await jr_repo.create(JoinRequest(user_id=user_id, company_id=company_id))

            # Notify admin
            try:
                from tessera_api.adapters.email import FastMailEmailAdapter
                from tessera_api.config import get_settings

                settings = get_settings()
                admin_user = await SqlUserRepository(session).get_by_id(company.admin_user_id)
                if admin_user:
                    user_model = await SqlUserRepository(session).get_by_id(user_id)
                    user_name = user_model.display_name if user_model else email
                    adapter = FastMailEmailAdapter()
                    await adapter.send_join_request_notification(
                        to=admin_user.email,
                        requester_name=user_name,
                        requester_email=email,
                        company_name=company.name,
                        review_url=f"{settings.frontend_url}/companies/{company_id}/join-requests",
                    )
            except Exception:
                pass  # Email failure must not block the join request

            await write_audit(
                session,
                actor_type="user",
                actor_id=user_id,
                action="company.join_request_submitted",
                entity_type="company",
                entity_id=company_id,
            )

            return {
                "status": "pending",
                "company_id": str(company_id),
                "company_name": company.name,
            }

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown join method"
    )


@router.get("/companies/{company_id}/join-status")
async def get_join_status(company_id: UUID, user_info: CurrentUser, session: SessionDep) -> dict:
    user_id = UUID(user_info["sub"])

    jr_repo = SqlJoinRequestRepository(session)
    company_repo = SqlCompanyRepository(session)

    company = await company_repo.get_by_id(company_id)
    company_name = company.name if company else ""

    join_req = await jr_repo.get_by_user_and_company(user_id, company_id)
    if join_req is None:
        # Check if already a member
        membership = await company_repo.get_membership(user_id, company_id)
        if membership:
            return {"status": "approved", "company_name": company_name}
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No join request found")

    if join_req.status == JoinRequestStatus.PENDING:
        return {
            "status": "pending",
            "company_name": company_name,
            "requested_at": (join_req.requested_at.isoformat() if join_req.requested_at else None),
        }
    elif join_req.status == JoinRequestStatus.APPROVED:
        return {
            "status": "approved",
            "company_name": company_name,
            "approved_at": join_req.decided_at.isoformat() if join_req.decided_at else None,
        }
    else:
        return {"status": "denied"}


@router.delete("/companies/{company_id}/join-request", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_join_request(
    company_id: UUID, user_info: CurrentUser, session: SessionDep
) -> Response:
    user_id = UUID(user_info["sub"])

    jr_repo = SqlJoinRequestRepository(session)
    join_req = await jr_repo.get_by_user_and_company(user_id, company_id)
    if join_req and join_req.status == JoinRequestStatus.PENDING:
        await jr_repo.cancel(join_req.id)
        await write_audit(
            session,
            actor_type="user",
            actor_id=user_id,
            action="company.join_request_cancelled",
            entity_type="company",
            entity_id=company_id,
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/companies/{company_id}/join-requests")
async def list_join_requests(company_id: UUID, user_info: CurrentUser, session: SessionDep) -> dict:
    user_id = UUID(user_info["sub"])

    company_repo = SqlCompanyRepository(session)
    await _require_company_admin(user_id, company_id, company_repo)

    jr_repo = SqlJoinRequestRepository(session)
    requests = await jr_repo.list_pending_for_company(company_id)
    user_repo = SqlUserRepository(session)

    items = []
    for jr in requests:
        requester = await user_repo.get_by_id(jr.user_id)
        items.append(
            {
                "id": str(jr.id),
                "user_id": str(jr.user_id),
                "user_name": requester.display_name if requester else "",
                "user_email": requester.email if requester else "",
                "requested_at": jr.requested_at.isoformat() if jr.requested_at else None,
            }
        )

    return {"join_requests": items}


@router.post("/companies/{company_id}/join-requests/{request_id}/approve")
async def approve_join_request(
    company_id: UUID, request_id: UUID, user_info: CurrentUser, session: SessionDep
) -> dict:
    admin_id = UUID(user_info["sub"])

    company_repo = SqlCompanyRepository(session)
    await _require_company_admin(admin_id, company_id, company_repo)

    company = await company_repo.get_by_id(company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    jr_repo = SqlJoinRequestRepository(session)
    join_req = await jr_repo.get_by_id(request_id)
    if join_req is None or join_req.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Join request not found")
    if join_req.status != JoinRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {"code": "already_decided", "message": "Join request already decided"}
            },
        )

    await jr_repo.decide(request_id, JoinRequestStatus.APPROVED, admin_id)
    await company_repo.add_membership(
        CompanyMembership(user_id=join_req.user_id, company_id=company_id, role=CompanyRole.MEMBER)
    )

    ob_repo = SqlOnboardingRepository(session)
    await ob_repo.advance_step(join_req.user_id, "complete", company_join_method="joined")

    # Notify the requester
    try:
        from tessera_api.adapters.email import FastMailEmailAdapter
        from tessera_api.config import get_settings

        settings = get_settings()
        user_repo = SqlUserRepository(session)
        requester = await user_repo.get_by_id(join_req.user_id)
        if requester:
            adapter = FastMailEmailAdapter()
            await adapter.send_join_request_decision(
                to=requester.email,
                company_name=company.name,
                approved=True,
                dashboard_url=f"{settings.frontend_url}/",
            )
    except Exception:
        pass

    await write_audit(
        session,
        actor_type="user",
        actor_id=admin_id,
        action="company.join_request_approved",
        entity_type="company",
        entity_id=company_id,
        metadata={"requester_id": str(join_req.user_id)},
    )

    return {"status": "approved", "request_id": str(request_id)}


@router.post("/companies/{company_id}/join-requests/{request_id}/deny")
async def deny_join_request(
    company_id: UUID, request_id: UUID, user_info: CurrentUser, session: SessionDep
) -> dict:
    admin_id = UUID(user_info["sub"])

    company_repo = SqlCompanyRepository(session)
    await _require_company_admin(admin_id, company_id, company_repo)

    company = await company_repo.get_by_id(company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    jr_repo = SqlJoinRequestRepository(session)
    join_req = await jr_repo.get_by_id(request_id)
    if join_req is None or join_req.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Join request not found")
    if join_req.status != JoinRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {"code": "already_decided", "message": "Join request already decided"}
            },
        )

    await jr_repo.decide(request_id, JoinRequestStatus.DENIED, admin_id)

    # Notify the requester
    try:
        from tessera_api.adapters.email import FastMailEmailAdapter
        from tessera_api.config import get_settings

        settings = get_settings()
        user_repo = SqlUserRepository(session)
        requester = await user_repo.get_by_id(join_req.user_id)
        if requester:
            adapter = FastMailEmailAdapter()
            await adapter.send_join_request_decision(
                to=requester.email,
                company_name=company.name,
                approved=False,
                dashboard_url=f"{settings.frontend_url}/",
            )
    except Exception:
        pass

    await write_audit(
        session,
        actor_type="user",
        actor_id=admin_id,
        action="company.join_request_denied",
        entity_type="company",
        entity_id=company_id,
        metadata={"requester_id": str(join_req.user_id)},
    )

    return {"status": "denied", "request_id": str(request_id)}


@router.post("/companies/{company_id}/domain-policies", status_code=status.HTTP_201_CREATED)
async def create_domain_policy(
    company_id: UUID,
    body: CreateDomainPolicyRequest,
    user_info: CurrentUser,
    session: SessionDep,
) -> dict:
    user_id = UUID(user_info["sub"])

    domain = body.domain.lower().lstrip("@")

    # Reject public / free email-provider domains outright (FR-010, defense in
    # depth): a company must never claim gmail.com/outlook.com/etc. Guard runs
    # before any DB write or verification email.
    if is_public_email_domain(domain):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "public_domain_not_allowed",
                    "message": f"{domain} is a public email provider and cannot be claimed",
                }
            },
        )

    company_repo = SqlCompanyRepository(session)
    await _require_company_admin(user_id, company_id, company_repo)

    company = await company_repo.get_by_id(company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    domain_repo = SqlDomainPolicyRepository(session)
    existing = await domain_repo.get_by_domain(domain)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "domain_already_claimed",
                    "message": f"Domain {domain} is already claimed",
                }
            },
        )

    policy = await domain_repo.create(
        DomainJoinPolicy(
            company_id=company_id,
            domain=domain,
            policy=DomainPolicy(body.policy),
        )
    )

    # Send verification email to verify@<domain>
    try:
        from itsdangerous import URLSafeTimedSerializer

        from tessera_api.adapters.email import FastMailEmailAdapter
        from tessera_api.config import get_settings

        settings = get_settings()
        s = URLSafeTimedSerializer(settings.secret_key)
        token = s.dumps({"domain": domain, "policy_id": str(policy.id)}, salt="domain-verify")
        verify_url = f"{settings.frontend_url}/api/domain-verify/{token}"

        adapter = FastMailEmailAdapter()
        await adapter.send_verification(
            to=f"verify@{domain}",
            domain=domain,
            verify_url=verify_url,
        )
    except Exception:
        pass  # Email failure must not block policy creation

    await write_audit(
        session,
        actor_type="user",
        actor_id=user_id,
        action="company.domain_policy_created",
        entity_type="company",
        entity_id=company_id,
        metadata={"domain": domain},
    )

    return {
        "id": str(policy.id),
        "domain": policy.domain,
        "policy": policy.policy.value,
        "verified": policy.verified,
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
    }


@router.get("/domain-verify/{token}")
async def verify_domain(token: str, session: SessionDep) -> Response:
    """Public endpoint — no auth required. Validates a domain verification token."""
    from fastapi.responses import RedirectResponse
    from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

    from tessera_api.config import get_settings

    settings = get_settings()
    s = URLSafeTimedSerializer(settings.secret_key)

    try:
        data = s.loads(token, salt="domain-verify", max_age=86400)  # 24 hours
    except SignatureExpired:
        return RedirectResponse(url=f"{settings.frontend_url}/settings/domain?error=expired")
    except BadSignature:
        return RedirectResponse(url=f"{settings.frontend_url}/settings/domain?error=invalid")

    domain = data.get("domain")
    policy_id = data.get("policy_id")

    if not domain or not policy_id:
        return RedirectResponse(url=f"{settings.frontend_url}/settings/domain?error=invalid")

    domain_repo = SqlDomainPolicyRepository(session)
    policy = await domain_repo.get_by_id(UUID(policy_id))
    if policy is None:
        return RedirectResponse(url=f"{settings.frontend_url}/settings/domain?error=invalid")
    if not policy.verified:
        await domain_repo.mark_verified(UUID(policy_id))

    return RedirectResponse(url=f"{settings.frontend_url}/settings/domain?verified=true")


@router.post("/companies/{company_id}/activate")
async def activate_company(
    company_id: UUID, request: Request, user_info: CurrentUser, session: SessionDep
) -> dict:
    """Issue a company-scoped JWT and set active_company_id in session."""
    user_id = UUID(user_info["sub"])

    repo = SqlCompanyRepository(session)
    company = await repo.get_by_id(company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "not_found", "message": "Company not found"}},
        )
    membership = await repo.get_membership(user_id, company_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "forbidden", "message": "Not a member of this company"}},
        )

    from tessera_api.auth.jwt_auth import create_access_token

    token = create_access_token(
        user_id,
        user_info.get("email", ""),
        user_info.get("is_admin", False),
        company_id=company_id,
    )

    if "user" not in request.session:
        request.session["user"] = {
            "sub": user_info["sub"],
            "email": user_info.get("email", ""),
            "is_admin": user_info.get("is_admin", False),
        }
    request.session["user"]["active_company_id"] = str(company_id)

    return {"token": token, "company_id": str(company_id), "company_name": company.name}
