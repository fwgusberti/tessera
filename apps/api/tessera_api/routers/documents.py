"""Document and version endpoints."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from tessera_api.adapters.audit import write_audit
from tessera_api.adapters.celery import get_celery_app
from tessera_api.adapters.database import SessionDep
from tessera_api.adapters.repo import (
    SqlDocumentRepository,
    SqlDocumentVersionRepository,
    SqlSpaceMembershipRepository,
    SqlSpaceRepository,
    SqlUserRepository,
)
from tessera_api.auth.oidc import (
    CompanyContext,
    CompanyMemberContext,
    is_company_admin,
)
from tessera_core.domain.entities import (
    Confidentiality,
    Document,
    DocumentLifecycleState,
    DocumentVersion,
)
from tessera_core.permissions.access import can_write_document
from tessera_core.services.lifecycle import assign_owner
from tessera_core.services.lifecycle import publish_document as lifecycle_publish

router = APIRouter(tags=["documents"])


def _not_found() -> HTTPException:
    """Generic 404 for cross-company by-ID access — indistinguishable from absent (FR-004)."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": {"code": "not_found", "message": "Not found"}},
    )


class CreateDocumentRequest(BaseModel):
    space_id: UUID
    title: str
    language: str = "pt-BR"
    confidentiality: Confidentiality = Confidentiality.INTERNAL
    tags: list[str] = []
    content_markdown: str
    frontmatter: dict[str, Any] = {}


@router.get("/documents")
async def list_documents(
    ctx: CompanyContext,
    session: SessionDep,
    space_id: UUID | None = Query(None),  # noqa: B008
    state: str | None = Query(None),  # noqa: B008
) -> dict:
    user_info, company_id = ctx
    doc_repo = SqlDocumentRepository(session)
    space_repo = SqlSpaceRepository(session)
    state_enum = DocumentLifecycleState(state) if state else None

    if space_id:
        space = await space_repo.get_by_id_for_company(space_id, company_id)
        if space is None:
            actor_id = UUID(user_info.get("sub", ""))
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
        docs = await doc_repo.list_by_space(space_id, state_enum)
    else:
        company_spaces = await space_repo.list_by_company(company_id)
        space_ids = [s.id for s in company_spaces]
        docs = await doc_repo.list_by_space_ids_for_company(space_ids, company_id, state_enum)

    return {"documents": [d.model_dump() for d in docs]}


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def create_document(
    body: CreateDocumentRequest, ctx: CompanyMemberContext, session: SessionDep
) -> dict:
    user_info, company_id, caller_membership = ctx
    company_admin = is_company_admin(caller_membership)
    user_id_str = user_info.get("id") or user_info.get("sub")
    owner_id = UUID(user_id_str) if user_id_str else None

    space_repo = SqlSpaceRepository(session)
    space = await space_repo.get_by_id_for_company(body.space_id, company_id)
    if space is None:
        actor_id = UUID(user_info.get("sub", "")) if owner_id is None else owner_id
        await write_audit(
            session,
            actor_type="user",
            actor_id=actor_id,
            action="cross_tenant_denied",
            entity_type="space",
            entity_id=body.space_id,
            metadata={"company_id": str(company_id)},
        )
        await session.commit()
        raise _not_found()

    user_repo = SqlUserRepository(session)
    actor = await user_repo.get_by_id(owner_id) if owner_id else None
    if actor is None:
        with contextlib.suppress(Exception):
            actor = await user_repo.get_by_subject(user_info.get("sub", ""))

    if actor is not None:
        membership_repo = SqlSpaceMembershipRepository(session)
        memberships = await membership_repo.list_by_space(body.space_id)
        if not can_write_document(
            actor, body.space_id, memberships, is_company_admin=company_admin
        ):
            raise HTTPException(
                status_code=403,
                detail="You must be an Editor or Admin to create documents in this space",
            )

    doc_repo = SqlDocumentRepository(session)
    ver_repo = SqlDocumentVersionRepository(session)

    doc = Document(
        space_id=body.space_id,
        owner_user_id=owner_id,
        title=body.title,
        language=body.language,
        confidentiality=body.confidentiality,
        tags=body.tags,
        state=DocumentLifecycleState.INGESTED,
    )
    created_doc = await doc_repo.create(doc)
    version = DocumentVersion(
        document_id=created_doc.id,
        version_number=1,
        content_markdown=body.content_markdown,
        frontmatter=body.frontmatter,
    )
    created_version = await ver_repo.create(version)
    created_doc = await doc_repo.set_current_version(created_doc.id, created_version.id)

    return {"document": created_doc.model_dump(), "version": created_version.model_dump()}


