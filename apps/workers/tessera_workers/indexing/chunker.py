"""Chunking + embedding + pgvector indexing of published document versions."""

from __future__ import annotations

import uuid
from uuid import UUID

from tessera_core.domain.entities import Chunk, Confidentiality, DocumentVersion


def chunk_document(
    version: DocumentVersion,
    document_id: UUID,
    space_id: UUID,
    confidentiality: Confidentiality = Confidentiality.INTERNAL,
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[Chunk]:
    """Split document content into overlapping chunks for vector indexing."""
    content = version.content_markdown
    language = version.frontmatter.get("language", "pt-BR")

    # Simple token-based sliding window on words
    words = content.split()
    chunks: list[Chunk] = []
    step = max(1, chunk_size - overlap)

    for i, start in enumerate(range(0, max(1, len(words) - overlap), step)):
        window = words[start : start + chunk_size]
        if not window:
            break
        text = " ".join(window)
        chunks.append(
            Chunk(
                id=uuid.uuid4(),
                document_version_id=version.id,
                document_id=document_id,
                space_id=space_id,
                ordinal=i,
                text=text,
                confidentiality=confidentiality,
                language=language,
            )
        )
        if start + chunk_size >= len(words):
            break

    return chunks
