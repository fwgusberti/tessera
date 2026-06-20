"""Tests for structured error logging in the indexing worker."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import structlog.testing


@pytest.fixture()
def mock_session():
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.mark.anyio
async def test_embedding_failure_logs_document_id(mock_session):
    """When embed() raises, document_id must appear in the structlog error record."""
    doc_id = uuid4()
    ver_id = uuid4()
    space_id = uuid4()

    from tessera_core.domain.entities import (
        Chunk,
        Confidentiality,
        Document,
        DocumentLifecycleState,
        DocumentVersion,
    )

    fake_doc = Document(
        id=doc_id,
        space_id=space_id,
        title="Test Doc",
        confidentiality=Confidentiality.INTERNAL,
        state=DocumentLifecycleState.PUBLISHED,
    )
    fake_version = DocumentVersion(
        id=ver_id,
        document_id=doc_id,
        version_number=1,
        content_markdown="Some content",
    )
    fake_chunk = Chunk(
        id=uuid4(),
        document_version_id=ver_id,
        document_id=doc_id,
        space_id=space_id,
        ordinal=0,
        text="# Test Doc\n\nSome content",
        confidentiality=Confidentiality.INTERNAL,
        language="en",
    )

    with (
        patch(
            "tessera_workers.indexing._index._get_session",
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_session),
                __aexit__=AsyncMock(return_value=False),
            ),
        ),
        patch(
            "tessera_api.adapters.repo.SqlDocumentVersionRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=fake_version,
        ),
        patch(
            "tessera_api.adapters.repo.SqlDocumentRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=fake_doc,
        ),
        patch(
            "tessera_workers.indexing.chunker.chunk_document",
            return_value=[fake_chunk],
        ),
        patch(
            "tessera_api.adapters.embeddings.OllamaEmbeddingProvider.embed",
            new_callable=AsyncMock,
            side_effect=ConnectionError("connection refused"),
        ),
    ):
        from tessera_workers.indexing._index import _do_index

        with structlog.testing.capture_logs() as cap_logs:
            with pytest.raises(ConnectionError):
                await _do_index(
                    version_id=ver_id,
                    document_id=doc_id,
                    space_id=space_id,
                )

        error_records = [r for r in cap_logs if r.get("log_level") == "error"]
        assert len(error_records) >= 1, "Expected at least one error log record"
        record = error_records[0]
        assert "document_id" in record, f"document_id missing from log record: {record}"
        assert str(doc_id) == record["document_id"]


@pytest.mark.anyio
async def test_embedding_failure_re_raises(mock_session):
    """When embed() raises, _do_index must re-raise the exception."""
    doc_id = uuid4()
    ver_id = uuid4()
    space_id = uuid4()

    from tessera_core.domain.entities import (
        Chunk,
        Confidentiality,
        Document,
        DocumentLifecycleState,
        DocumentVersion,
    )

    fake_doc = Document(
        id=doc_id,
        space_id=space_id,
        title="Test Doc",
        confidentiality=Confidentiality.INTERNAL,
        state=DocumentLifecycleState.PUBLISHED,
    )
    fake_version = DocumentVersion(
        id=ver_id,
        document_id=doc_id,
        version_number=1,
        content_markdown="Some content",
    )
    fake_chunk = Chunk(
        id=uuid4(),
        document_version_id=ver_id,
        document_id=doc_id,
        space_id=space_id,
        ordinal=0,
        text="# Test Doc\n\nSome content",
        confidentiality=Confidentiality.INTERNAL,
        language="en",
    )

    with (
        patch(
            "tessera_workers.indexing._index._get_session",
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_session),
                __aexit__=AsyncMock(return_value=False),
            ),
        ),
        patch(
            "tessera_api.adapters.repo.SqlDocumentVersionRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=fake_version,
        ),
        patch(
            "tessera_api.adapters.repo.SqlDocumentRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=fake_doc,
        ),
        patch(
            "tessera_workers.indexing.chunker.chunk_document",
            return_value=[fake_chunk],
        ),
        patch(
            "tessera_api.adapters.embeddings.OllamaEmbeddingProvider.embed",
            new_callable=AsyncMock,
            side_effect=RuntimeError("ollama unavailable"),
        ),
    ):
        from tessera_workers.indexing._index import _do_index

        with pytest.raises(RuntimeError, match="ollama unavailable"):
            await _do_index(
                version_id=ver_id,
                document_id=doc_id,
                space_id=space_id,
            )
