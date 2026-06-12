"""MCP permission tests: scoped agent, 0 leaks for out-of-scope/restricted.

SC-003/SC-007.
"""

import uuid
import pytest

from tessera_core.domain.entities import AgentCredential, Confidentiality


def make_credential(space_ids=None, max_confidentiality=Confidentiality.INTERNAL) -> AgentCredential:
    return AgentCredential(
        name="test-agent",
        token_hash="hash123",
        scoped_space_ids=space_ids or [],
        max_confidentiality=max_confidentiality,
    )


class TestMcpPermissions:
    def test_agent_cannot_access_out_of_scope_space(self):
        """Credential scoped to engineering cannot access HR space."""
        from tessera_mcp.tools.search import filter_scoped_spaces

        eng_space = uuid.uuid4()
        hr_space = uuid.uuid4()

        credential = make_credential(space_ids=[eng_space])
        effective = filter_scoped_spaces(
            credential=credential, requested_space_ids=[hr_space]
        )
        assert hr_space not in effective
        assert len(effective) == 0

    def test_restricted_documents_excluded_for_agents(self):
        """Restricted documents must be excluded from agent results regardless of scope."""
        from tessera_mcp.tools.search import filter_agent_results

        space_id = uuid.uuid4()
        credential = make_credential(space_ids=[space_id])

        results = [
            {"chunk_id": str(uuid.uuid4()), "confidentiality": "restricted", "space_id": str(space_id)},
            {"chunk_id": str(uuid.uuid4()), "confidentiality": "internal", "space_id": str(space_id)},
        ]
        filtered = filter_agent_results(results, credential=credential)
        assert all(r["confidentiality"] != "restricted" for r in filtered)

    def test_agent_max_confidentiality_is_enforced(self):
        """Agent with internal max cannot see confidential documents."""
        from tessera_mcp.tools.search import filter_agent_results

        space_id = uuid.uuid4()
        credential = make_credential(space_ids=[space_id], max_confidentiality=Confidentiality.INTERNAL)

        results = [
            {"chunk_id": str(uuid.uuid4()), "confidentiality": "confidential", "space_id": str(space_id)},
            {"chunk_id": str(uuid.uuid4()), "confidentiality": "internal", "space_id": str(space_id)},
        ]
        filtered = filter_agent_results(results, credential=credential)
        assert all(r["confidentiality"] == "internal" for r in filtered)

    def test_empty_scope_returns_no_results(self):
        """Agent with no scoped spaces should get no results."""
        from tessera_mcp.tools.search import filter_scoped_spaces

        credential = make_credential(space_ids=[])
        any_space = uuid.uuid4()
        effective = filter_scoped_spaces(credential=credential, requested_space_ids=[any_space])
        assert len(effective) == 0
