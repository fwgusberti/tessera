"""Indexing Celery tasks: chunk + embed + write to pgvector."""

from __future__ import annotations

import uuid

from tessera_workers.celery_app import app


@app.task(name="tessera.index_document_version")
def index_document_version(document_version_id: str, document_id: str, space_id: str) -> None:
    """Chunk a published DocumentVersion and store embeddings in pgvector."""
    import asyncio
    from tessera_workers.indexing._index import _do_index

    asyncio.run(
        _do_index(
            version_id=uuid.UUID(document_version_id),
            document_id=uuid.UUID(document_id),
            space_id=uuid.UUID(space_id),
        )
    )


@app.task(name="tessera.remove_document_index")
def remove_document_index(document_id: str) -> None:
    """Remove all chunks for a document from the vector index."""
    import asyncio
    from tessera_workers.indexing._index import _do_remove

    asyncio.run(_do_remove(document_id=uuid.UUID(document_id)))
