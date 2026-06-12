"""Parity test: MCP search_documents == REST /v1/search for identical permissions."""

import uuid
import pytest

from tessera_core.domain.entities import AgentCredential, Confidentiality
from tessera_core.permissions.access import AccessContext


def make_credential(space_ids=None) -> AgentCredential:
    return AgentCredential(
        name="parity-agent",
        token_hash="parity-hash",
        scoped_space_ids=space_ids or [],
        max_confidentiality=Confidentiality.INTERNAL,
    )


class TestSearchParity:
    def test_mcp_and_rest_apply_same_confidentiality_filter(self):
        """Both MCP and REST must apply the same confidentiality filtering logic."""
        from tessera_mcp.tools.search import filter_agent_results
        from tessera_api.rag.retrieval import filter_by_confidentiality

        space_id = uuid.uuid4()
        credential = make_credential(space_ids=[space_id])

        chunks = [
            {"chunk_id": str(uuid.uuid4()), "confidentiality": "internal", "space_id": str(space_id)},
            {"chunk_id": str(uuid.uuid4()), "confidentiality": "confidential", "space_id": str(space_id)},
            {"chunk_id": str(uuid.uuid4()), "confidentiality": "restricted", "space_id": str(space_id)},
        ]

        mcp_results = filter_agent_results(chunks, credential=credential)
        rest_results = filter_by_confidentiality(chunks, max_confidentiality=Confidentiality.INTERNAL)

        mcp_ids = {r["chunk_id"] for r in mcp_results}
        rest_ids = {r["chunk_id"] for r in rest_results}

        assert mcp_ids == rest_ids, "MCP and REST must return identical chunk sets for same permissions"

    def test_restricted_excluded_from_both_mcp_and_rest(self):
        """Restricted chunks must never appear in either MCP or REST results."""
        from tessera_mcp.tools.search import filter_agent_results
        from tessera_api.rag.retrieval import filter_by_confidentiality

        space_id = uuid.uuid4()
        chunks = [{"chunk_id": str(uuid.uuid4()), "confidentiality": "restricted", "space_id": str(space_id)}]
        credential = make_credential(space_ids=[space_id])

        assert filter_agent_results(chunks, credential=credential) == []
        assert filter_by_confidentiality(chunks, max_confidentiality=Confidentiality.RESTRICTED) == []
