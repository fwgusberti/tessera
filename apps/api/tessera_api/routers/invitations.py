"""Invitation management endpoints."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator

from tessera_api.adapters.audit import write_audit
from tessera_api.adapters.database import SessionDep
from tessera_api.adapters.repo import (
    SqlCompanyRepository,
    SqlInvitationRepository,
    SqlUserRepository,
)
from tessera_api.auth.oidc import CurrentUser, require_user
from tessera_core.domain.entities import CompanyRole, Invitation, InvitationStatus

router = APIRouter(tags=["invitations"])

INVITATION_TTL_DAYS = 7


class InvitationRequest(BaseModel):
    emails: list[EmailStr]

    @field_validator("emails")
    @classmethod
    def emails_not_empty_and_within_limit(cls, v: list[EmailStr]) -> list[EmailStr]:
        if not v:
            raise ValueError("emails must not be empty")
        if len(v) > 50:
            raise ValueError("at most 50 emails per request")
        return v


class FailedInvitation(BaseModel):
    email: str
    reason: str


class InvitationResponse(BaseModel):
    sent: list[str]
    failed: list[FailedInvitation]


async def send_invitation_email(
    *,
    to: str,
    company_name: str,
    invited_by: str,
    token: str,
) -> None:
    from tessera_api.adapters.email import FastMailEmailAdapter
    from tessera_api.config import get_settings

    settings = get_settings()
    accept_url = f"{settings.frontend_url}/onboarding/company?invite={token}"
    adapter = FastMailEmailAdapter()
    await adapter.send_invitation(
        to=to,
        company_name=company_name,
        invited_by=invited_by,
        accept_url=accept_url,
    )


@router.post("/invitations", status_code=207, response_model=InvitationResponse)
async def send_invitations(
    body: InvitationRequest,
    user_info: CurrentUser,
    session: SessionDep,
) -> InvitationResponse:
    user_id = UUID(user_info["sub"])
    caller_email: str = user_info.get("email", "")

    company_repo = SqlCompanyRepository(session)
    inv_repo = SqlInvitationRepository(session)
    user_repo = SqlUserRepository(session)

    # Resolve admin company
    memberships = await company_repo.list_memberships_for_user(user_id)
    admin_memberships = [m for m in memberships if m.role == CompanyRole.ADMIN]
    if not admin_memberships:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "not_admin", "message": "Only company admins can send invitations."},
        )

    company_id = admin_memberships[0].company_id
    company = await company_repo.get_by_id(company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

    caller = await user_repo.get_by_id(user_id)
    invited_by_name = caller.display_name if caller else caller_email

    sent: list[str] = []
    failed: list[FailedInvitation] = []
    to_create: list[Invitation] = []
    raw_tokens: dict[str, str] = {}

    # Deduplicate input
    seen_emails: set[str] = set()
    unique_emails: list[str] = []
    for em in body.emails:
        lower = em.lower()
        if lower not in seen_emails:
            seen_emails.add(lower)
            unique_emails.append(lower)

    for email in unique_emails:
        # Check already member via user lookup
        target_user = await user_repo.get_by_email(email)
        if target_user:
            existing_membership = await company_repo.get_membership(target_user.id, company_id)
            if existing_membership:
                failed.append(FailedInvitation(email=email, reason="already_member"))
                continue

        # Check pending invitation
        pending = await inv_repo.get_pending_for_email(email)
        if any(p.company_id == company_id for p in pending):
            failed.append(FailedInvitation(email=email, reason="already_invited"))
            continue

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        raw_tokens[email] = token

        to_create.append(
            Invitation(
                company_id=company_id,
                invited_by_user_id=user_id,
                email=email,
                token_hash=token_hash,
                status=InvitationStatus.PENDING,
                expires_at=datetime.now(UTC) + timedelta(days=INVITATION_TTL_DAYS),
            )
        )

    if to_create:
        await inv_repo.create_bulk(to_create)
        for inv in to_create:
            try:
                await send_invitation_email(
                    to=inv.email,
                    company_name=company.name,
                    invited_by=invited_by_name,
                    token=raw_tokens[inv.email],
                )
                await write_audit(
                    session,
                    actor_type="user",
                    actor_id=user_id,
                    action="invitation.sent",
                    entity_type="invitation",
                    entity_id=inv.id,
                    metadata={"email": inv.email, "company_id": str(company_id)},
                )
                sent.append(inv.email)
            except Exception:
                failed.append(FailedInvitation(email=inv.email, reason="send_failed"))

    return InvitationResponse(sent=sent, failed=failed)
