from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.document import DocumentModel
from tessera_api.adapters.models.space import SpaceModel
from tessera_core.domain.confidentiality import Confidentiality
from tessera_core.domain.document import Document
from tessera_core.domain.document_lifecycle_state import DocumentLifecycleState
from tessera_core.ports.repositories.document import DocumentRepository


def _doc_from_model(m: DocumentModel) -> Document:
    return Document(
        id=m.id,
        space_id=m.space_id,
        owner_user_id=m.owner_user_id,
        title=m.title,
        language=m.language,
        confidentiality=Confidentiality(m.confidentiality),
        tags=m.tags or [],
        validity_until=m.validity_until,
        state=DocumentLifecycleState(m.state),
        current_version_id=m.current_version_id,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SqlDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, document: Document) -> Document:
        model = DocumentModel(
            id=document.id,
            space_id=document.space_id,
            owner_user_id=document.owner_user_id,
            title=document.title,
            language=document.language,
            confidentiality=document.confidentiality.value,
            tags=document.tags,
            validity_until=document.validity_until,
            state=document.state.value,
            current_version_id=document.current_version_id,
        )
        self._session.add(model)
        await self._session.flush()
        return _doc_from_model(model)

    async def get_by_id(self, document_id: UUID) -> Document | None:
        result = await self._session.execute(
            select(DocumentModel).where(DocumentModel.id == document_id)
        )
        model = result.scalar_one_or_none()
        return _doc_from_model(model) if model else None

    async def list_by_space(
        self, space_id: UUID, state: DocumentLifecycleState | None = None
    ) -> list[Document]:
        q = select(DocumentModel).where(DocumentModel.space_id == space_id)
        if state:
            q = q.where(DocumentModel.state == state.value)
        result = await self._session.execute(q)
        return [_doc_from_model(m) for m in result.scalars().all()]

    async def get_by_id_for_company(self, document_id: UUID, company_id: UUID) -> Document | None:
        result = await self._session.execute(
            select(DocumentModel)
            .join(SpaceModel, SpaceModel.id == DocumentModel.space_id)
            .where(DocumentModel.id == document_id, SpaceModel.company_id == company_id)
        )
        model = result.scalar_one_or_none()
        return _doc_from_model(model) if model else None

    async def list_by_space_ids(
        self, space_ids: list[UUID], state: DocumentLifecycleState | None = None
    ) -> list[Document]:
        if not space_ids:
            return []
        q = select(DocumentModel).where(DocumentModel.space_id.in_(space_ids))
        if state:
            q = q.where(DocumentModel.state == state.value)
        result = await self._session.execute(q)
        return [_doc_from_model(m) for m in result.scalars().all()]

    async def list_by_space_ids_for_company(
        self,
        space_ids: list[UUID],
        company_id: UUID,
        state: DocumentLifecycleState | None = None,
    ) -> list[Document]:
        if not space_ids:
            return []
        q = (
            select(DocumentModel)
            .join(SpaceModel, SpaceModel.id == DocumentModel.space_id)
            .where(
                DocumentModel.space_id.in_(space_ids),
                SpaceModel.company_id == company_id,
            )
        )
        if state:
            q = q.where(DocumentModel.state == state.value)
        result = await self._session.execute(q)
        return [_doc_from_model(m) for m in result.scalars().all()]

    async def update_state(self, document_id: UUID, state: DocumentLifecycleState) -> Document:
        await self._session.execute(
            update(DocumentModel).where(DocumentModel.id == document_id).values(state=state.value)
        )
        doc = await self.get_by_id(document_id)
        assert doc is not None
        return doc

    async def set_current_version(self, document_id: UUID, version_id: UUID) -> Document:
        await self._session.execute(
            update(DocumentModel)
            .where(DocumentModel.id == document_id)
            .values(current_version_id=version_id)
        )
        doc = await self.get_by_id(document_id)
        assert doc is not None
        return doc

    async def set_owner(self, document_id: UUID, user_id: UUID) -> Document:
        await self._session.execute(
            update(DocumentModel)
            .where(DocumentModel.id == document_id)
            .values(owner_user_id=user_id)
        )
        doc = await self.get_by_id(document_id)
        assert doc is not None
        return doc

    async def delete(self, document_id: UUID) -> None:
        await self._session.execute(delete(DocumentModel).where(DocumentModel.id == document_id))
