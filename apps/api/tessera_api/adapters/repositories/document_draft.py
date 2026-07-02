from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.document import DocumentModel
from tessera_api.adapters.models.document_draft import DocumentDraftModel
from tessera_api.adapters.models.space import SpaceModel
from tessera_core.domain.document_draft import DocumentDraft
from tessera_core.ports.repositories.document_draft import DocumentDraftRepository


def _draft_from_model(m: DocumentDraftModel) -> DocumentDraft:
    return DocumentDraft(
        document_id=m.document_id,
        content_markdown=m.content_markdown,
        editor_user_id=m.editor_user_id,
        started_at=m.started_at,
        last_autosaved_at=m.last_autosaved_at,
    )


class SqlDocumentDraftRepository(DocumentDraftRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_document_id_for_company(
        self, document_id: UUID, company_id: UUID
    ) -> DocumentDraft | None:
        result = await self._session.execute(
            select(DocumentDraftModel)
            .join(DocumentModel, DocumentModel.id == DocumentDraftModel.document_id)
            .join(SpaceModel, SpaceModel.id == DocumentModel.space_id)
            .where(
                DocumentDraftModel.document_id == document_id,
                SpaceModel.company_id == company_id,
            )
        )
        model = result.scalar_one_or_none()
        return _draft_from_model(model) if model else None

    async def upsert_for_company(
        self,
        document_id: UUID,
        company_id: UUID,
        editor_user_id: UUID,
        content_markdown: str,
    ) -> DocumentDraft:
        owned = await self._session.execute(
            select(DocumentModel.id)
            .join(SpaceModel, SpaceModel.id == DocumentModel.space_id)
            .where(DocumentModel.id == document_id, SpaceModel.company_id == company_id)
        )
        if owned.scalar_one_or_none() is None:
            raise LookupError(f"document {document_id} not found for company {company_id}")

        now = datetime.now(UTC)
        insert_stmt = pg_insert(DocumentDraftModel).values(
            document_id=document_id,
            content_markdown=content_markdown,
            editor_user_id=editor_user_id,
            started_at=now,
            last_autosaved_at=now,
        )
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[DocumentDraftModel.document_id],
            set_={
                "content_markdown": insert_stmt.excluded.content_markdown,
                "editor_user_id": insert_stmt.excluded.editor_user_id,
                "last_autosaved_at": insert_stmt.excluded.last_autosaved_at,
            },
        ).returning(DocumentDraftModel)
        result = await self._session.execute(upsert_stmt)
        model = result.scalar_one()
        await self._session.flush()
        return _draft_from_model(model)

    async def delete_for_company(self, document_id: UUID, company_id: UUID) -> None:
        existing = await self.get_by_document_id_for_company(document_id, company_id)
        if existing is None:
            return
        await self._session.execute(
            delete(DocumentDraftModel).where(DocumentDraftModel.document_id == document_id)
        )
        await self._session.flush()
