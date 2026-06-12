"""Async ingestion sync logic called by Celery tasks."""

from __future__ import annotations

import os
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


async def _get_session() -> AsyncSession:
    engine = create_async_engine(
        os.getenv("DATABASE_URL", "postgresql+psycopg://tessera:tessera@localhost:5432/tessera"),
        echo=False,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return factory()


async def _do_sync(connector_id: UUID) -> None:
    async with await _get_session() as session:
        from tessera_api.adapters.repo import (
            SqlConnectorRepository,
            SqlDocumentRepository,
            SqlDocumentVersionRepository,
            SqlSourceArtifactRepository,
            SqlSpaceRepository,
        )
        from tessera_workers.connectors.git import GitConnector
        from tessera_workers.ingestion.pipeline import ingest_artifact, classify_document_state
        from tessera_core.domain.entities import Document, DocumentLifecycleState, SourceArtifact
        import hashlib

        connector_repo = SqlConnectorRepository(session)
        artifact_repo = SqlSourceArtifactRepository(session)
        doc_repo = SqlDocumentRepository(session)
        version_repo = SqlDocumentVersionRepository(session)
        space_repo = SqlSpaceRepository(session)

        connector = await connector_repo.get_by_id(connector_id)
        if connector is None:
            return

        space = await space_repo.get_by_id(connector.space_id)
        if space is None:
            return

        plugin = GitConnector()
        since_version = connector.last_sync_at and connector.config.get("last_sha")

        for record in plugin.fetch_artifacts(connector_id, connector.config, since_version):
            # Check for existing artifact by external_id
            existing = await artifact_repo.get_by_external_id(connector_id, record.external_id)
            if existing and existing.content_hash == record.content_hash:
                continue  # Idempotent: same content, skip

            # Upsert source artifact
            artifact_entity = SourceArtifact(
                connector_id=connector_id,
                external_id=record.external_id,
                path=record.path,
                source_version=record.source_version,
                raw_content=record.raw_content,
                content_hash=record.content_hash,
            )
            saved_artifact = await artifact_repo.upsert(artifact_entity)

            # Find or create document for this path
            docs = await doc_repo.list_by_space(connector.space_id)
            doc = next(
                (d for d in docs if d.current_version_id is not None
                 and hasattr(d, "_path") and d._path == record.path),
                None,
            )
            if doc is None:
                version_number = 1
                doc_entity = Document(
                    space_id=connector.space_id,
                    title=record.path.split("/")[-1].replace(".md", ""),
                    state=DocumentLifecycleState.INGESTED,
                )
                doc = await doc_repo.create(doc_entity)
            else:
                version_number = await version_repo.next_version_number(doc.id)

            # Create document version from ingested artifact
            version = ingest_artifact(
                artifact=record,
                space=space,
                connector_id=connector_id,
                version_number=version_number,
                document_id=doc.id,
            )
            version_entity = version.model_copy(update={"source_artifact_id": saved_artifact.id})
            await version_repo.create(version_entity)

        # Update connector sync status
        current_sha = plugin.current_version(connector.config)
        connector.config["last_sha"] = current_sha
        await connector_repo.update_sync_status(connector_id, "ok")
        await session.commit()
