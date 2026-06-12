"""MCP contract tests: search_documents / read_document structure."""

import uuid
import pytest

from tessera_core.domain.entities import AgentCredential, Confidentiality


def make_credential(space_ids=None) -> AgentCredential:
    return AgentCredential(
        name="test-agent",
        token_hash="fake-hash",
        scoped_space_ids=space_ids or [uuid.uuid4()],
        max_confidentiality=Confidentiality.INTERNAL,
    )


class TestSearchDocumentsContract:
    def test_search_result_has_required_fields(self):
        """search_documents result must include document_id, snippet, citation."""
        from tessera_mcp.tools.search import SearchDocumentsResult

        space_id = uuid.uuid4()
        result = SearchDocumentsResult(
            document_id=uuid.uuid4(),
            version_id=uuid.uuid4(),
            chunk_id=uuid.uuid4(),
            score=0.88,
            snippet="The onboarding steps are...",
            citation={"document_title": "Onboarding Guide", "source": "Git:main:docs/onboarding.md"},
        )
        assert result.document_id is not None
        assert result.snippet is not None
        assert result.citation is not None
        assert 0.0 <= result.score <= 1.0

    def test_search_returns_empty_for_out_of_scope_space(self):
        """When space_ids include spaces outside credential scope, they are silently ignored."""
        from tessera_mcp.tools.search import filter_scoped_spaces

        credential = make_credential(space_ids=[uuid.uuid4()])
        requested = [uuid.UUID("00000000-0000-0000-0000-000000000001")]  # out of scope

        effective = filter_scoped_spaces(credential=credential, requested_space_ids=requested)
        assert effective == []

    def test_search_excludes_restricted_from_agent_results(self):
        """Restricted documents must never appear in agent search results."""
        from tessera_mcp.tools.search import filter_agent_results
        from tessera_core.domain.entities import Confidentiality

        chunks = [
            {"chunk_id": str(uuid.uuid4()), "confidentiality": "restricted", "score": 0.95},
            {"chunk_id": str(uuid.uuid4()), "confidentiality": "internal", "score": 0.80},
        ]
        filtered = filter_agent_results(chunks, credential=make_credential())
        assert all(c["confidentiality"] != "restricted" for c in filtered)


class TestReadDocumentContract:
    def test_read_document_result_has_required_fields(self):
        """read_document must return markdown + frontmatter + version_number."""
        from tessera_mcp.tools.read import ReadDocumentResult

        result = ReadDocumentResult(
            document_id=uuid.uuid4(),
            title="Onboarding Guide",
            markdown="# Onboarding Guide\nWelcome...",
            frontmatter={"sector": "engineering", "language": "en"},
            version_number=3,
            citations_supported=True,
        )
        assert result.markdown is not None
        assert result.version_number > 0
        assert result.citations_supported is True

    def test_not_found_response_does_not_leak_existence(self):
        """Error for missing/restricted doc must be 'not_found', not 'forbidden'."""
        from tessera_mcp.tools.read import NotFoundError

        err = NotFoundError(document_id=uuid.uuid4())
        assert err.error == "not_found"
        assert "forbidden" not in str(err).lower()
        assert "restricted" not in str(err).lower()
