from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.document_version import DocumentVersionModel
from tessera_core.domain.document_version import DocumentVersion
from tessera_core.ports.repositories.document_version import DocumentVersionRepository


def _version_from_model(m: DocumentVersionModel) -> DocumentVersion:
    return DocumentVersion(
        id=m.id,
        document_id=m.document_id,
        version_number=m.version_number,
        content_markdown=m.content_markdown,
        frontmatter=m.frontmatter or {},
        author_user_id=m.author_user_id,
        approver_user_id=m.approver_user_id,
        approved_at=m.approved_at,
        source_artifact_id=m.source_artifact_id,
        created_from_proposal_id=m.created_from_proposal_id,
        created_at=m.created_at,
    )


class SqlDocumentVersionRepository(DocumentVersionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, version: DocumentVersion) -> DocumentVersion:
        model = DocumentVersionModel(
            id=version.id,
            document_id=version.document_id,
            version_number=version.version_number,
            content_markdown=version.content_markdown,
            frontmatter=version.frontmatter,
            author_user_id=version.author_user_id,
            approver_user_id=version.approver_user_id,
            approved_at=version.approved_at,
            source_artifact_id=version.source_artifact_id,
            created_from_proposal_id=version.created_from_proposal_id,
        )
        self._session.add(model)
        await self._session.flush()
        return _version_from_model(model)

    async def get_by_id(self, version_id: UUID) -> DocumentVersion | None:
        result = await self._session.execute(
            select(DocumentVersionModel).where(DocumentVersionModel.id == version_id)
        )
        model = result.scalar_one_or_none()
        return _version_from_model(model) if model else None

    async def list_by_document(self, document_id: UUID) -> list[DocumentVersion]:
        result = await self._session.execute(
            select(DocumentVersionModel)
            .where(DocumentVersionModel.document_id == document_id)
            .order_by(DocumentVersionModel.version_number)
        )
        return [_version_from_model(m) for m in result.scalars().all()]

    async def next_version_number(self, document_id: UUID) -> int:
        result = await self._session.execute(
            select(func.coalesce(func.max(DocumentVersionModel.version_number), 0)).where(
                DocumentVersionModel.document_id == document_id
            )
        )
        return (result.scalar() or 0) + 1

    async def update_approval(
        self, version_id: UUID, approver_id: UUID, approved_at: object
    ) -> DocumentVersion:
        await self._session.execute(
            update(DocumentVersionModel)
            .where(DocumentVersionModel.id == version_id)
            .values(approver_user_id=approver_id, approved_at=approved_at)
        )
        result = await self._session.execute(
            select(DocumentVersionModel).where(DocumentVersionModel.id == version_id)
        )
        model = result.scalar_one()
        return _version_from_model(model)
