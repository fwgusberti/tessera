"""Retention policy execution: expire documents and purge vector index."""

from __future__ import annotations

import os
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


async def _do_run_retention() -> None:
    engine = create_async_engine(
        os.getenv("DATABASE_URL", "postgresql+psycopg://tessera:tessera@localhost:5432/tessera"),
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        from tessera_api.adapters.repo import SqlDocumentRepository, SqlChunkRepository
        from tessera_core.domain.entities import DocumentLifecycleState
        from tessera_core.services.lifecycle import expire_document
        from sqlalchemy import select
        from tessera_api.adapters.models import DocumentModel

        today = date.today()
        result = await session.execute(
            select(DocumentModel).where(
                DocumentModel.validity_until <= today,
                DocumentModel.state.in_(["published", "outdated"]),
            )
        )
        models = result.scalars().all()

        doc_repo = SqlDocumentRepository(session)
        chunk_repo = SqlChunkRepository(session)

        for model in models:
            from tessera_core.domain.entities import Document, Confidentiality

            doc = Document(
                id=model.id,
                space_id=model.space_id,
                title=model.title,
                state=DocumentLifecycleState(model.state),
                owner_user_id=model.owner_user_id,
                current_version_id=model.current_version_id,
            )
            expired = expire_document(doc)
            await doc_repo.update_state(doc.id, expired.state)
            await chunk_repo.delete_by_document(doc.id)

        await session.commit()
