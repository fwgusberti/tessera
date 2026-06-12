"""Async indexing logic called by Celery tasks."""

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


async def _do_index(version_id: UUID, document_id: UUID, space_id: UUID) -> None:
    from tessera_workers.indexing.chunker import chunk_document

    async with await _get_session() as session:
        from tessera_api.adapters.repo import (
            SqlChunkRepository,
            SqlDocumentRepository,
            SqlDocumentVersionRepository,
        )

        version_repo = SqlDocumentVersionRepository(session)
        doc_repo = SqlDocumentRepository(session)
        chunk_repo = SqlChunkRepository(session)

        version = await version_repo.get_by_id(version_id)
        document = await doc_repo.get_by_id(document_id)
        if version is None or document is None:
            return

        # Generate chunks
        chunks = chunk_document(
            version=version,
            document_id=document_id,
            space_id=space_id,
            confidentiality=document.confidentiality,
        )

        # Embed chunks
        from tessera_api.adapters.embeddings import OllamaEmbeddingProvider

        embedding_provider = OllamaEmbeddingProvider()
        texts = [c.text for c in chunks]
        if texts:
            embeddings = await embedding_provider.embed(texts)
            for chunk, emb in zip(chunks, embeddings, strict=False):
                chunk.embedding = emb

        # Remove old chunks and write new ones
        await chunk_repo.delete_by_document(document_id)
        await chunk_repo.upsert_chunks(chunks)
        await session.commit()


async def _do_remove(document_id: UUID) -> None:
    async with await _get_session() as session:
        from tessera_api.adapters.repo import SqlChunkRepository

        repo = SqlChunkRepository(session)
        await repo.delete_by_document(document_id)
        await session.commit()
