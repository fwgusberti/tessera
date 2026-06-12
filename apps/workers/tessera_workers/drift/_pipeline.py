"""Async drift detection pipeline."""

from __future__ import annotations

import os
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


async def _get_session() -> AsyncSession:
    engine = create_async_engine(
        os.getenv("DATABASE_URL", "postgresql+psycopg://tessera:tessera@localhost:5432/tessera"),
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return factory()


async def _do_detect_drift(connector_id: UUID) -> None:
    async with await _get_session() as session:
        from tessera_api.adapters.repo import (
            SqlConnectorRepository,
            SqlDocumentRepository,
            SqlSourceArtifactRepository,
            SqlProposalRepository,
        )
        from tessera_workers.drift.detector import detect_drift, create_proposal
        from tessera_workers.connectors.git import GitConnector
        from tessera_core.domain.entities import DocumentLifecycleState
        from tessera_core.services.lifecycle import mark_outdated

        connector_repo = SqlConnectorRepository(session)
        doc_repo = SqlDocumentRepository(session)
        artifact_repo = SqlSourceArtifactRepository(session)
        proposal_repo = SqlProposalRepository(session)

        connector = await connector_repo.get_by_id(connector_id)
        if connector is None:
            return

        plugin = GitConnector()
        for record in plugin.fetch_artifacts(connector_id, connector.config):
            existing = await artifact_repo.get_by_external_id(connector_id, record.external_id)
            if existing is None:
                continue

            if not detect_drift(existing, existing.__class__(**{**existing.__dict__, "content_hash": record.content_hash})):
                continue

            # Find the document associated with this artifact
            docs = await doc_repo.list_by_space(connector.space_id, DocumentLifecycleState.PUBLISHED)
            for doc in docs:
                pending = await proposal_repo.list_pending_for_document(doc.id)
                if pending:
                    # Invalidate stale proposals
                    await proposal_repo.invalidate_pending_for_document(doc.id)

                proposal = create_proposal(
                    document_id=doc.id,
                    source_artifact_id=existing.id,
                    old_markdown=existing.raw_content or "",
                    new_markdown=record.raw_content or "",
                    drift_score=0.8,
                    summary=f"Source changed: {record.path}",
                )
                await proposal_repo.create(proposal)

                # Mark document as outdated (but keep serving prior version)
                updated_doc = mark_outdated(doc)
                await doc_repo.update_state(doc.id, updated_doc.state)

        await session.commit()
