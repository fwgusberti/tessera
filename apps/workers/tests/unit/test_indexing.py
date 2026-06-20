"""Unit tests for indexing pipeline — TDD for title-prepend fix."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch


def _make_document(title: str = "Quarterly Budget Review", content: str = "Some body text."):
    from tessera_core.domain.entities import (
        Confidentiality,
        Document,
        DocumentLifecycleState,
        DocumentVersion,
    )

    doc_id = uuid.uuid4()
    ver_id = uuid.uuid4()
    space_id = uuid.uuid4()

    document = Document(
        id=doc_id,
        space_id=space_id,
        title=title,
        language="en",
        confidentiality=Confidentiality.INTERNAL,
        tags=[],
        state=DocumentLifecycleState.PUBLISHED,
        current_version_id=ver_id,
    )
    version = DocumentVersion(
        id=ver_id,
        document_id=doc_id,
        version_number=1,
        content_markdown=content,
        frontmatter={},
    )
    return document, version, space_id


def _run_do_index(document, version, space_id):
    """Run _do_index with all DB/embedding calls mocked."""
    from tessera_workers.indexing._index import _do_index

    mock_ver_repo = MagicMock()
    mock_ver_repo.get_by_id = AsyncMock(return_value=version)

    mock_doc_repo = MagicMock()
    mock_doc_repo.get_by_id = AsyncMock(return_value=document)

    saved_chunks: list = []

    mock_chunk_repo = MagicMock()

    async def _capture_upsert(chunks):
        saved_chunks.extend(chunks)

    mock_chunk_repo.upsert_chunks = _capture_upsert
    mock_chunk_repo.delete_by_document = AsyncMock()

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    fake_embedding = [0.1] * 768

    with (
        patch(
            "tessera_workers.indexing._index._get_session",
            new=AsyncMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_session),
                __aexit__=AsyncMock(return_value=False),
            )),
        ),
        patch("tessera_api.adapters.repo.SqlDocumentVersionRepository", return_value=mock_ver_repo),
        patch("tessera_api.adapters.repo.SqlDocumentRepository", return_value=mock_doc_repo),
        patch("tessera_api.adapters.repo.SqlChunkRepository", return_value=mock_chunk_repo),
        patch(
            "tessera_api.adapters.embeddings.OllamaEmbeddingProvider.embed",
            new=AsyncMock(return_value=[[fake_embedding[0]] * 768] * 20),
        ),
    ):
        asyncio.run(_do_index(version.id, document.id, space_id))

    return saved_chunks


def test_title_prepended_to_first_chunk_text():
    """First chunk text must start with the document title after _do_index."""
    document, version, space_id = _make_document(
        title="Quarterly Budget Review",
        content="This document covers the budget allocation for Q3.",
    )

    chunks = _run_do_index(document, version, space_id)

    assert chunks, "_do_index produced no chunks"
    first_text = chunks[0].text
    assert "Quarterly Budget Review" in first_text, (
        f"Expected first chunk to contain title, got: {first_text!r}"
    )


def test_title_in_chunk_when_content_does_not_contain_title():
    """Even if content_markdown has no mention of the title, it must appear in a chunk."""
    title = "Unique Title XYZ-99"
    document, version, space_id = _make_document(
        title=title,
        content="Completely unrelated content with no mention of the title whatsoever.",
    )

    chunks = _run_do_index(document, version, space_id)

    all_text = " ".join(c.text for c in chunks)
    assert title in all_text, (
        f"Title '{title}' not found in any chunk text; chunks: {[c.text[:80] for c in chunks]}"
    )
