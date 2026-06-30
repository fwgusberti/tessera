"""Proposal review endpoints: list, get, approve, reject.

All handlers are scoped to the active company (feature 035/036): a proposal is
only reachable when its document's space belongs to the caller's active company.
A cross-company by-ID access is audited as ``cross_tenant_denied`` and returns the
same generic 404 body as a missing proposal (indistinguishable — FR-004 / SC-003).
Approve/reject authority is per-company admin (or in-company publish rights); an
in-company non-admin without those rights still receives 403.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.audit import write_audit
from tessera_api.adapters.database import SessionDep
from tessera_api.adapters.repo import (
    SqlDocumentRepository,
    SqlDocumentVersionRepository,
    SqlProposalRepository,
    SqlSpaceRepository,
    SqlUserRepository,
)
from tessera_api.auth.oidc import (
    CompanyContext,
    CompanyMemberContext,
    is_company_admin,
)
from tessera_core.domain.entities import DocumentLifecycleState, DocumentVersion
from tessera_core.permissions.access import (
    AccessContext,
    AccessDecision,
    can_approve_proposal,
)
from tessera_core.services.proposals import approve_proposal as svc_approve
from tessera_core.services.proposals import reject_proposal as svc_reject

router = APIRouter(tags=["proposals"])


class RejectRequest(BaseModel):
    reason: str | None = None


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": {"code": "forbidden", "message": "Access denied"}},
    )


def _not_found() -> HTTPException:
    """Generic 404 for cross-company by-ID access — indistinguishable from absent (FR-004)."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": {"code": "not_found", "message": "Not found"}},
    )


async def _audit_cross_tenant(
    session: AsyncSession, actor_id: UUID, proposal_id: UUID, company_id: UUID
) -> None:
    await write_audit(
        session,
        actor_type="user",
        actor_id=actor_id,
        action="cross_tenant_denied",
        entity_type="proposal",
        entity_id=proposal_id,
        metadata={"company_id": str(company_id)},
    )


@router.get("/proposals")
async def list_proposals(
    ctx: CompanyContext,
    session: SessionDep,
    state: str | None = Query(None),  # noqa: B008
    space_id: UUID | None = Query(None),  # noqa: B008
) -> dict:
    _user_info, company_id = ctx
    repo = SqlProposalRepository(session)
    proposals = await repo.list_for_company(company_id, state=state, space_id=space_id)
    return {"proposals": [p.model_dump() for p in proposals]}


@router.get("/proposals/{proposal_id}")
async def get_proposal(
    proposal_id: UUID, ctx: CompanyContext, session: SessionDep
) -> dict:
    user_info, company_id = ctx
    proposal_repo = SqlProposalRepository(session)
    doc_repo = SqlDocumentRepository(session)

    proposal = await proposal_repo.get_by_id_for_company(proposal_id, company_id)
    if proposal is None:
        await _audit_cross_tenant(session, UUID(user_info["sub"]), proposal_id, company_id)
        await session.commit()
        raise _not_found()

    doc = await doc_repo.get_by_id_for_company(proposal.document_id, company_id)

    return {
        "proposal": proposal.model_dump(),
        "diff": proposal.proposed_markdown_patch,
        "target_document": doc.model_dump() if doc else None,
    }


@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: UUID, ctx: CompanyMemberContext, session: SessionDep
) -> dict:
    user_info, company_id, caller_membership = ctx
    company_admin = is_company_admin(caller_membership)
    actor_id = UUID(user_info["sub"])
    approver_id = user_info.get("id")

    proposal_repo = SqlProposalRepository(session)
    doc_repo = SqlDocumentRepository(session)
    ver_repo = SqlDocumentVersionRepository(session)
    user_repo = SqlUserRepository(session)
    space_repo = SqlSpaceRepository(session)

    proposal = await proposal_repo.get_by_id_for_company(proposal_id, company_id)
    if proposal is None:
        await _audit_cross_tenant(session, actor_id, proposal_id, company_id)
        await session.commit()
        raise _not_found()

    doc = await doc_repo.get_by_id_for_company(proposal.document_id, company_id)
    if doc is None:
        await _audit_cross_tenant(session, actor_id, proposal_id, company_id)
        await session.commit()
        raise _not_found()

    # In-company publish rights (FR-004): caller must be able to publish the
    # target document's space (space role or company admin), even within their
    # own company. An in-company non-admin without publish rights gets 403.
    actor = await user_repo.get_by_id(actor_id)
    permissions = await space_repo.list_role_permissions(doc.space_id)
    ctx_access = AccessContext(
        user=actor, space_permissions=permissions, is_company_admin=company_admin
    )
    if can_approve_proposal(ctx=ctx_access, document=doc) == AccessDecision.DENY:
        raise _forbidden()

    approved = svc_approve(proposal=proposal, approver_id=approver_id)
    await proposal_repo.update_state(approved)

    # Create new DocumentVersion from patch
    versions = await ver_repo.list_by_document(doc.id)
    next_version = len(versions) + 1
    new_version = DocumentVersion(
        document_id=doc.id,
        version_number=next_version,
        content_markdown=proposal.proposed_markdown_patch,
        frontmatter={},
        approver_user_id=approver_id,
        approved_at=datetime.now(UTC),
        created_from_proposal_id=proposal.id,
    )
    created_version = await ver_repo.create(new_version)
    await doc_repo.update_state(doc.id, DocumentLifecycleState.PUBLISHED)
    await doc_repo.set_current_version(doc.id, created_version.id)

    await write_audit(
        session,
        actor_type="user",
        actor_id=approver_id,
        action="approve",
        entity_type="proposal",
        entity_id=proposal_id,
    )

    updated_doc = await doc_repo.get_by_id(doc.id)

    return {"document": updated_doc.model_dump(), "version": created_version.model_dump()}


@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: UUID, body: RejectRequest, ctx: CompanyMemberContext, session: SessionDep
) -> dict:
    user_info, company_id, caller_membership = ctx
    company_admin = is_company_admin(caller_membership)
    actor_id = UUID(user_info["sub"])
    rejector_id = user_info.get("id")

    proposal_repo = SqlProposalRepository(session)
    doc_repo = SqlDocumentRepository(session)
    user_repo = SqlUserRepository(session)
    space_repo = SqlSpaceRepository(session)

    proposal = await proposal_repo.get_by_id_for_company(proposal_id, company_id)
    if proposal is None:
        await _audit_cross_tenant(session, actor_id, proposal_id, company_id)
        await session.commit()
        raise _not_found()

    doc = await doc_repo.get_by_id_for_company(proposal.document_id, company_id)
    if doc is None:
        await _audit_cross_tenant(session, actor_id, proposal_id, company_id)
        await session.commit()
        raise _not_found()

    # In-company publish rights (FR-004).
    actor = await user_repo.get_by_id(actor_id)
    permissions = await space_repo.list_role_permissions(doc.space_id)
    ctx_access = AccessContext(
        user=actor, space_permissions=permissions, is_company_admin=company_admin
    )
    if can_approve_proposal(ctx=ctx_access, document=doc) == AccessDecision.DENY:
        raise _forbidden()

    rejected = svc_reject(proposal=proposal, rejector_id=rejector_id, reason=body.reason)
    await proposal_repo.update_state(rejected)

    await write_audit(
        session,
        actor_type="user",
        actor_id=rejector_id,
        action="reject",
        entity_type="proposal",
        entity_id=proposal_id,
    )

    return {"proposal": rejected.model_dump()}
