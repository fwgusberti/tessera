"""Company management endpoints."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from tessera_api.adapters.audit import write_audit
from tessera_api.adapters.database import get_db
from tessera_api.adapters.repo import (
    SqlCompanyRepository,
    SqlDomainPolicyRepository,
    SqlInvitationRepository,
    SqlJoinRequestRepository,
    SqlOnboardingRepository,
    SqlUserRepository,
)
from tessera_api.auth.oidc import require_user
from tessera_core.domain.entities import (
    Company,
    CompanyMembership,
    CompanyRole,
    DomainJoinPolicy,
    DomainPolicy,
    InvitationStatus,
    JoinRequest,
    JoinRequestStatus,
)

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
async def get_my_companies(request: Request) -> CompanyMeResponse:
    user_info = await require_user(request)
    user_id = UUID(user_info["sub"])

    async with get_db() as session:
        company_repo = SqlCompanyRepository(session)
        memberships = await company_repo.list_memberships_for_user(user_id)

        entries = []
        for m in memberships:
            company = await company_repo.get_by_id(m.company_id)
            if company is None:
                continue
            entries.append(CompanyMeEntry(
                id=str(company.id),
                name=company.name,
                role=m.role.value,
            ))

        entries.sort(key=lambda e: e.name)

    return CompanyMeResponse(companies=entries)


@router.post("/companies", status_code=status.HTTP_201_CREATED)
async def create_company(body: CreateCompanyRequest, request: Request) -> dict:
    user_info = await require_user(request)
    user_id = UUID(user_info["sub"])

    if body.team_size is not None and body.team_size not in VALID_TEAM_SIZES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "invalid_team_size", "message": f"team_size must be one of {VALID_TEAM_SIZES}"}},
        )

    async with get_db() as session:
        company_repo = SqlCompanyRepository(session)
        ob_repo = SqlOnboardingRepository(session)

        company = await company_repo.create(
            Company(name=body.name, industry=body.industry, team_size=body.team_size, admin_user_id=user_id)
        )
        membership = await company_repo.add_membership(
            CompanyMembership(user_id=user_id, company_id=company.id, role=CompanyRole.ADMIN)
        )

        await ob_repo.advance_step(user_id, "invite", company_join_method="created", company_id=company.id)

        await write_audit(
            session,
            actor_type="user",
            actor_id=user_id,
            action="company.created",
            entity_type="company",
            entity_id=company.id,
        )

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
async def get_suggestions(request: Request) -> dict:
    user_info = await require_user(request)
    user_id = UUID(user_info["sub"])
    email = user_info.get("email", "")
    domain = _email_domain(email) if "@" in email else ""

    invitations_out = []
    domain_matches_out = []

    async with get_db() as session:
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
            invitations_out.append({
                "id": str(inv.id),
                "company_id": str(inv.company_id),
                "company_name": company.name,
                "invited_by": invited_by_name,
                "expires_at": inv.expires_at.isoformat(),
            })

        # Verified domain policies for the caller's email domain
        if domain:
            policy = await domain_repo.get_by_domain(domain)
            if policy and policy.verified:
                company = await company_repo.get_by_id(policy.company_id)
                if company:
                    domain_matches_out.append({
                        "company_id": str(company.id),
                        "company_name": company.name,
                        "domain": policy.domain,
                        "policy": policy.policy.value,
                    })

    return {"invitations": invitations_out, "domain_matches": domain_matches_out}


@router.post("/companies/{company_id}/join")
async def join_company(company_id: UUID, body: JoinRequest_, request: Request) -> dict:
    user_info = await require_user(request)
    user_id = UUID(user_info["sub"])
    email = user_info.get("email", "")

    async with get_db() as session:
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
                detail={"error": {"code": "already_member", "message": "Already a member of this company"}},
            )

        if body.method == "invitation":
            if body.invitation_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"error": {"code": "missing_invitation_id", "message": "invitation_id is required for method=invitation"}},
                )
            inv_repo = SqlInvitationRepository(session)
            invitation = await inv_repo.get_by_id(body.invitation_id)

            if invitation is None or invitation.status != InvitationStatus.PENDING:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error": {"code": "invitation_invalid", "message": "Invitation not found, expired, or already used"}},
                )
            from datetime import UTC, datetime

            if invitation.expires_at < datetime.now(UTC):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"error": {"code": "invitation_expired", "message": "Invitation has expired"}},
                )

            await inv_repo.update_status(invitation.id, InvitationStatus.ACCEPTED)
            await company_repo.add_membership(
                CompanyMembership(user_id=user_id, company_id=company_id, role=CompanyRole.MEMBER)
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

            return {"status": "joined", "company_id": str(company_id), "company_name": company.name, "role": "member"}

        elif body.method == "domain_match":
            domain = _email_domain(email) if "@" in email else ""
            if not domain:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email domain required")

            domain_repo = SqlDomainPolicyRepository(session)
            policy = await domain_repo.get_by_domain(domain)
            if policy is None or policy.company_id != company_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"error": {"code": "no_domain_policy", "message": "No verified domain policy found"}},
                )
            if not policy.verified:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error": {"code": "domain_not_verified", "message": "Domain not yet verified"}},
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

                return {"status": "joined", "company_id": str(company_id), "company_name": company.name, "role": "member"}

            else:  # request_approval
                jr_repo = SqlJoinRequestRepository(session)
                existing_request = await jr_repo.get_by_user_and_company(user_id, company_id)
                if existing_request and existing_request.status == JoinRequestStatus.PENDING:
                    return {"status": "pending", "company_id": str(company_id), "company_name": company.name}

                join_request = await jr_repo.create(
                    JoinRequest(user_id=user_id, company_id=company_id)
                )

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

                return {"status": "pending", "company_id": str(company_id), "company_name": company.name}

        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown join method")


@router.get("/companies/{company_id}/join-status")
async def get_join_status(company_id: UUID, request: Request) -> dict:
    user_info = await require_user(request)
    user_id = UUID(user_info["sub"])

    async with get_db() as session:
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
                "requested_at": join_req.requested_at.isoformat() if join_req.requested_at else None,
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
async def cancel_join_request(company_id: UUID, request: Request) -> Response:
    user_info = await require_user(request)
    user_id = UUID(user_info["sub"])

    async with get_db() as session:
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
async def list_join_requests(company_id: UUID, request: Request) -> dict:
    user_info = await require_user(request)
    user_id = UUID(user_info["sub"])

    async with get_db() as session:
        company_repo = SqlCompanyRepository(session)
        await _require_company_admin(user_id, company_id, company_repo)

        jr_repo = SqlJoinRequestRepository(session)
        requests = await jr_repo.list_pending_for_company(company_id)
        user_repo = SqlUserRepository(session)

        items = []
        for jr in requests:
            requester = await user_repo.get_by_id(jr.user_id)
            items.append({
                "id": str(jr.id),
                "user_id": str(jr.user_id),
                "user_name": requester.display_name if requester else "",
                "user_email": requester.email if requester else "",
                "requested_at": jr.requested_at.isoformat() if jr.requested_at else None,
            })

    return {"join_requests": items}


@router.post("/companies/{company_id}/join-requests/{request_id}/approve")
async def approve_join_request(
    company_id: UUID, request_id: UUID, request: Request
) -> dict:
    user_info = await require_user(request)
    admin_id = UUID(user_info["sub"])

    async with get_db() as session:
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
                detail={"error": {"code": "already_decided", "message": "Join request already decided"}},
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
    company_id: UUID, request_id: UUID, request: Request
) -> dict:
    user_info = await require_user(request)
    admin_id = UUID(user_info["sub"])

    async with get_db() as session:
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
                detail={"error": {"code": "already_decided", "message": "Join request already decided"}},
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
    company_id: UUID, body: CreateDomainPolicyRequest, request: Request
) -> dict:
    user_info = await require_user(request)
    user_id = UUID(user_info["sub"])

    domain = body.domain.lower().lstrip("@")

    async with get_db() as session:
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
                detail={"error": {"code": "domain_already_claimed", "message": f"Domain {domain} is already claimed"}},
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
async def verify_domain(token: str) -> Response:
    """Public endpoint — no auth required. Validates a domain verification token."""
    from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
    from fastapi.responses import RedirectResponse
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

    async with get_db() as session:
        domain_repo = SqlDomainPolicyRepository(session)
        policy = await domain_repo.get_by_id(UUID(policy_id))
        if policy is None:
            return RedirectResponse(url=f"{settings.frontend_url}/settings/domain?error=invalid")
        if not policy.verified:
            await domain_repo.mark_verified(UUID(policy_id))

    return RedirectResponse(url=f"{settings.frontend_url}/settings/domain?verified=true")


@router.post("/companies/{company_id}/activate")
async def activate_company(company_id: UUID, request: Request) -> dict:
    """Issue a company-scoped JWT and set active_company_id in session."""
    user_info = await require_user(request)
    user_id = UUID(user_info["sub"])

    async with get_db() as session:
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
        request.session["user"] = {}
    request.session["user"]["active_company_id"] = str(company_id)

    return {"token": token, "company_id": str(company_id), "company_name": company.name}
