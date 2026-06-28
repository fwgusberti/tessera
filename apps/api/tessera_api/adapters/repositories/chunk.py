from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tessera_core.domain.chunk import Chunk
from tessera_core.domain.confidentiality import Confidentiality as Conf
from tessera_core.ports.repositories.chunk import ChunkRepository


class SqlChunkRepository(ChunkRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_chunks(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            await self._session.execute(
                text("""
                    INSERT INTO chunks
                        (id, document_version_id, document_id, space_id,
                         ordinal, text, confidentiality, language, embedding)
                    VALUES
                        (:id, :document_version_id, :document_id, :space_id,
                         :ordinal, :text, :confidentiality, :language,
                         CAST(:embedding AS vector))
                    ON CONFLICT (id) DO UPDATE SET
                        document_version_id = EXCLUDED.document_version_id,
                        ordinal             = EXCLUDED.ordinal,
                        text                = EXCLUDED.text,
                        confidentiality     = EXCLUDED.confidentiality,
                        language            = EXCLUDED.language,
                        embedding           = EXCLUDED.embedding
                """),
                {
                    "id": chunk.id,
                    "document_version_id": chunk.document_version_id,
                    "document_id": chunk.document_id,
                    "space_id": chunk.space_id,
                    "ordinal": chunk.ordinal,
                    "text": chunk.text,
                    "confidentiality": chunk.confidentiality.value,
                    "language": chunk.language,
                    "embedding": str(chunk.embedding) if chunk.embedding is not None else None,
                },
            )

    async def delete_by_document(self, document_id: UUID) -> None:
        await self._session.execute(
            text("DELETE FROM chunks WHERE document_id = :doc_id"),
            {"doc_id": document_id},
        )

    async def search(
        self,
        query_embedding: list[float],
        space_ids: list[UUID],
        max_confidentiality_level: int,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        allowed_levels = [
            c.value for c in Conf if c.level() <= max_confidentiality_level and c != Conf.RESTRICTED
        ]
        space_id_strs = [str(sid) for sid in space_ids]

        sql = text("""
            SELECT
                c.id, c.document_version_id, c.document_id, c.space_id,
                c.ordinal, c.text, c.confidentiality, c.language,
                1 - (c.embedding <=> CAST(:embedding AS vector)) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE
                c.space_id = ANY(CAST(:space_ids AS uuid[]))
                AND c.confidentiality = ANY(CAST(:allowed_confidentiality AS text[]))
                AND d.state = 'published'
                AND c.embedding IS NOT NULL
            ORDER BY c.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)
        result = await self._session.execute(
            sql,
            {
                "embedding": str(query_embedding),
                "space_ids": "{" + ",".join(space_id_strs) + "}",
                "allowed_confidentiality": "{" + ",".join(allowed_levels) + "}",
                "top_k": top_k,
            },
        )
        return [dict(row._mapping) for row in result]
