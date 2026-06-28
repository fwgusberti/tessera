from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_api.adapters.models.source_artifact import SourceArtifactModel
from tessera_core.domain.source_artifact import SourceArtifact
from tessera_core.ports.repositories.source_artifact import SourceArtifactRepository


def _artifact_from_model(m: SourceArtifactModel) -> SourceArtifact:
    return SourceArtifact(
        id=m.id,
        connector_id=m.connector_id,
        external_id=m.external_id,
        path=m.path,
        source_version=m.source_version,
        raw_content=m.raw_content,
        content_hash=m.content_hash,
        fetched_at=m.fetched_at,
    )


class SqlSourceArtifactRepository(SourceArtifactRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, artifact: SourceArtifact) -> SourceArtifact:
        existing = await self.get_by_external_id(artifact.connector_id, artifact.external_id)
        if existing:
            await self._session.execute(
                update(SourceArtifactModel)
                .where(SourceArtifactModel.id == existing.id)
                .values(
                    raw_content=artifact.raw_content,
                    content_hash=artifact.content_hash,
                    source_version=artifact.source_version,
                )
            )
            return (
                await self.get_by_external_id(artifact.connector_id, artifact.external_id)
            ) or artifact
        model = SourceArtifactModel(
            id=artifact.id,
            connector_id=artifact.connector_id,
            external_id=artifact.external_id,
            path=artifact.path,
            source_version=artifact.source_version,
            raw_content=artifact.raw_content,
            content_hash=artifact.content_hash,
        )
        self._session.add(model)
        await self._session.flush()
        return _artifact_from_model(model)

    async def get_by_external_id(
        self, connector_id: UUID, external_id: str
    ) -> SourceArtifact | None:
        result = await self._session.execute(
            select(SourceArtifactModel).where(
                SourceArtifactModel.connector_id == connector_id,
                SourceArtifactModel.external_id == external_id,
            )
        )
        model = result.scalar_one_or_none()
        return _artifact_from_model(model) if model else None

    async def list_by_connector(self, connector_id: UUID) -> list[SourceArtifact]:
        result = await self._session.execute(
            select(SourceArtifactModel).where(SourceArtifactModel.connector_id == connector_id)
        )
        return [_artifact_from_model(m) for m in result.scalars().all()]
