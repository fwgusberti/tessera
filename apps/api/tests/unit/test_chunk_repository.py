"""Unit tests for SqlChunkRepository.upsert_chunks — TDD for Bug 1+2 fix."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, call

import pytest

from tessera_api.adapters.repo import SqlChunkRepository
from tessera_core.domain.entities import Chunk, Confidentiality


def _make_chunk(embedding: list[float] | None = None) -> Chunk:
    return Chunk(
        id=uuid.uuid4(),
        document_version_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        space_id=uuid.uuid4(),
        ordinal=0,
        text="sample text",
        embedding=embedding or [0.1] * 768,
        confidentiality=Confidentiality.INTERNAL,
        language="pt-BR",
    )


def test_upsert_chunks_executes_insert_for_each_chunk():
    """session.execute must be called once per chunk — currently it is never called."""
    mock_session = AsyncMock()
    repo = SqlChunkRepository(mock_session)

    chunks = [_make_chunk(), _make_chunk()]
    asyncio.run(repo.upsert_chunks(chunks))

    assert mock_session.execute.call_count == len(chunks), (
        "execute() must be called once per chunk; currently upsert_chunks never calls execute()"
    )


def test_upsert_chunks_includes_embedding_in_params():
    """The params dict passed to execute must contain an 'embedding' key."""
    captured: list[dict] = []

    class _Session:
        async def execute(self, sql, params=None):
            captured.append(params or {})

    repo = SqlChunkRepository(_Session())
    chunk = _make_chunk(embedding=[0.5] * 768)
    asyncio.run(repo.upsert_chunks([chunk]))

    assert captured, "execute() was never called — upsert_chunks does not call execute()"
    assert "embedding" in captured[0], (
        "params must include 'embedding'; currently missing so all embeddings are NULL"
    )


def test_upsert_chunks_skips_null_embedding_gracefully():
    """A chunk with embedding=None must not raise; embedding param should be None."""
    captured: list[dict] = []

    class _Session:
        async def execute(self, sql, params=None):
            captured.append(params or {})

    repo = SqlChunkRepository(_Session())
    chunk = _make_chunk(embedding=None)
    chunk = chunk.model_copy(update={"embedding": None})

    asyncio.run(repo.upsert_chunks([chunk]))

    assert captured, "execute() was never called"
    assert captured[0].get("embedding") is None
