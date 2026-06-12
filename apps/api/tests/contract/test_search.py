"""Contract test: POST /v1/search — ACL-first, só published."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSearchContract:
    def test_search_result_has_required_fields(self):
        """Each search result must have: document_id, version_id, chunk_id, score, snippet, citation."""
        from tessera_api.rag.retrieval import SearchResult

        result = SearchResult(
            document_id=uuid.uuid4(),
            version_id=uuid.uuid4(),
            chunk_id=uuid.uuid4(),
            score=0.87,
            snippet="This is the relevant snippet...",
            citation={"document_title": "Onboarding Guide", "source": "Git:main:docs/onboarding.md"},
        )
        assert result.document_id is not None
        assert result.version_id is not None
        assert result.chunk_id is not None
        assert 0.0 <= result.score <= 1.0
        assert result.snippet is not None
        assert result.citation is not None

    def test_search_only_returns_published_docs(self):
        """ACL-first invariant: only published documents appear in results."""
        from tessera_api.rag.retrieval import filter_published

        published_ids = {uuid.uuid4(), uuid.uuid4()}
        draft_id = uuid.uuid4()

        results = [
            {"document_id": pid, "state": "published"} for pid in published_ids
        ] + [{"document_id": draft_id, "state": "ingested"}]

        filtered = filter_published(results)
        assert all(r["state"] == "published" for r in filtered)
        assert len(filtered) == len(published_ids)

    def test_restricted_documents_excluded_from_results(self):
        """Restricted documents must never appear in search results."""
        from tessera_api.rag.retrieval import filter_by_confidentiality
        from tessera_core.domain.entities import Confidentiality

        results = [
            {"document_id": uuid.uuid4(), "confidentiality": Confidentiality.INTERNAL.value},
            {"document_id": uuid.uuid4(), "confidentiality": Confidentiality.RESTRICTED.value},
            {"document_id": uuid.uuid4(), "confidentiality": Confidentiality.CONFIDENTIAL.value},
        ]

        filtered = filter_by_confidentiality(results, max_confidentiality=Confidentiality.CONFIDENTIAL)
        confidentialities = [r["confidentiality"] for r in filtered]
        assert Confidentiality.RESTRICTED.value not in confidentialities
        assert Confidentiality.INTERNAL.value in confidentialities
        assert Confidentiality.CONFIDENTIAL.value in confidentialities
