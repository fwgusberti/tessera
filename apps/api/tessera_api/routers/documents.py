"""Document and version endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel

from tessera_core.domain.entities import (
    Confidentiality,
    Document,
    DocumentLifecycleState,
    DocumentVersion,
)
from tessera_core.permissions.access import AccessContext, can_publish_document, can_read_document
from tessera_core.permissions.access import AccessDecision

router = APIRouter(tags=["documents"])


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
    space_id: UUID | None = Query(None),
    state: str | None = Query(None),
    request: Request = None,
) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlDocumentRepository
    from tessera_api.auth.oidc import require_user

    await require_user(request)
    async with get_db() as session:
        repo = SqlDocumentRepository(session)
        state_enum = DocumentLifecycleState(state) if state else None
        if space_id:
            docs = await repo.list_by_space(space_id, state_enum)
        else:
            docs = []
    return {"documents": [d.model_dump() for d in docs]}


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def create_document(body: CreateDocumentRequest, request: Request) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlDocumentRepository, SqlDocumentVersionRepository
    from tessera_api.auth.oidc import require_user

    user_info = await require_user(request)
    async with get_db() as session:
        doc_repo = SqlDocumentRepository(session)
        ver_repo = SqlDocumentVersionRepository(session)

        doc = Document(
            space_id=body.space_id,
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

    return {"document": created_doc.model_dump(), "version": created_version.model_dump()}


@router.get("/documents/{document_id}")
async def get_document(document_id: UUID, request: Request) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlDocumentRepository, SqlDocumentVersionRepository, SqlSpaceRepository
    from tessera_api.auth.oidc import require_user

    user_info = await require_user(request)
    async with get_db() as session:
        doc_repo = SqlDocumentRepository(session)
        ver_repo = SqlDocumentVersionRepository(session)
        space_repo = SqlSpaceRepository(session)

        doc = await doc_repo.get_by_id(document_id)
        if doc is None:
            raise HTTPException(status_code=404)

        version = None
        if doc.current_version_id:
            version = await ver_repo.get_by_id(doc.current_version_id)

    return {"document": doc.model_dump(), "current_version": version.model_dump() if version else None}


@router.get("/documents/{document_id}/versions")
async def list_versions(document_id: UUID, request: Request) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlDocumentVersionRepository
    from tessera_api.auth.oidc import require_user

    await require_user(request)
    async with get_db() as session:
        repo = SqlDocumentVersionRepository(session)
        versions = await repo.list_by_document(document_id)
    return {"versions": [v.model_dump() for v in versions]}


@router.post("/documents/{document_id}/publish")
async def publish_document(document_id: UUID, request: Request) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlDocumentRepository, SqlDocumentVersionRepository, SqlSpaceRepository
    from tessera_api.adapters.audit import write_audit
    from tessera_api.auth.oidc import require_user
    from tessera_core.services.lifecycle import publish_document as lifecycle_publish

    user_info = await require_user(request)
    async with get_db() as session:
        doc_repo = SqlDocumentRepository(session)
        ver_repo = SqlDocumentVersionRepository(session)

        doc = await doc_repo.get_by_id(document_id)
        if doc is None:
            raise HTTPException(status_code=404)

        if doc.owner_user_id is None:
            raise HTTPException(status_code=400, detail="Document has no owner — assign one before publishing")

        versions = await ver_repo.list_by_document(document_id)
        if not versions:
            raise HTTPException(status_code=400, detail="No versions to publish")

        latest = versions[-1]
        now = datetime.now(timezone.utc)

        # Mark version as approved
        approved_version = latest.model_copy(update={
            "approver_user_id": user_info.get("id"),
            "approved_at": now,
        })
        await ver_repo.create(approved_version)

        # Transition document state
        updated = lifecycle_publish(doc, version_id=latest.id, approver_id=user_info.get("id"))
        await doc_repo.update_state(document_id, updated.state)
        await doc_repo.set_current_version(document_id, latest.id)

        await write_audit(
            session,
            actor_type="user",
            actor_id=user_info.get("id"),
            action="publish",
            entity_type="document",
            entity_id=document_id,
        )

    return {"document": updated.model_dump(), "version": latest.model_dump()}
