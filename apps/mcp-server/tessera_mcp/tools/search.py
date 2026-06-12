"""MCP search_documents tool — server-side permission enforcement."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel

from tessera_core.domain.entities import AgentCredential, Confidentiality


class SearchDocumentsResult(BaseModel):
    document_id: UUID
    version_id: UUID
    chunk_id: UUID
    score: float
    snippet: str
    citation: dict[str, Any]


def filter_scoped_spaces(
    credential: AgentCredential,
    requested_space_ids: list[UUID],
) -> list[UUID]:
    """Return only space IDs within the credential's scope."""
    scoped = set(credential.scoped_space_ids)
    return [sid for sid in requested_space_ids if sid in scoped]


def filter_agent_results(
    results: list[dict[str, Any]],
    credential: AgentCredential,
) -> list[dict[str, Any]]:
    """Filter search results by agent credential permissions.

    - Restricted documents are ALWAYS excluded for agents.
    - Confidentiality must not exceed the credential's max_confidentiality.
    """
    max_level = credential.max_confidentiality.level()
    return [
        r
        for r in results
        if Confidentiality(r["confidentiality"]) != Confidentiality.RESTRICTED
        and Confidentiality(r["confidentiality"]).level() <= max_level
    ]
