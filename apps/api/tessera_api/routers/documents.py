"""Document and version endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
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
    space_id: UUID | None = Query(None),  # noqa: B008
    state: str | None = Query(None),  # noqa: B008
    request: Request = None,
) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import (
        SqlDocumentRepository,
        SqlSpaceRepository,
        SqlUserRepository,
    )
    from tessera_api.auth.oidc import require_user

    user_info = await require_user(request)
    async with get_db() as session:
        doc_repo = SqlDocumentRepository(session)
        state_enum = DocumentLifecycleState(state) if state else None
        if space_id:
            docs = await doc_repo.list_by_space(space_id, state_enum)
        else:
            user_repo = SqlUserRepository(session)
            space_repo = SqlSpaceRepository(session)
            user = await user_repo.get_by_subject(user_info["sub"])
            if user is None:
                import contextlib

                with contextlib.suppress(ValueError, KeyError):
                    user = await user_repo.get_by_id(UUID(user_info["sub"]))
            if user is None:
                docs = []
            else:
                spaces = await space_repo.list_for_user(user)
                space_ids = [s.id for s in spaces]
                docs = await doc_repo.list_by_space_ids(space_ids, state_enum)
    return {"documents": [d.model_dump() for d in docs]}


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def create_document(body: CreateDocumentRequest, request: Request) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlDocumentRepository, SqlDocumentVersionRepository
    from tessera_api.auth.oidc import require_user

    user_info = await require_user(request)
    user_id_str = user_info.get("id") or user_info.get("sub")
    owner_id = UUID(user_id_str) if user_id_str else None
    async with get_db() as session:
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
async def get_document(document_id: UUID, request: Request) -> dict:
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlDocumentRepository, SqlDocumentVersionRepository
    from tessera_api.auth.oidc import require_user

    await require_user(request)
    async with get_db() as session:
        doc_repo = SqlDocumentRepository(session)
        ver_repo = SqlDocumentVersionRepository(session)

        doc = await doc_repo.get_by_id(document_id)
        if doc is None:
            raise HTTPException(status_code=404)

        version = None
        if doc.current_version_id:
            version = await ver_repo.get_by_id(doc.current_version_id)

    return {
        "document": doc.model_dump(),
        "current_version": version.model_dump() if version else None,
    }


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
    from tessera_api.adapters.audit import write_audit
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import (
        SqlDocumentRepository,
        SqlDocumentVersionRepository,
    )
    from tessera_api.auth.oidc import require_user
    from tessera_core.services.lifecycle import publish_document as lifecycle_publish

    user_info = await require_user(request)
    user_id_str = user_info.get("id") or user_info.get("sub")
    publisher_id = UUID(user_id_str) if user_id_str else None
    async with get_db() as session:
        doc_repo = SqlDocumentRepository(session)
        ver_repo = SqlDocumentVersionRepository(session)

        doc = await doc_repo.get_by_id(document_id)
        if doc is None:
            raise HTTPException(status_code=404)

        if doc.owner_user_id is None and publisher_id:
            from tessera_core.services.lifecycle import assign_owner

            doc = assign_owner(doc, publisher_id)
            await doc_repo.set_owner(document_id, publisher_id)

        versions = await ver_repo.list_by_document(document_id)
        if not versions:
            raise HTTPException(status_code=400, detail="No versions to publish")

        latest = versions[-1]
        now = datetime.now(UTC)

        await ver_repo.update_approval(latest.id, publisher_id, now)

        # Transition document state
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

    from tessera_api.adapters.celery import get_celery_app

    get_celery_app().send_task(
        "tessera.index_document_version",
        args=[str(latest.id), str(document_id), str(doc.space_id)],
    )

    return {"document": updated.model_dump(), "version": latest.model_dump()}


@router.post("/documents/{document_id}/reindex")
async def reindex_document(document_id: UUID, request: Request) -> dict:
    from tessera_api.adapters.celery import get_celery_app
    from tessera_api.adapters.database import get_db
    from tessera_api.adapters.repo import SqlDocumentRepository, SqlDocumentVersionRepository
    from tessera_api.auth.oidc import require_user

    user_info = await require_user(request)
    user_id_str = user_info.get("id") or user_info.get("sub")
    user_id = UUID(user_id_str) if user_id_str else None
    is_admin = user_info.get("is_admin", False)

    async with get_db() as session:
        doc_repo = SqlDocumentRepository(session)
        ver_repo = SqlDocumentVersionRepository(session)

        doc = await doc_repo.get_by_id(document_id)
        if doc is None:
            raise HTTPException(status_code=404)

        if not is_admin and doc.owner_user_id != user_id:
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