@router.get("/documents/{document_id}")
async def get_document(
    document_id: UUID, ctx: CompanyContext, session: SessionDep
) -> dict:
    user_info, company_id = ctx
    doc_repo = SqlDocumentRepository(session)
    ver_repo = SqlDocumentVersionRepository(session)

    doc = await doc_repo.get_by_id_for_company(document_id, company_id)
    if doc is None:
        actor_id = UUID(user_info["sub"])
        await write_audit(
            session,
            actor_type="user",
            actor_id=actor_id,
            action="cross_tenant_denied",
            entity_type="document",
            entity_id=document_id,
            metadata={"company_id": str(company_id)},
        )
        await session.commit()
        raise _not_found()

    version = None
    if doc.current_version_id:
        version = await ver_repo.get_by_id(doc.current_version_id)

    return {
        "document": doc.model_dump(),
        "current_version": version.model_dump() if version else None,
    }


@router.get("/documents/{document_id}/versions")
async def list_versions(
    document_id: UUID, ctx: CompanyContext, session: SessionDep
) -> dict:
    user_info, company_id = ctx
    doc_repo = SqlDocumentRepository(session)
    doc = await doc_repo.get_by_id_for_company(document_id, company_id)
    if doc is None:
        actor_id = UUID(user_info["sub"])
        await write_audit(
            session,
            actor_type="user",
            actor_id=actor_id,
            action="cross_tenant_denied",
            entity_type="document",
            entity_id=document_id,
            metadata={"company_id": str(company_id)},
        )
        await session.commit()
        raise _not_found()
    repo = SqlDocumentVersionRepository(session)
    versions = await repo.list_by_document(document_id)
    return {"versions": [v.model_dump() for v in versions]}


@router.post("/documents/{document_id}/publish")
async def publish_document(
    document_id: UUID, ctx: CompanyContext, session: SessionDep
) -> dict:
    user_info, company_id = ctx
    user_id_str = user_info.get("id") or user_info.get("sub")
    publisher_id = UUID(user_id_str) if user_id_str else None

    doc_repo = SqlDocumentRepository(session)
    ver_repo = SqlDocumentVersionRepository(session)

    doc = await doc_repo.get_by_id_for_company(document_id, company_id)
    if doc is None:
        actor_id = publisher_id or UUID(user_info["sub"])
        await write_audit(
            session,
            actor_type="user",
            actor_id=actor_id,
            action="cross_tenant_denied",
            entity_type="document",
            entity_id=document_id,
            metadata={"company_id": str(company_id)},
        )
        await session.commit()
        raise _not_found()

    if doc.owner_user_id is None and publisher_id:
        doc = assign_owner(doc, publisher_id)
        await doc_repo.set_owner(document_id, publisher_id)

    versions = await ver_repo.list_by_document(document_id)
    if not versions:
        raise HTTPException(status_code=400, detail="No versions to publish")

    latest = versions[-1]
    now = datetime.now(UTC)

    await ver_repo.update_approval(latest.id, publisher_id, now)

    updated = lifecycle_publish(doc, version_id=latest.id, approver_id=publisher_id)
    await doc_repo.update_state(document_id, updated.state)
    await doc_repo.set_current_version(document_id, latest.id)

    await write_audit(
        session,
        actor_type="user",
        actor_id=publisher_id,
        action="publish",
        entity_type="document",
        entity_id=document_id,
    )

    get_celery_app().send_task(
        "tessera.index_document_version",
        args=[str(latest.id), str(document_id), str(doc.space_id)],
    )

    return {"document": updated.model_dump(), "version": latest.model_dump()}


@router.post("/documents/{document_id}/reindex")
async def reindex_document(
    document_id: UUID, ctx: CompanyMemberContext, session: SessionDep
) -> dict:
    user_info, company_id, caller_membership = ctx
    company_admin = is_company_admin(caller_membership)
    user_id_str = user_info.get("id") or user_info.get("sub")
    user_id = UUID(user_id_str) if user_id_str else None

    doc_repo = SqlDocumentRepository(session)
    ver_repo = SqlDocumentVersionRepository(session)

    doc = await doc_repo.get_by_id_for_company(document_id, company_id)
    if doc is None:
        actor_id = user_id or UUID(user_info["sub"])
        await write_audit(
            session,
            actor_type="user",
            actor_id=actor_id,
            action="cross_tenant_denied",
            entity_type="document",
            entity_id=document_id,
            metadata={"company_id": str(company_id)},
        )
        await session.commit()
        raise _not_found()

    if not company_admin and doc.owner_user_id != user_id:
        raise HTTPException(
            status_code=403, detail="Only the document owner or an admin may reindex"
        )

    if doc.state != DocumentLifecycleState.PUBLISHED:
        raise HTTPException(status_code=400, detail="Only published documents can be reindexed")

    versions = await ver_repo.list_by_document(document_id)
    if not versions:
        raise HTTPException(status_code=400, detail="No versions to index")
    latest = versions[-1]

    get_celery_app().send_task(
        "tessera.index_document_version",
        args=[str(latest.id), str(document_id), str(doc.space_id)],
    )

    return {"queued": True, "document_id": str(document_id)}
