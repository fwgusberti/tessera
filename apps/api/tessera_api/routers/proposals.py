"""Proposal review endpoints: list, get, approve, reject."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel

router = APIRouter(tags=["proposals"])


class RejectRequest(BaseModel):
    reason: str | None = None


@router.get("/proposals")
async def list_proposals(
    state: str | None = Query(None),
    space_id: UUID | None = Query(None),
    request: Request = None,
) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlProposalRepository, SqlDocumentRepository
    from tessera_api.auth.oidc import require_user

    await require_user(request)
    async with get_db() as session:
        # If space_id given, list proposals for docs in that space
        from sqlalchemy import select
        from tessera_api.adapters.models import UpdateProposalModel, DocumentModel

        q = select(UpdateProposalModel)
        if state:
            q = q.where(UpdateProposalModel.state == state)
        if space_id:
            q = q.join(DocumentModel, DocumentModel.id == UpdateProposalModel.document_id).where(
                DocumentModel.space_id == space_id
            )
        result = await session.execute(q)
        from tessera_api.adapters.repo import _proposal_from_model

        proposals = [_proposal_from_model(m) for m in result.scalars().all()]
    return {"proposals": [p.model_dump() for p in proposals]}


@router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: UUID, request: Request) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlProposalRepository, SqlDocumentRepository, SqlDocumentVersionRepository
    from tessera_api.auth.oidc import require_user

    await require_user(request)
    async with get_db() as session:
        proposal_repo = SqlProposalRepository(session)
        doc_repo = SqlDocumentRepository(session)

        proposal = await proposal_repo.get_by_id(proposal_id)
        if proposal is None:
            raise HTTPException(status_code=404)

        doc = await doc_repo.get_by_id(proposal.document_id)

    return {
        "proposal": proposal.model_dump(),
        "diff": proposal.proposed_markdown_patch,
        "target_document": doc.model_dump() if doc else None,
    }


@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(proposal_id: UUID, request: Request) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import (
        SqlProposalRepository,
        SqlDocumentRepository,
        SqlDocumentVersionRepository,
    )
    from tessera_api.adapters.audit import write_audit
    from tessera_api.auth.oidc import require_user
    from tessera_core.services.proposals import approve_proposal as svc_approve
    from tessera_core.domain.entities import DocumentLifecycleState

    user_info = await require_user(request)
    async with get_db() as session:
        proposal_repo = SqlProposalRepository(session)
        doc_repo = SqlDocumentRepository(session)
        ver_repo = SqlDocumentVersionRepository(session)

        proposal = await proposal_repo.get_by_id(proposal_id)
        if proposal is None:
            raise HTTPException(status_code=404)

        doc = await doc_repo.get_by_id(proposal.document_id)
        if doc is None:
            raise HTTPException(status_code=404)

        approver_id = user_info.get("id")
        approved = svc_approve(proposal=proposal, approver_id=approver_id)
        await proposal_repo.update_state(approved)

        # Create new DocumentVersion from patch
        versions = await ver_repo.list_by_document(doc.id)
        next_version = len(versions) + 1
        from tessera_core.domain.entities import DocumentVersion

        new_version = DocumentVersion(
            document_id=doc.id,
            version_number=next_version,
            content_markdown=proposal.proposed_markdown_patch,
            frontmatter={},
            approver_user_id=approver_id,
            approved_at=datetime.now(timezone.utc),
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
async def reject_proposal(proposal_id: UUID, body: RejectRequest, request: Request) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlProposalRepository
    from tessera_api.adapters.audit import write_audit
    from tessera_api.auth.oidc import require_user
    from tessera_core.services.proposals import reject_proposal as svc_reject

    user_info = await require_user(request)
    async with get_db() as session:
        proposal_repo = SqlProposalRepository(session)
        proposal = await proposal_repo.get_by_id(proposal_id)
        if proposal is None:
            raise HTTPException(status_code=404)

        rejector_id = user_info.get("id")
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
